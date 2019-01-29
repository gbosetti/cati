# coding: utf-8

import argparse
import json
# std
import time
from datetime import datetime

import os
import shutil

# web
from flask import Flask, render_template, request
from flask import jsonify
from flask_cors import CORS, cross_origin
from flask_frozen import Freezer

# mabed
from mabed.functions import Functions
import mabed.utils as utils

event_browser = Flask(__name__, static_folder='browser/static', template_folder='browser/templates')

# Enable CORS
cors = CORS(event_browser)
event_browser.config['CORS_HEADERS'] = 'Content-Type'


# Disable Cache
@event_browser.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r


@event_browser.route('/')
def index():
    return render_template('template.html',
                           events=event_descriptions,
                           event_impact='[' + ','.join(impact_data) + ']',
                           k=mabed.k,
                           theta=mabed.theta,
                           sigma=mabed.sigma)


@event_browser.route('/f')
def ind():
    return render_template('index.html')


# Settings Form submit
@event_browser.route('/settings', methods=['POST'])
@cross_origin()
def settings():
    data = request.form
    print(data)
    return jsonify(data)


# Run MABED
@event_browser.route('/detect_events', methods=['POST', 'GET'])
@cross_origin()
def detect_events():
    events = functions.detect_events("test3")
    return jsonify(events)


@event_browser.route('/images')
def firas():
    with open('res2016.json') as f:
        data = json.load(f)

    clusters_num = len(data['duplicates'])
    clusters = data['duplicates']
    return render_template('images.html',
                           clusters_num=clusters_num,
                           clusters=clusters
                           )


@event_browser.route('/event_descriptions')
def event_descriptions():
    res = {}
    events = []
    for event in event_descriptions:
        start_date = datetime.strptime(event[1], "%Y-%m-%d %H:%M:%S")
        end_date = datetime.strptime(event[1], "%Y-%m-%d %H:%M:%S")
        obj = {
            "media": {
                "url": "static/images/img.jpg"
            },
            "start_date": {
                "month": start_date.month,
                "day": start_date.day,
                "year": start_date.year
            },
            "end_date": {
                "month": end_date.month,
                "day": end_date.day,
                "year": end_date.year
            },
            "text": {
                "headline": event[3],
                "text": "<p>" + event[4] + "</p>"
            }
        }
        events.append(obj)
    res = {
        "events": events
    }
    return jsonify(res)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Build event browser')
    p.add_argument('i', metavar='input', type=str, help='Input pickle file')
    p.add_argument('--o', metavar='output', type=str, help='Output html directory', default=None)
    args = p.parse_args()

    print('Loading events from %s...' % args.i)
    mabed = utils.load_events(args.i)

    functions = Functions()

    # format data
    print('Preparing data...')
    event_descriptions = []
    impact_data = []
    formatted_dates = []
    for i in range(0, mabed.corpus.time_slice_count):
        formatted_dates.append(int(time.mktime(mabed.corpus.to_date(i).timetuple())) * 1000)
    for event in mabed.events:
        mag = event[0]
        main_term = event[2]
        raw_anomaly = event[4]
        formatted_anomaly = []
        time_interval = event[1]
        related_terms = []
        for related_term in event[3]:
            related_terms.append(related_term[0] + ' (' + str("{0:.2f}".format(related_term[1])) + ')')
        event_descriptions.append((mag,
                                   str(mabed.corpus.to_date(time_interval[0])),
                                   str(mabed.corpus.to_date(time_interval[1])),
                                   main_term,
                                   ', '.join(related_terms)))
        for i in range(0, mabed.corpus.time_slice_count):
            value = 0
            if time_interval[0] <= i <= time_interval[1]:
                value = raw_anomaly[i]
                if value < 0:
                    value = 0
            formatted_anomaly.append('[' + str(formatted_dates[i]) + ',' + str(value) + ']')
        impact_data.append('{"key":"' + main_term + '", "values":[' + ','.join(formatted_anomaly) + ']}')

    if args.o is not None:
        if os.path.exists(args.o):
            shutil.rmtree(args.o)
        os.makedirs(args.o)
        print('Freezing event browser into %s...' % args.o)
        event_browser_freezer = Freezer(event_browser)
        event_browser.config.update(
            FREEZER_DESTINATION=args.o,
            FREEZER_RELATIVE_URLS=True,
        )
        event_browser.debug = False
        event_browser.config['ASSETS_DEBUG'] = False
        event_browser_freezer.freeze()
        print('Done.')
    else:
        event_browser.run(debug=False, host='localhost', port=2016)
