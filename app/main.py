from flask import Flask
from flask import request
from flask import render_template
import requests
# import couchdb

app = Flask(__name__)

address = '172.26.132.81'
username = 'group63'
password = '123'
database = 'twitter_stream_processed'
view = 'by_place'
# couch = couchdb.Server('http://{}:5984'.format(address))
# couch.resource.credentials = (username, password)
# db = couch[database]

country = 'Australia'
state = ['New South Wales', 'Queensland', 'South Australia', 'Tasmania', 'Victoria', 'Western Australia', 'Australian Capital Territory', 'Northern Territory']
# administrative_division = {'Australia': {'New South Wales': ['Sydney', 'Newcastle', 'Wollongong', 'Central Coast'],
#                                          'Queensland': ['Brisbane', 'Cairns', 'Gold Coast', 'Sunshine Coast', 'Toowoomba', 'Townsville'],
#                                          'South Australia': ['Adelaide', 'Port Lincoln'],
#                                          'Tasmania': ['Hobart', 'Launceston'],
#                                          'Victoria': ['Ballarat', 'Bendigo', 'Geelong', 'Melbourne', 'Melton', 'Wangaratta'],
#                                          'Western Australia': ['Albany', 'Perth'],
#                                          'Australian Capital Territory': ['Canberra'],
#                                          'Northern Territory': ['Darwin', 'Ghan']
#                                          }
#                            }


@app.route('/')
def index():
    return render_template('index.html', name='Group 63')


@app.route('/sentiment')
def sentiment():
    key = request.args.get("key")
    result = {}
    if key == country:
        response = requests.get('http://{}:5984/{}/_design/{}/_view/{}?group=True'.format(address, database, view, key))
        for row in response.json()['rows']:
            if row['key'] in state:
                result[row['key']] = row['value']['sum'] / row['value']['count']
    # elif key in state:
    #     response = requests.get('http://{}:5984/{}/_design/{}/_view/{}?group=True'.format(address, database, view, key))
    #     for row in response.json()['rows']:
    #         if row['key'] in administrative_division[country][key]:
    #             result[row['key']] = row['value']['sum'] / row['value']['count']
    return render_template('sentiment.html', key=key, result=result)


if __name__ == '__main__':
    app.run(debug=True)
