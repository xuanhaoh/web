from flask import Flask
from flask import request
from flask import render_template
import requests
import json
from collections import OrderedDict
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression, BayesianRidge
from sklearn.metrics import mean_squared_error
import pandas as pd

app = Flask(__name__)

address = '172.26.132.81'
username = 'group63'
password = '123'
twitter_database = 'twitter_stream_processed'
twitter_view = 'by_place'
# limit = 8

country = 'Australia'
state = ['NSW', 'QLD', 'SA', 'TAS', 'VIC', 'WA', 'ACT', 'NT']
short_name = {'New South Wales': 'NSW', 'Queensland': 'QLD', 'South Australia': 'SA', 'Tasmania': 'TAS',
              'Victoria': 'VIC', 'Western Australia': 'WA', 'Australian Capital Territory': 'ACT', 'Northern Territory': 'NT'}
factors = ['income', 'education', 'alcohol', 'smoking', 'obesity']
factor_lookup = {'income': {'database': 'aurin_income', 'design': 'by_place', 'view': 'income',
                            'state': 'state', 'lga': 'Name', 'count': 'income_aud_2014_15', 'rate': 'mean_aud_2014_15'},
                 'education': {'database': 'aurin_education', 'design': 'by_place', 'view': 'education',
                               'state': 'State', 'lga': 'Name', 'count': 'Persons_Bachelor_Degree_Level_Total',
                               'rate': 'Persons_With_Post_School_Qualifications_Bachelor_Degree__'},
                 'alcohol': {'database': 'aurin_health', 'design': 'by_place', 'view': 'alcohol',
                             'state': 'ste_name', 'lga': 'lga_name', 'count': 'alchl_p_1_count', 'rate': 'alchl_p_2_asr'},
                 'smoking': {'database': 'aurin_health', 'design': 'by_place', 'view': 'smoking',
                             'state': 'ste_name', 'lga': 'lga_name', 'count': 'smkrs_p_1_count', 'rate': 'smkrs_p_2_asr'},
                 'obesity': {'database': 'aurin_health', 'design': 'by_place', 'view': 'obesity',
                             'state': 'ste_name', 'lga': 'lga_name', 'count': 'obese_p_1_count', 'rate': 'obese_p_2_asr'}}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/backend', methods=['POST', 'GET'])
def backend():
    if request.method == 'GET':
        place = request.args.get("place")
        factor = request.args.get("factor")
        if request.args.get("limit"):
            limit = False
        else:
            limit = 8
    elif request.method == 'POST':
        data = json.loads(request.get_data(as_text=True))
        place = data['place']
        factor = data['factor']
        limit = 8
    else:
        return 'Method not allowed!'

    if place == country:
        factor_args = factor_lookup[factor]
        twitter_response = requests.get('http://{}:5984/{}/_design/{}/_view/{}?group=True'
                                        .format(address, twitter_database, twitter_view, place))
        aurin_response = requests.get('http://{}:5984/{}/_design/{}/_view/{}?group=True'
                                      .format(address, factor_args['database'], factor_args['design'], factor_args['view']))
        aurin_result = {row['key']: row['value'][0] / row['value'][1] for row in aurin_response.json()['rows']}
        final_result = {row['key']: [row['value']['sum'] / row['value']['count'], aurin_result[short_name[row['key']].lower()]]
                        for row in twitter_response.json()['rows'] if row['key'] in short_name.keys()}
    elif place == 'ACT':
        factor_args = factor_lookup[factor]
        twitter_response = requests.get('http://{}:5984/{}/_design/{}/_view/{}?group=True'
                                        .format(address, twitter_database, twitter_view, place))
        twitter_result = {row['key']: {'value': row['value']['sum'] / row['value']['count'],
                                       'count': row['value']['count']} for row in twitter_response.json()['rows'] if row['key'] == 'Canberra'}
        aurin_response = requests.post('http://{}:5984/{}/_find'.format(address, factor_args['database']),
                                       headers={'Content-Type': 'application/json'},
                                       json={'selector': {factor_args['lga']: {'$regex': r'Unincorporated ACT'}},
                                             'fields': [factor_args['lga'], factor_args['rate']]})
        aurin_result = aurin_response.json()['docs'][0]
        final_result = {'Canberra': [twitter_result['Canberra']['value'], aurin_result[factor_args['rate']]]}
    elif place in state:
        factor_args = factor_lookup[factor]
        twitter_response = requests.get('http://{}:5984/{}/_design/{}/_view/{}?group=True'
                                        .format(address, twitter_database, twitter_view, place))
        twitter_result = {row['key']: {'value': row['value']['sum'] / row['value']['count'],
                                       'count': row['value']['count']} for row in twitter_response.json()['rows']}
        ordered_result = OrderedDict(sorted(twitter_result.items(), key=lambda x: x[1]['count'], reverse=True))
        final_result = {}
        for k, v in ordered_result.items():
            aurin_response = requests.post('http://{}:5984/{}/_find'.format(address, factor_args['database']),
                                           headers={'Content-Type': 'application/json'},
                                           json={'selector': {factor_args['lga']: {'$regex': r'(Greater )?{} \(\w+\)'.format(k)}},
                                                 'fields': [factor_args['lga'], factor_args['rate']]})
            if aurin_response.json()['docs']:
                aurin_result = aurin_response.json()['docs'][0]
                final_result[k] = [ordered_result[k]['value'], aurin_result[factor_args['rate']]]
                if limit and len(final_result) == limit:
                    break
    else:
        return 'Place not found!'

    final_result = {x[0]: [(x[1][0] + 1) * 50, x[1][1]] for x in final_result.items()}
    return json.dumps(final_result, ensure_ascii=False)


@app.route('/backend/result', methods=['POST', 'GET'])
def result():
    _id = requests.get('http://{}:5984/{}/_all_docs'.format(address, 'analyse')).json()['rows'][-1]['id']
    places_df = requests.post('http://{}:5984/{}/_find'.format(address, 'analyse'),
                              headers={'Content-Type': 'application/json'},
                              json={'selector': {'_id': _id}}).json()['docs'][0]
    places_df.pop('_id')
    places_df.pop('_rev')
    places_df = pd.DataFrame.from_dict(places_df).T
    model = run_model(places_df)
    feature_importance = {factor: importance for factor, importance in zip(factors, model.coef_)}
    return json.dumps({'data': places_df.T.to_dict(), 'result': feature_importance}, ensure_ascii=False)


@app.route('/backend/analyze', methods=['POST', 'GET'])
def analyze():
    places_df = get_data()
    requests.post('http://{}:5984/{}'.format(address, 'analyse'), json=places_df.T.to_dict())
    model = run_model(places_df)
    feature_importance = {factor: importance for factor, importance in zip(factors, model.coef_)}
    return json.dumps({'data': places_df.T.to_dict(), 'result': feature_importance}, ensure_ascii=False)


@app.route('/smoke')
def smoke():
    return render_template('smoke.html')


@app.route('/income')
def income():
    return render_template('income.html')


@app.route('/alcohol')
def alcohol():
    return render_template('alcohol.html')


@app.route('/obesity')
def obsesity():
    return render_template('obesity.html')


@app.route('/education')
def education():
    return render_template('education.html')


@app.route('/analyse')
def analyse():
    return render_template('analyse.html')


def get_data():
    places_df = []
    for place in state:
        place_df = []
        for factor in factors:
            print(place + ' ' + factor + ' start')
            response = requests.get(
                'http://{}:5000/backend?place={}&factor={}&limit=False'.format('localhost', place, factor)).json()
            factor_df = pd.DataFrame.from_dict(response).T
            factor_df.columns = ['sentiment', factor]
            factor_df = [factor_df.drop(['sentiment'], axis=1), factor_df['sentiment']]
            place_df.append(factor_df[0])
        place_df.append(factor_df[1])
        place_df = pd.concat(place_df, axis=1)
        places_df.append(place_df)
    places_df = pd.concat(places_df).dropna()
    return places_df


def run_model(places_df):
    x = places_df.drop('sentiment', axis=1)
    y = places_df['sentiment']
    mms = MinMaxScaler()
    x = pd.DataFrame(mms.fit_transform(x), index=x.index, columns=x.columns)
    model = LinearRegression()
    model.fit(x, y)
    return model


if __name__ == '__main__':
    app.run()
