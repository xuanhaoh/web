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

country_lookup = {'Australia': 8}
state_lookup = {'NSW': {'full_name': 'New South Wales', 'limit': 8}, 'QLD': {'full_name': 'Queensland', 'limit': 8},
                'SA': {'full_name': 'South Australia', 'limit': 8}, 'TAS': {'full_name': 'Tasmania', 'limit': 8},
                'VIC': {'full_name': 'Victoria', 'limit': 8}, 'WA': {'full_name': 'Western Australia', 'limit': 8},
                'ACT': {'full_name': 'Australian Capital Territory', 'limit': 8},
                'NT': {'full_name': 'Northern Territory', 'limit': 8}}
factor_lookup = {'alcohol': {'database': 'aurin_health', 'count': 'alchl_p_1_count', 'rate': 'alchl_p_2_asr'},
                 'smoking': {'database': 'aurin_health', 'count': 'smkrs_p_1_count', 'rate': 'smkrs_p_2_asr'}}


def couch_query(key):
    result = {}
    count = {}
    response = requests.get('http://{}:5984/{}/_design/{}/_view/{}?group=True'.format(address, twitter_database, twitter_view, key))
    for row in response.json()['rows']:
        result[row['key']] = row['value']['sum'] / row['value']['count']
        count[row['key']] = row['value']['count']
    return result, count


@app.route('/')
def index():
    return render_template('index.html', name='Group 63')


@app.route('/backend', methods=['POST', 'GET'])
def backend():
    if request.method == 'GET':
        area = request.args.get("area")
        factor = request.args.get("factor")
    elif request.method == 'GET':
        data = request.get_data()
        area = data['place']
        factor = data['factor']
    else:
        return 'Method not allowed'

    final_result = OrderedDict()
    if area in country_lookup.keys():
        pass
    elif area in state_lookup.keys():
        limit = state_lookup[area]['limit']
        twitter_response = requests.get('http://{}:5984/{}/_design/{}/_view/{}?group=True'
                                        .format(address, twitter_database, twitter_view, area))
        twitter_result = {row['key']: {'value': row['value']['sum'] / row['value']['count'],
                                       'count': row['value']['count']} for row in twitter_response.json()['rows']}
        ordered_result = OrderedDict(sorted(twitter_result.items(), key=lambda x: x[1]['count'], reverse=True))
        for k, v in ordered_result.items():
            aurin_response = requests.post('http://{}:5984/{}/_find'.format(address, factor_lookup[factor]['database']),
                                           headers={'Content-Type': 'application/json'},
                                           json={'selector': {'lga_name': {'$regex': r'(Greater )?{} \(\w+\)'.format(k)}},
                                                 'fields': ['lga_name', factor_lookup[factor]['rate']]})
            if aurin_response.json()['docs']:
                aurin_result = aurin_response.json()['docs'][0]
                final_result[k] = [ordered_result[k]['value'], aurin_result[factor_lookup[factor]['rate']]]
                if len(final_result) == limit:
                    return json.dumps(final_result)
    return json.dumps(final_result)


@app.route('/test', methods=['POST', 'GET'])
def test():
    if request.method == 'POST':
        loc = request.get_data(as_text=True)
        print(loc)
        d = {}
        c = {}
        tem = {}
        # 等aurin数据过来在这里加一下变成形式{place1:[emo, aurin], place2:[emo, aurin]...}
        if loc == 'Australia':
            d, c = couch_query('Australia')
        elif loc == 'NSW':
            d, c = couch_query('New South Wales')
        elif loc == 'QLD':
            d, c = couch_query('Queensland')
        elif loc == 'VIC':
            d, c = couch_query('Victoria')
        elif loc == 'TAS':
            d, c = couch_query('Tasmania')
        elif loc == 'WA':
            d, c = couch_query('Western Australia')
        elif loc == 'ACT':
            d, c = couch_query('Australian Capital Territory')
        elif loc == 'NT':
            d, c = couch_query('Northern Territory')
        else:
            d, c = couch_query('South Australia')
        l = sorted(c.items(), key=lambda item: item[1], reverse=True)
        if len(l) > 8:
            for i in range(0, 8):
                tem[l[i][0]] = d[l[i][0]] + 0.2  # base +0.2
            d = tem
        print(json.dumps(d, ensure_ascii=False))
        return json.dumps(d, ensure_ascii=False)

    else:
        print('456')
        return render_template('smoke.html')


@app.route('/smoke', methods=['POST', 'GET'])
def smoke():
    if request.method == 'POST':
        d = {"a": 1, "b": 2}
        return render_template('smoke.html', rs=json.dumps(d))

    else:
        return render_template('smoke.html')


if __name__ == '__main__':
    app.run(debug=True)
