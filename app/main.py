from flask import Flask
from flask import request
from flask import render_template
import requests
import json
from collections import OrderedDict

app = Flask(__name__)

address = '172.26.132.81'
username = 'group63'
password = '123'
twitter_database = 'twitter_stream_processed'
twitter_view = 'by_place'
limit = 8

country = 'Australia'
state = ['NSW', 'QLD', 'SA', 'TAS', 'VIC', 'WA', 'ACT', 'NT']
short_name = {'New South Wales': 'NSW', 'Queensland': 'QLD', 'South Australia': 'SA', 'Tasmania': 'TAS',
              'Victoria': 'VIC', 'Western Australia': 'WA', 'Australian Capital Territory': 'ACT', 'Northern Territory': 'NT'}
factor_lookup = {'alcohol': {'database': 'aurin_health',
                             'state': 'ste_name', 'lga': 'lga_name', 'count': 'alchl_p_1_count', 'rate': 'alchl_p_2_asr'},
                 'smoking': {'database': 'aurin_health', 'design': 'by_place', 'view': 'smoking',
                             'state': 'ste_name', 'lga': 'lga_name', 'count': 'smkrs_p_1_count', 'rate': 'smkrs_p_2_asr'}}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/backend', methods=['POST', 'GET'])
def backend():
    if request.method == 'GET':
        place = request.args.get("place")
        factor = request.args.get("factor")
    elif request.method == 'POST':
        data = json.loads(request.get_data(as_text=True))
        place = data['place']
        factor = data['factor']
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
                if len(final_result) == limit:
                    return json.dumps(final_result, ensure_ascii=False)
    else:
        return 'Place not found!'

    return json.dumps(final_result, ensure_ascii=False)


@app.route('/smoke', methods=['POST', 'GET'])
def smoke():
    if request.method == 'GET':
        return render_template('smoke.html')


if __name__ == '__main__':
    app.run(debug=True)
