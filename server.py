# coding: utf-8

import argparse
import json
# std
from datetime import datetime

# web
from flask import Flask, render_template, request
from flask import jsonify
from flask_cors import CORS, cross_origin
from flask_frozen import Freezer
from flask import Response
from flask_htpasswd import HtPasswdAuth

from kneed import KneeLocator



# mabed
from mabed.functions import Functions
import datetime
app = Flask(__name__, static_folder='browser/static', template_folder='browser/templates')
app.config['FLASK_HTPASSWD_PATH'] = '.htpasswd'
app.config['FLASK_SECRET'] = 'Hey Hey Kids, secure me!'


htpasswd = HtPasswdAuth(app)


# ==================================================================
# 1. Tests and Debug
# ==================================================================

# Enable CORS
# cors = CORS(app)
# app.config['CORS_HEADERS'] = 'Content-Type'

# Disable Cache
@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r


# Settings Form submit
@app.route('/settings', methods=['POST'])
# @cross_origin()
def settings():
    data = request.form
    return jsonify(data)


@app.route('/event_descriptions')
def event_descriptions():
    event_descriptions = functions.event_descriptions("test3")
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

# ==================================================================
# 2. MABED
# ==================================================================

# Run MABED
@app.route('/detect_events', methods=['POST', 'GET'])
# @cross_origin()
def detect_events():
    data = request.form
    index = data['index']
    k = int(data['top_events'])
    maf = float(data['min_absolute_frequency'])
    mrf = float(data['max_relative_frequency'])
    tsl = int(data['time_slice_length'])
    p = float(data['p_value'])
    theta = float(data['t_value'])
    sigma = float(data['s_value'])
    session = data['session']
    filter = data['filter']
    cluster = int(data['cluster'])
    events=""
    res = False
    if filter=="all":
        events = functions.event_descriptions(index, k, maf, mrf, tsl, p, theta, sigma, cluster)
    elif filter == "proposedconfirmed":
        filter = ["proposed","confirmed"]
        events = functions.filtered_event_descriptions(index, k, maf, mrf, tsl, p, theta, sigma, session, filter, cluster)
    else:
        events = functions.filtered_event_descriptions(index, k, maf, mrf, tsl, p, theta, sigma, session, [filter], cluster)
    if not events:
        events = "No Result!"
    else:
        res = True
    return jsonify({"result": res, "events":events})


# ==================================================================
# 3. Images
# ==================================================================

@app.route('/images')
def images():
    with open('twitter2015.json') as f:
        data = json.load(f)
    clusters_num = len(data['duplicates'])
    clusters = data['duplicates']
    return render_template('images.html',
                           clusters_num=clusters_num,
                           clusters=clusters
                           )

# ==================================================================
# 4. Tweets
# ==================================================================

# Get Tweets
@app.route('/tweets', methods=['POST'])
# @cross_origin()
def tweets():
    data = request.form
    tweets= functions.get_tweets(index=data['index'], word=data['word'])
    clusters= functions.get_clusters(index=data['index'], word=data['word'])
    return jsonify({"tweets": tweets, "clusters": clusters})

# Get Tweets
@app.route('/tweets_filter', methods=['POST'])
# @cross_origin()
def tweets_filter():
    data = request.form
    tweets= functions.get_tweets_query_state(index=data['index'], word=data['word'], state=data['state'], session=data['session'])
    clusters= functions.get_clusters(index=data['index'], word=data['word'])
    return jsonify({"tweets": tweets, "clusters": clusters})


@app.route('/tweets_scroll', methods=['POST'])
# @cross_origin()
def tweets_scroll():
    data = request.form
    tweets= functions.get_tweets_scroll(index=data['index'], sid=data['sid'], scroll_size=int(data['scroll_size']))
    return jsonify({"tweets": tweets})


# Get Event related tweets
@app.route('/event_tweets', methods=['POST'])
# @cross_origin()
def event_tweets():
    data = request.form
    index = data['index']
    event = json.loads(data['obj'])
    main_term = event['main_term'].replace(",", " ")
    related_terms = event['related_terms']
    tweets = functions.get_event_tweets(index, main_term, related_terms)
    clusters = functions.get_event_clusters(index, main_term, related_terms)
    return jsonify({"tweets": tweets, "clusters": clusters})


# Get Event related tweets
@app.route('/event_filter_tweets', methods=['POST'])
def event_filter_tweets():
    data = request.form
    index = data['index']
    state = data['state']
    session = data['session']
    event = json.loads(data['obj'])
    main_term = event['main_term'].replace(",", " ")
    related_terms = event['related_terms']
    tweets = functions.get_event_filter_tweets(index, main_term, related_terms, state, session)
    clusters = functions.get_event_clusters(index, main_term, related_terms)
    return jsonify({"tweets": tweets, "clusters": clusters})


@app.route('/tweets_state', methods=['POST'])
# @cross_origin()
def tweets_state():
    data = request.form
    tweets= functions.get_tweets_state(index=data['index'], session=data['session'], state=data['state'])
    return jsonify({"tweets": tweets})

# Get Image Cluster tweets
@app.route('/cluster_tweets', methods=['POST', 'GET'])
# @cross_origin()
def cluster_tweets():
    data = request.form
    index = data['index']
    cid = data['cid']
    event = json.loads(data['obj'])
    main_term = event['main_term'].replace(",", " ")
    related_terms = event['related_terms']
    tres = functions.get_event_tweets2(index, main_term, related_terms, cid)
    event_tweets = tres
    res = functions.get_cluster_tweets(index, cid)
    tweets = res['hits']['hits']
    tweets = {"results":tweets}
    return jsonify({"tweets": tweets, "event_tweets": event_tweets})

# Get Search Image Cluster tweets
@app.route('/cluster_search_tweets', methods=['POST', 'GET'])
# @cross_origin()
def cluster_search_tweets():
    data = request.form
    index = data['index']
    cid = data['cid']
    word = data['word']
    search_tweets = functions.get_big_tweets(index=index, word=word)
    res = functions.get_cluster_tweets(index, cid)
    tweets = res['hits']['hits']
    tweets = {"results": tweets}
    return jsonify({"tweets": tweets, "search_tweets": search_tweets})

# Get Event main image
@app.route('/event_image', methods=['POST'])
# @cross_origin()
def event_image():
    data = request.form
    index = data['index']
    event = json.loads(data['obj'])
    main_term = event['main_term'].replace(",", " ")
    related_terms = event['related_terms']
    image = functions.get_event_image(index, main_term, related_terms)
    res = False
    if image:
        image = image['hits']['hits'][0]['_source']
        res = True
    return jsonify({"result":res, "image": image})


# Test & Debug
@app.route('/mark_valid', methods=['POST', 'GET'])
# @cross_origin()
def mark_valid():
    data = request.form
    res = functions.set_all_status("twitter2015", "session_Twitter2015", "proposed")
    return jsonify(res)


@app.route('/mark_event', methods=['POST', 'GET'])
# @cross_origin()
def mark_event():
    data = request.form
    index = data['index']
    session = data['session']
    functions.set_status(index, session, data)
    return jsonify(data)


@app.route('/mark_cluster', methods=['POST', 'GET'])
# @cross_origin()
def mark_cluster():
    data = request.form
    index = data['index']
    session = data['session']
    cid = data['cid']
    state = data['state']
    res = functions.set_cluster_state(index, session, cid, state)
    return jsonify(res)


@app.route('/mark_tweet', methods=['POST', 'GET'])
# @cross_origin()
def mark_tweet():
    data = request.form
    index = data['index']
    session = data['session']
    tid = data['tid']
    val = data['val']
    functions.set_tweet_state(index, session, tid, val)
    return jsonify(data)


@app.route('/mark_search_tweets', methods=['POST', 'GET'])
# @cross_origin()
def mark_search_tweets():
    data = request.form
    index = data['index']
    session = data['session']
    word= data['word']
    state = data['state']
    functions.set_search_status(index, session, state, word)
    return jsonify(data)


@app.route('/mark_search_tweets_force', methods=['POST', 'GET'])
def mark_search_tweets_force():
    data = request.form
    index = data['index']
    session = data['session']
    word= data['word']
    state = data['state']
    functions.set_search_status_force(index, session, state, word)
    return jsonify(data)


@app.route('/delete_field', methods=['POST', 'GET'])
# @cross_origin()
def delete_field():
    up1 = functions.update_all("twitter2017", "tweet", "imagesCluster", "")
    return jsonify(up1)


# ==================================================================
# 5. Export
# ==================================================================


@app.route('/export_events', methods=['POST', 'GET'])
# @cross_origin()
def export_events():
    # data = request.form
    # session = data['session_id']
    # res = functions.get_session(session)
    res = functions.get_session('6n7aD2QBU2R9ngE9d8IB')
    index = res['_source']['s_index']
    events = json.loads(res['_source']['events'])
    for event in events:
        main_term = event['main_term'].replace(",", " ")
        # event['main_term']=main_term
        related_terms = event['related_terms']
        # tweets = functions.get_event_tweets(index, main_term, related_terms)
        # tweets = tweets['hits']['hits']
        event['tweets'] = 'tweets'

    return jsonify(events)
    # return Response(str(events),
    #     mimetype='application/json',
    #     headers={'Content-Disposition': 'attachment;filename=events.json'})


@app.route('/export_tweets', methods=['POST', 'GET'])
# @cross_origin()
def export_tweets():
    session = request.args.get('session')

    # data = request.form
    # session = data['session_id']
    # res = functions.get_session(session)
    res = functions.get_session(session)
    index = res['_source']['s_index']
    events = json.loads(res['_source']['events'])
    for event in events:
        main_term = event['main_term'].replace(",", " ")
        # event['main_term']=main_term
        related_terms = event['related_terms']
        # tweets = functions.get_event_tweets(index, main_term, related_terms)
        # tweets = tweets['hits']['hits']
        event['tweets'] = 'tweets'

    return jsonify(session)
    # return Response(str(events),
    #     mimetype='application/json',
    #     headers={'Content-Disposition': 'attachment;filename=events.json'})


@app.route('/export_confirmed_tweets', methods=['POST', 'GET'])
# @cross_origin()
def export_confirmed_tweets():
    session = request.args.get('session')
    res = functions.get_session(session)
    index = res['_source']['s_index']
    s_name = res['_source']['s_name']
    tweets = functions.export_event(index,s_name)
    return Response(str(tweets),
                mimetype='application/json',
                headers={'Content-Disposition':'attachment;filename='+s_name+'tweets.json'})

# ==================================================================
# 6. Beta
# ==================================================================
@app.route('/event_tweets_count', methods=['POST', 'GET'])
def event_tweets_count():
    data = request.form
    index = data['index']
    event = json.loads(data['obj'])
    main_term = event['main_term'].replace(",", " ")
    related_terms = event['related_terms']
    count = functions.get_event_tweets_count(index, main_term, related_terms)
    all_count = functions.get_all_count(index)
    percentage = 100*(count/all_count)
    res = {'count':count, 'all': all_count, 'percentage':percentage}
    return jsonify(res)

@app.route('/get_all_count', methods=['POST', 'GET'])
def get_all_count():
    data = request.form
    index = data['index']
    count = functions.get_all_count(index)
    res = {'count':count}
    return jsonify(res)

@app.route('/get_words_count', methods=['POST', 'GET'])
def get_words_count():
    data = request.form
    index = data['index']
    words = data['words']
    count = functions.get_words_count(index, words)
    res = {'count':count}
    return jsonify(res)

@app.route('/get_keywords', methods=['POST', 'GET'])
def get_keywords():
    data = request.form
    index = data['index']
    words = data['words']
    sd = data['sd']
    ed = data['ed']
    count = data['count']
    # event = json.loads(data['obj'])
    # main_term = event['main_term'].replace(",", " ")
    # related_terms = event['related_terms']

    start_time = int(sd) / 1000
    start_time = datetime.datetime.fromtimestamp(start_time)
    end_time = int(ed) / 1000
    end_time = datetime.datetime.fromtimestamp(end_time)

    start_ms = start_time.timestamp() * 1000
    end_ms = end_time.timestamp() * 1000

    # count = functions.get_range_count(index, start_ms, end_ms)
    newKeywords = functions.process_range_tweets(index, start_ms, end_ms, words, 100)


    res = {"words":words, "count":count, "newKeywords":newKeywords}
    # res = {"words":words, "count":count}
    return jsonify(res)


@app.route('/get_word2vec', methods=['POST', 'GET'])
def get_word2vec():
    # data = request.form
    index = 'twitter2017'
    words = "fêtes"
    count = 10

    # count = functions.get_range_count(index, start_ms, end_ms)
    newKeywords = functions.process_w2v_tweets(index, words, 10)

    res = {"words":words, "count":count, "newKeywords":newKeywords}
    # res = {"words":words, "count":count}
    print(res)
    return jsonify(res)

@app.route('/get_sse', methods=['POST', 'GET'])
def get_sse():
    data = request.form
    index = data['index']
    words = data['words']
    event = json.loads(data['obj'])
    keywords = json.loads(data['keywords'])
    newKeywords = keywords['words']

    main_term = event['main_term'].replace(",", " ")
    related_terms = event['related_terms']
    sd = data['sd']
    ed = data['ed']

    start_time = int(sd) / 1000
    start_time = datetime.datetime.fromtimestamp(start_time)
    end_time = int(ed) / 1000
    end_time = datetime.datetime.fromtimestamp(end_time)
    start_ms = start_time.timestamp() * 1000
    end_ms = end_time.timestamp() * 1000

    sse = {}
    sse_points = []
    # mean = functions.getMean(index, main_term, related_terms)
    # sse0 = functions.getSSE(index, main_term, related_terms, mean)
    # sse[0]=sse0

    related_string = ""
    least_value = 100.0
    for t in related_terms:
        related_string = related_string + " "+ t['word']
        if float(t['value'])<least_value:
            least_value=float(t['value'])
    words = main_term +" "+ related_string

    # newKeywords = functions.process_range_tweets(index, start_ms, end_ms, words, 20)

    # newKeywords = [('couleurs', 0.9541982412338257), ('cette…', 0.9535157084465027), ('consultation', 0.9513106346130371), ('tgvmax', 0.9512830972671509), ('lyonmag', 0.9508819580078125), ('vous…', 0.9507380127906799), ('sublime', 0.9503788948059082), ('le_progres', 0.9499937891960144), ('vue', 0.9492042660713196), ('oliviermontels', 0.9490641355514526), ('sport2job', 0.9481754899024963), ('lyonnai…', 0.9481167197227478), ('hauteurs', 0.9463335275650024), ('illuminations', 0.9462761282920837), ('familial', 0.9458074569702148), ('fdl2017…', 0.945579469203949), ('leprogreslyon', 0.9455731511116028), ('weekend', 0.9454441070556641), ('pensant', 0.9449157118797302), ('radioscoopinfos', 0.9441419839859009)]
    print("---------------")
    print("newKeywords")
    print(newKeywords)
    print("related_terms")
    print(related_terms)
    print("---------------")
    sse2 = []
    for i in range(0, 40):
        temp_terms = []
        temp_terms = temp_terms + related_terms

        # for j in range(0,i):
        #     keyword=newKeywords[j]
        #     temp_terms = temp_terms + [{'word':keyword[0], 'value':least_value*keyword[1]}]

        keyword = newKeywords[i]
        temp_terms = temp_terms + [{'word': keyword[0], 'value': least_value * keyword[1]}]

        tempMean = functions.getMean(index, main_term, temp_terms)
        tempSSE = functions.getSSE(index, main_term, temp_terms, tempMean)
        sse[i] = tempSSE
        sse2 = sse2 + [(i,(tempSSE, keyword[0]))]

        # sse[i] = 99
        print(i)
        print("-------------------------------")

        # tweets = functions.get_event_tweets_bigsearch(index, main_term, related_terms)
    # tweet = functions.get_event_central_tweets(index, main_term, related_terms)
    # tweet = tweet['hits']['hits'][0]['_source']['text']
    # functions.d2v(tweet, tweets)


    x = range(0, 40)
    y = []
    print("++++++")
    newlist = sorted(sse2, key=lambda x: x[1][0], reverse=False)
    print(main_term)
    print(" ")
    print(newlist)
    x2 = []
    y2 = []
    for k in newlist:
        x2.append(k[0])
        y2.append(k[1][0])
    # print(x2)
    print(" ")
    print(y2)
    print("++++")

    # for val in sse:
    #     print(sse[val])
    #     y.append(sse[val])
    # print(y)

    # kn = KneeLocator(x, y, invert=True, direction='decreasing')
    kn = KneeLocator(x, y2, invert=True)

    print("kn.knee")
    print(kn.knee)
    elbow = kn.knee
    if not elbow:
        elbow = KneeLocator(x, y2, invert=False).knee

    sse_points2 = []
    count = 0
    for point in y2:
        if count == elbow:
            sse_points2.append({"x": count, "y": point, "label": newlist[count][1][1], "indexLabel": "Optimal number of new keywords","markerColor": "red"})
        else:
            sse_points2.append({"x": count, "y": point, "label": newlist[count][1][1]})
        count = count + 1

    # for point in sse:
    #     if point == kn.knee:
    #         sse_points.append({"x": point, "y": sse[point], "indexLabel": "Optimal number of new keywords","markerColor": "red"})
    #     else:
    #         sse_points.append({"x": point, "y": sse[point]})


    # res = {'count':len(tweets), "tweet":tweet['hits']['hits'][0]['_source']}
    res = {"sse":sse, "elbow":elbow, "sse_points":sse_points2, "sse2":sse2}
    return jsonify(res)


@app.route('/get_results', methods=['POST', 'GET'])
def get_results():
    data = request.form
    index = data['index']
    session = data['session']
    keywords = json.loads(data['keywords'])
    event = json.loads(data['obj'])
    main_term = event['main_term'].replace(",", " ")
    related_terms = event['related_terms']


    query_words = main_term.replace(","," ") + " "
    for t in related_terms:
        query_words += t['word'] + " "

    # print("query_words")
    # print(query_words)
    results = []

    all = functions.get_event_tweets_count(index, main_term, related_terms)
    event_confirmed = functions.get_event_state_tweets_count(index, session, query_words, "confirmed")

    # new_confirmed = functions.get_event_state_tweets_count(index, session, query_words, "confirmed")

    # results.append({'confirmed': event_confirmed, 'event': event_confirmed, 'all': all, 'words': ''})

    # print("words")
    temp_words = ""
    total = 0
    finalwords = ""
    ListS = []
    i = 0
    for keyword in keywords:
        # print(keyword)
        # temp_words = temp_words + ' '+keyword[0]
        # new_words = query_words + ' '+temp_words
        new_words = query_words + ' '+keyword[0]
        # query_words = query_words + ' '+keyword[0]
        new_confirmed = functions.get_event_state_tweets_count(index, session, new_words, "confirmed")
        words_count = functions.get_words_tweets_count(index, session, new_words)
        NbK = functions.get_words_tweets_count(index, session, keyword[0])
        event_count = functions.get_words_tweets_count(index, session, query_words)

        gain = new_confirmed - event_confirmed

        new_section = words_count - event_count
        NbKb = NbK - new_section
        percent2=0
        if NbKb>0:
            percent = (NbKb / NbK)*100
            if new_section > 0:
                percent2 = (gain / new_section)*100
            else:
                percent2 = 100
        else:
            percent = 0

        if percent > 30:
            # total = total + gain
            finalwords = finalwords + keyword[0] + " "


        output = {'confirmed': new_confirmed, 'NbK': NbK, 'NbE': event_confirmed, 'NbKb': NbKb, 'all': words_count, 'word': keyword[0],"percent":percent, "p2":percent2,"gain": gain}
        ListS = ListS + [(i, (keyword[0], percent, output))]
        i+=1
        # results.append({'confirmed': new_confirmed, 'event': event_confirmed, 'all': words_count, 'word': keyword[0],"percent":percent, "p2":percent2,"gain": gain})
        results.append(output)
        # results.append({'word': keyword[0],"percent":percent, "p2":percent2, "gain": gain})


    # ============================================================
    # Elbow point
    # ============================================================
    newlist = sorted(ListS, key=lambda x: x[1][1], reverse=True)
    # print(newlist)

    x = range(0, 100)
    y2 = []
    for k in newlist:
        y2.append(k[1][1])
    # print(" ")
    # print(y2)
    # print("++++")

    kn = KneeLocator(x, y2,direction="decreasing", invert=False)

    # print("kn.knee")
    # print(kn.knee)
    elbow = kn.knee
    if not elbow:
        elbow = KneeLocator(x, y2,direction="decreasing", invert=True).knee
        # print("kn.knee2")
        # print(elbow)

    sse_points2 = []
    count = 0
    elbow_value = 0
    for point in y2:
        if count == elbow:
            elbow_value = point
            sse_points2.append(
                {"x": count, "y": point, "label": newlist[count][1][0], "indexLabel": "Elbow value",
                 "markerColor": "red"})
        else:
            sse_points2.append({"x": count, "y": point, "label": newlist[count][1][0]})
        count = count + 1


    # ============================================================
    # Results
    # ============================================================
    testValues = [1, 5, 10, 20, 30, 40 , 50, 60, 70]
    testValues = testValues  + [elbow_value]
    testValues = sorted(testValues)
    print(testValues)
    print("total = ")
    total = functions.get_event_state_tweets_count(index, session, finalwords, "confirmed")
    print(total)
    finalcount = functions.get_words_tweets_count(index, session, finalwords)

    eventCount = functions.get_words_tweets_count(index, session, query_words)
    eventConfirmedCount = functions.get_event_state_tweets_count(index, session, query_words, "confirmed")
    eventNegativeCount = functions.get_event_state_tweets_count(index, session, query_words, "negative")


    testList = []
    for val in testValues:
        testWords = ''
        for kv in newlist:
            if kv[1][1] >= val:
                testWords = testWords + kv[1][0] + ' '
        testValCount = functions.get_words_tweets_count(index, session, testWords)
        testValConfirmedCount = functions.get_event_state_tweets_count(index, session, testWords, "confirmed")
        testValNegativeCount = functions.get_event_state_tweets_count(index, session, testWords, "negative")

        testAllCount = functions.get_words_tweets_count(index, session, query_words + ' ' + testWords)
        testAllConfirmedCount = functions.get_event_state_tweets_count(index, session, query_words + ' ' +testWords, "confirmed")
        testAllNegativeCount = functions.get_event_state_tweets_count(index, session, query_words + ' ' +testWords, "negative")
        newtweets = testAllCount - eventCount
        newConfirmedtweets = testAllConfirmedCount - eventConfirmedCount
        newNegativetweets = testAllNegativeCount - eventNegativeCount


        # if newtweets > 0:
        if newConfirmedtweets > 0 or newNegativetweets>0:
            # newConfirmedPersent = (newConfirmedtweets / newtweets)*100
            newConfirmedPersent = (newConfirmedtweets / (newConfirmedtweets+newNegativetweets))*100
        else:
            newConfirmedPersent = 0

        reviewedTweetsCount = testValConfirmedCount + testValNegativeCount
        testList.append({'val': val, 'words': testWords, 'testValCount': testValCount, 'testValConfirmedCount': testValConfirmedCount, 'testValNegativeCount':testValNegativeCount, 'newtweets': newtweets, 'newConfirmedtweets': newConfirmedtweets, 'newConfirmedPersent': newConfirmedPersent, 'reviewedTweetsCount': reviewedTweetsCount})

    step5= {'eventCount': eventCount, 'eventConfirmedCount':eventConfirmedCount, 'testList': testList}
    print("finalcount = ")
    print(finalcount)
    print(finalwords)


    # all_count = functions.get_all_count(index)
    # percentage = 100 * (count / all_count)
    # res = {'count': count}
    return jsonify({'results':results, 'elbow':sse_points2, 'newlist': newlist, 'step5':step5})

# ==================================================================
# 7. Sessions
# ==================================================================

# Get Sessions
@app.route('/sessions', methods=['POST', 'GET'])
# @cross_origin()
def sessions():
    data = request.form
    # up1 = functions.update_all("mabed_sessions", "session", "s_type", "tweet")
    # up = functions.delete_session("s1")
    res = functions.get_sessions()
    return jsonify(res['hits']['hits'])

# Add new Session
@app.route('/add_session', methods=['POST'])
# @cross_origin()
def add_session():
    data = request.form
    name = data['s_name']
    index = data['s_index']
    res = functions.add_session(name, index)
    status = False
    if res:
        status = True
    return jsonify({"result": status, "body": res})


# Delete Session
@app.route('/delete_session', methods=['POST'])
# @cross_origin()
def delete_session():
    data = request.form
    id = data['id']
    res = functions.delete_session(id)
    return jsonify({"result": res})


# Get Session
@app.route('/get_session', methods=['POST'])
# @cross_origin()
def get_session():
    data = request.form
    id = data['id']
    res = functions.get_session(id)
    status = False
    if res:
        status = True
    return jsonify({"result": status, "body": res})


# Update session results
@app.route('/update_session_results', methods=['POST'])
# @cross_origin()
def update_session_results():
    data = request.form
    events = data['events']
    impact_data = data['impact_data']
    index = data['index']
    res = functions.update_session_results(index, events, impact_data)
    status = False
    if res:
        status = True
    return jsonify({"result": status, "body": res})


# Get session results
@app.route('/get_session_results', methods=['POST', 'GET'])
# @cross_origin()
def get_session_results():
    data = request.form
    index = data['index']
    res = functions.get_session_results(index)
    status = False
    if res:
        status = True
    return jsonify({"result": status, "body": res})


# ==================================================================
# 6. Main
# ==================================================================
@app.route('/')
@htpasswd.required
def index(user):
    return render_template('index.html')


if __name__ == '__main__':
    functions = Functions()
    app.run(debug=True, host='localhost', port=5000, threaded=True)
    # app.run(debug=False, host='mediamining.univ-lyon2.fr', port=5000, threaded=True)
