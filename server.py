# coding: utf-8
from preprocessing_and_stats.PreProcessor import PreProcessor
from preprocessing_and_stats.StopWords import EnglishStopWords, FrenchStopWords
from BackendLogger import BackendLogger

import argparse
import json
import base64
import os
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
from classification.active_learning import ActiveLearning
from classification.active_learning_no_ui import ActiveLearningNoUi
from classification.ngram_based_classifier import NgramBasedClasifier


# mabed
from mabed.functions import Functions
import datetime
app = Flask(__name__, static_folder='browser/static', template_folder='browser/templates')
app.config['FLASK_HTPASSWD_PATH'] = '.htpasswd'
app.config['FLASK_SECRET'] = 'Hey Hey Kids, secure me!'
app.backend_logger = BackendLogger()

functions = Functions()
SELF = "'self'"
DownSELF = "'self'"
# here we define the content security policy,
# this CSP allows for inline script, and using a nonce will improve security
with open('config.json', 'r') as f:
    config = json.load(f)
default_source = config['default']['index']
default_session = config['default']['session']
for source in config['elastic_search_sources']:
    if source['index'] == default_source:
        default_host = source['host']
        default_port = source['port']
        default_user = source['user']
        default_password = source['password']
        default_timeout = source['timeout']
        default_index = source['index']
        default_doc_type = source['doc_type']

htpasswd = HtPasswdAuth(app)
ngram_classifier = NgramBasedClasifier()
classifier = ActiveLearning(download_folder_name="tmp_data")

al_path = os.path.join(os.getcwd(), "classification", "logs", "current_al_status.json")
if not os.path.exists(os.path.dirname(al_path)):
    os.makedirs(os.path.dirname(al_path))

al_backend_logger = BackendLogger(al_path)
app.loop_index = 0

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


# Returns the analysis of the raw dataset
@app.route('/produce_dataset_stats', methods=['POST'])
# @cross_origin()
def produce_dataset_stats():
    data = request.form
    # pre_processor = PreProcessor()
    # raw_tweets = read_raw_tweets_from_elastic()
    # pre_processor.pre_process(
    #     raw_tweets,
    #     generate_stats=True,
    #     include_mentions=True,
    #     include_hashtags=True
    # )
    # stats = pre_processor.get_stats()
    # print(stats)
    stats = functions.get_lang_count(index=data['index'])
    return jsonify({
        "total_tweets": functions.get_total_tweets(index=data['index']),
        "total_hashtags": functions.get_total_hashtags(index=data['index']),
        "total_urls": functions.get_total_urls(index=data['index']),
        "total_images": functions.get_total_images(index=data['index']),
        "lang_stats":stats['aggregations']['distinct_lang']['buckets'],
        "total_lang": stats['aggregations']['count']['value'],
        "total_mentions": functions.get_total_mentions(index=data['index'])

    })

# Get Classification stats
@app.route('/produce_classification_stats', methods=['GET','POST'])
def produce_classification_stats():
    data = request.form
    #get session and index name
    return jsonify({
        "classification_stats" : functions.get_classification_stats(index=data['index'], session_name=data['session'])
    })

@app.route('/get_elastic_logs', methods=['POST', 'GET'])
# @cross_origin()
def get_elastic_logs():
    data = request.form

    return jsonify(functions.get_elastic_logs(data['index']))
    # logs = jsonify(app.backend_logger.get_logs())
    # app.backend_logger.clear_logs()
    #return logs

@app.route('/get_backend_logs', methods=['POST', 'GET'])
# @cross_origin()
def get_backend_logs():
    logs = jsonify(app.backend_logger.get_logs())
    app.backend_logger.clear_logs()
    return logs

# Run MABED
@app.route('/detect_events', methods=['POST', 'GET'])
# @cross_origin()
def detect_events():

    data = request.form
    target_index = data['index']
    print("\n\nTARGET INDEX:", target_index)
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
        events = functions.event_descriptions(target_index, k, maf, mrf, tsl, p, theta, sigma, cluster, logger=app.backend_logger)
    elif filter == "proposedconfirmed":
        filter = ["proposed","confirmed"]
        events = functions.filtered_event_descriptions(target_index, k, maf, mrf, tsl, p, theta, sigma, session, filter, cluster, logger=app.backend_logger)
    else:
        events = functions.filtered_event_descriptions(target_index, k, maf, mrf, tsl, p, theta, sigma, session, [filter], cluster, logger=app.backend_logger)
    if not events:
        events = "No Result!"
    else:
        res = True

    print("END OF DETECTION")
    return jsonify({"result": res, "events":events})


# ==================================================================
# 3. Images
# ==================================================================
# TODO replace hard coded options
# we are rendering the images of the default index
@app.route('/images')
def images():
    # with open('twitter2015.json') as f:
    #     data = json.load(f)
    # TODO make this page compatible with multiple sources
    # instead of using default_source
    for es_sources in config['elastic_search_sources']:
        if es_sources['index'] == default_source:
            images_folder = es_sources['images_folder']
            with open(es_sources['image_duplicates']) as file:
                data = json.load(file)
    clusters_num = len(data['duplicates'])
    clusters = data['duplicates']
    clusters_url = []
    for image_url in clusters:
        clusters_url.append(images_folder + "/" + image_url[0])
    return render_template('images.html',
                           clusters_num=clusters_num,
                           clusters=clusters_url
                           )


# ==================================================================
# 4. Tweets
# ==================================================================

# Get Tweets
@app.route('/search_for_tweets', methods=['POST'])
# @cross_origin()
def search_for_tweets():
    data = request.form
    last_searched_tweets = functions.get_tweets(index=data['index'], word=data['word'], session=data['session'], label=data['search_by_label'])
    clusters = functions.get_clusters(index=data['index'], word=data['word'], session=data['session'], label=data['search_by_label'])
    clusters_stats = functions.get_clusters_stats(index=data['index'], word=data['word'], session=data['session'])
    return jsonify({"tweets": last_searched_tweets, "clusters": clusters, "clusters_stats": clusters_stats, "keywords": data['word'] })


# Get Just image clusters
@app.route('/search_for_image_clusters', methods=['POST'])
# @cross_origin()
def search_for_image_clusters():
    data = request.form
    clusters = functions.get_clusters(index=data['index'], session=data['session'], label=data['search_by_label'], limit=data['image_clusters_limit'])
    clusters_stats = functions.get_clusters_stats(index=data['index'], word=data['word'], session=data['session'])
    return jsonify({"clusters": clusters, "clusters_stats": clusters_stats, "keywords": data['word'] })


# Get Tweets
@app.route('/get_image_folder', methods=['POST'])
# @cross_origin()
def get_image_folder():
    data = request.form
    folder_name = functions.get_image_folder(data["index"])
    print("folder: ", folder_name)
    return folder_name



# Get Tweets
@app.route('/get_dataset_date_range', methods=['POST'])
# @cross_origin()
def get_dataset_date_range():
    data = request.form
    range = functions.get_dataset_date_range(index=data["index"])
    return jsonify(range)


# Get Tweets
@app.route('/search_bigrams_related_tweets', methods=['POST'])
# @cross_origin()
def search_bigrams_related_tweets():
    data = request.form
    word = (request.form.get('word', '')).strip()
    full_search = len(word) == 0

    propName = data["n-grams-to-generate"] + "grams"
    matching_tweets = ngram_classifier.search_bigrams_related_tweets(index=data['index'], word=word, session=data['session'],
                                                                     label=data['search_by_label'], ngram=data['ngram'],
                                                                     ngramsPropName=propName, full_search=full_search)
    return jsonify({"tweets": matching_tweets})





# Get Tweets
@app.route('/ngrams_with_higher_ocurrence', methods=['POST'])
# @cross_origin()
def ngrams_with_higher_ocurrence():
    data = request.form
    word = (request.form.get('word', '')).strip()
    full_search = len(word) == 0

    matching_ngrams = ngram_classifier.get_ngrams(index=data['index'], word=data['word'], session=data['session'],
                                                       label=data['search_by_label'], results_size=data['top-bubbles-to-display'],
                                                       n_size=data['n-grams-to-generate'], full_search=full_search)

    return jsonify({
        "total_matching_tweets": matching_ngrams['hits']['total'],
        "ngrams": matching_ngrams['aggregations']['ngrams_count']['buckets'],
        "classiffication": ngram_classifier.get_classification_data(index=data['index'], word=data['word'],
                                                                    session=data['session'],
                                                                    label=data['search_by_label'], matching_ngrams=matching_ngrams, full_search=full_search)
    })

# Get Tweets
@app.route('/event_ngrams_with_higher_ocurrence', methods=['POST'])
# @cross_origin()
def event_ngrams_with_higher_ocurrence():
    data = request.form
    source_index = data['index']
    event = json.loads(data['event'])
    main_term = event['main_term'].replace(",", " ")
    related_terms = event['related_terms']
    target_terms = functions.get_retated_terms(main_term, related_terms)
    results_size = request.form.get('top-bubbles-to-display', 20)
    n_size = request.form.get('n-grams-to-generate', '2')

    print("-SESSION:", data['session'])

    matching_ngrams = ngram_classifier.get_ngrams_for_event(index=data['index'], session=data['session'],
                                                            label=data['search_by_label'], results_size=results_size,
                                                            n_size=n_size, target_terms=target_terms)

    if(matching_ngrams and matching_ngrams['hits']):
        total_hits = matching_ngrams['hits']['total']
    else: total_hits = 0

    if (matching_ngrams and matching_ngrams['aggregations']):
        aggs = matching_ngrams['aggregations']['ngrams_count']['buckets']
    else:
        aggs = []

    return jsonify({
        "total_matching_tweets": total_hits,
        "ngrams": aggs
    })


# Get Tweets
@app.route('/search_event_bigrams_related_tweets', methods=['POST'])
# @cross_origin()
def search_event_bigrams_related_tweets():
    data = request.form

    event = json.loads(data['event'])
    main_term = event['main_term'].replace(",", " ")
    related_terms = event['related_terms']
    target_terms = functions.get_retated_terms(main_term, related_terms)

    propName = data["n-grams-to-generate"] + "grams"
    matching_tweets = ngram_classifier.search_event_bigrams_related_tweets(index=data['index'], target_terms=target_terms, session=data['session'],
                                                                     label=data['search_by_label'], ngram=data['ngram'],
                                                                     ngramsPropName=propName)
    return jsonify({"tweets": matching_tweets})


@app.route('/top_retweets', methods=['POST'])
# @cross_origin()
def top_retweets():
    data = request.form
    word = (request.form.get('word', '')).strip()
    full_search = len(word) == 0

    retweets = functions.top_retweets(index=data['index'], word=data['word'], session=data['session'],
                                      label=data['search_by_label'], full_search=full_search, retweets_number=data['retweets_number'])

    return jsonify(retweets)

# Get Tweets
@app.route('/generate_ngrams_for_index', methods=['POST'])
# @cross_origin()
def generate_ngrams_for_index():
    data = request.form
    #preproc = PreProcessor()
    propName = data['to_property']

    print("Generating ngrams for index: ", data['index'])

    start_time = datetime.datetime.now()
    print("Starting at: ", start_time)
    #preproc.putDocumentProperty(index=data['index'], prop=propName, prop_type='keyword')
    res = ngram_classifier.generate_ngrams_for_index(index=data['index'], length=int(data["ngrams_length"]), prop=propName)
    print("Starting at: ", start_time, " - Ending at: ", datetime.datetime.now())
    return jsonify(res)


# @app.route('/generate_ngrams_for_unlabeled_tweets_on_index', methods=['POST'])
# # @cross_origin()
# def generate_ngrams_for_unlabeled_tweets_on_index():
#     data = request.form
#     preproc = PreProcessor()
#     print(data)
#     propName = data['to_property']
#
#     start_time = datetime.datetime.now()
#     preproc.putDocumentProperty(index=data['index'], prop=propName, prop_type='keyword')
#     res = ngram_classifier.generate_ngrams_for_unlabeled_tweets_on_index(index=data['index'], length=int(data["ngrams_length"]), prop=propName)
#     print("Starting at: ", start_time, " - Ending at: ", datetime.datetime.now())
#     return jsonify(res)


# Get Tweets
@app.route('/get_current_backend_logs', methods=['GET'])
# @cross_origin()
def get_current_backend_logs():
    last_logs = ngram_classifier.get_current_backend_logs()
    # return a flag indicating when to stop asking for more logs (e.g. when the ending time is not set)
    return jsonify(last_logs)

# Get Tweets
@app.route('/tweets_filter', methods=['POST'])
# @cross_origin()
def tweets_filter():
    data = request.form
    tweets= functions.get_tweets_query_state(index=data['index'], word=data['word'], state=data['state'], session=data['session'])
    clusters= functions.get_clusters(index=data['index'], word=data['word'])
    clusters_stats = functions.get_clusters_stats(index=data['index'], word=data['word'], session=data['session'])
    return jsonify({"tweets": tweets, "clusters": clusters, "clusters_stats": clusters_stats})


@app.route('/tweets_scroll', methods=['POST'])
# @cross_origin()
def tweets_scroll():
    data = request.form

    print(data)
    tweets= functions.get_tweets_scroll(index=data['index'], sid=data['sid'], scroll_size=int(data['scroll_size']))
    return jsonify({"tweets": tweets})




def to_boolean(str_param):
    if isinstance(str_param, bool):
        return str_param
    elif str_param.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    else:
        return False

@app.route('/download_al_init_data', methods=['POST'])
# @cross_origin()
def download_al_init_data():
    data = request.form
    download_data = to_boolean(data["download_data"])
    debug_limit = to_boolean(data["debug_limit"])

    classifier.clean_directories()

    # download
    if(True==download_data): #This just downloads, then add code to copy to tmp_data
       classifier.download_data(cleaning_dirs=True, index=data["index"], session=data["session"],
                             gt_session=data["gt_session"], text_field=data["text_field"],
                             is_field_array=data["is_field_array"], debug_limit=debug_limit)

    return jsonify(True)


@app.route('/save_classification', methods=['POST'])
def save_classification():
    data = request.form
    classifier.save_classification(index=data["index"], session=data["session"]);
    return jsonify(True)


@app.route('/clear_al_logs', methods=['POST'])
def clear_al_logs():
    al_backend_logger.clear_logs()
    app.loop_index = 0
    return jsonify(True)


@app.route('/train_model', methods=['POST'])
# @cross_origin()
def train_model():
    data = request.form
    num_questions = int(data["num_questions"])
    max_samples_to_sort = int(data["max_samples_to_sort"])
    sampling_strategy = "closer_to_hyperplane"
    index = data["index"]
    session = data["session"]

    # Building the model and getting the questions
    model, X_train, X_test, y_train, y_test, X_unlabeled, categories, scores = classifier.build_model(
        num_questions=num_questions, remove_stopwords=False)

    print("Strategy: ", sampling_strategy)
    if (sampling_strategy == "closer_to_hyperplane"):
         questions = classifier.get_samples_closer_to_hyperplane(model, X_train, X_test, y_train, y_test,
                                                                      X_unlabeled, categories, num_questions)
    if (sampling_strategy == "closer_to_hyperplane_bigrams_rt"):
        questions = classifier.get_samples_closer_to_hyperplane_bigrams_rt(model, X_train, X_test, y_train, y_test,
                                                                       X_unlabeled, categories,
                                                                       num_questions,
                                                                       max_samples_to_sort=max_samples_to_sort,
                                                                       index=index,
                                                                       session=session,
                                                                       text_field=False,
                                                                       cnf_weight=1,
                                                                       ret_weight=0,
                                                                       bgr_weight=0)

    al_backend_logger.add_raw_log('{ "loop": ' + str(app.loop_index) +
                                    ', "datetime": "' + str(datetime.datetime.now()) +
                                    '", "accuracy": ' + str(scores["accuracy"]) +
                                    ', "precision": ' + str(scores["precision"]) + ' } \n')
    app.loop_index += 1

    return jsonify({"questions": questions, "scores": scores})


@app.route('/save_user_answers', methods=['POST'])
def save_user_answers():
    data = request.form
    answers = json.loads(data['answers'])

    classifier.move_answers_to_training_set(answers)
    classifier.remove_matching_answers_from_test_set(answers)

    return jsonify(True)


@app.route('/suggest_classification', methods=['POST'])
def suggest_classification():
    data = request.form

    target_min_score = float(data.get('target_min_score', '0'))
    target_max_score = float(data.get('target_max_score', '1'))

    positives, negatives = classifier.get_classified_queries_ids(target_min_score=target_min_score, target_max_score=target_max_score)
    return jsonify({
       "pos": ngram_classifier.get_ngrams_for_ids(index=data["index"], session=data["session"],
                                                  ids=positives, n_size="2", results_size=data["results_size"]),
       "neg": ngram_classifier.get_ngrams_for_ids(index=data["index"], session=data["session"],
                                                  ids=negatives, n_size="2", results_size=data["results_size"]),
       "total_pos": functions.get_total_tweets_by_ids(index=data["index"], session=data["session"], ids=positives),
       "total_neg": functions.get_total_tweets_by_ids(index=data["index"], session=data["session"], ids=negatives)
    })

@app.route('/get_tweets_by_str_ids', methods=['POST'])
def get_tweets_by_str_ids():
    data = request.form
    return jsonify(functions.get_tweets_by_str_ids(index=data['index'], id_strs=data["id_strs"]))


@app.route('/get_results_from_al_logs', methods=['POST'])
def get_results_from_al_logs():
    data = request.form

    hyp_results = []
    #session_files = [f for f in os.scandir(os.path.dirname(al_path)) if not f.is_dir()]  # and "_OUR_" in f.name]
    logs = classifier.read_file(al_path)  # session_files[0].path)
    loops_values, accuracies, precision = classifier.process_results(logs)
    hyp_results.append({"loops": loops_values, "accuracies": accuracies, "precisions": precision})

    return jsonify(hyp_results)  # classifier.get_results_from_al_logs())


@app.route('/most_frequent_n_grams', methods=['POST'])
def most_frequent_n_grams():

    data = request.form
    if data['top_ngrams_to_retrieve'] == '0':
        top_ngrams_to_retrieve = None
    else:
        top_ngrams_to_retrieve = int(data['top_ngrams_to_retrieve'])

    stemming = data['stemming'].lower() in ("yes", "true", "t", "1")
    remove_stopwords = data['remove_stopwords'].lower() in ("yes", "true", "t", "1")

    n_grams = ngram_classifier.most_frequent_n_grams(data['tweet_texts'], int(data['length']), top_ngrams_to_retrieve, remove_stopwords, stemming)
    return jsonify(n_grams)


@app.route('/most_frequent_ngrams_in_quadrant', methods=['POST'])
def most_frequent_ngrams_in_quadrant():

    data = request.form
    quadrant = data["quadrant"]  # low-pos high-pos low-neg high-neg
    n_grams = []
    ids = ["674200892065845249", "673977216393416704", "674163320639913984", "674023070017933312", "674139694154842112", "673996047534841856"]

    matching_ngrams = ngram_classifier.get_ngrams(index=data['index'], word=data['word'], session=data['session'],
                                                  label=data['search_by_label'],
                                                  results_size=data['top-bubbles-to-display'],
                                                  n_size=data['n-grams-to-generate'])

    return jsonify({
        "total_matching_tweets": matching_ngrams['hits']['total'],
        "ngrams": matching_ngrams['aggregations']['ngrams_count']['buckets'],
        "classiffication": ngram_classifier.get_classification_data(index=data['index'], word=data['word'],
                                                                    session=data['session'],
                                                                    label=data['search_by_label'],
                                                                    matching_ngrams=matching_ngrams)
    })

    return jsonify(n_grams)

@app.route('/n_grams_classification', methods=['POST'])
def n_grams_classification():

    data = request.form
    if data['top_ngrams_to_retrieve'] == '0':
        top_ngrams_to_retrieve = None
    else:
        top_ngrams_to_retrieve = int(data['top_ngrams_to_retrieve'])

    stemming = data['stemming'].lower() in ("yes", "true", "t", "1")
    remove_stopwords = data['remove_stopwords'].lower() in ("yes", "true", "t", "1")

    searchClassifier = NgramBasedClasifier()

    n_grams = searchClassifier.most_frequent_n_grams(data['tweet_texts'], int(data['length']), top_ngrams_to_retrieve, remove_stopwords, stemming)
    return jsonify(n_grams)


# Get Event related tweets
@app.route('/event_tweets', methods=['POST'])
# @cross_origin()
def event_tweets():
    data = request.form
    source_index = data['index']
    session = data['session']
    event = json.loads(data['obj'])
    main_term = event['main_term'].replace(",", " ")
    related_terms = event['related_terms']
    tweets = functions.get_event_tweets(source_index, main_term, related_terms)
    clusters = functions.get_event_clusters(source_index, main_term, related_terms)
    clusters_stats = functions.get_event_image_clusters_stats(source_index, main_term, related_terms, session)
    return jsonify({"tweets": tweets, "clusters": clusters, "clusters_stats": clusters_stats})


# Get Event related tweets
@app.route('/event_image_cluster_stats', methods=['POST'])
# @cross_origin()
def event_image_cluster_stats():
    data = request.form
    source_index = data['index']
    session = data['session']
    cluster_id = data['cid']

    clusters_stats = functions.get_single_event_image_cluster_stats(source_index, session, cluster_id)

    return jsonify(clusters_stats)


# Get Event related tweets
@app.route('/massive_tag_event_tweets', methods=['POST'])
# @cross_origin()
def massive_tag_event_tweets():
    data = request.form

    event = json.loads(data['event'])
    main_term = event['main_term'].replace(",", " ")
    related_terms = event['related_terms']

    res = functions.massive_tag_event_tweets(index=data['index'], session=data['session'], labeling_class=data['labeling_class'], main_term=main_term, related_terms=related_terms)
    return jsonify(res)


# Get Event related tweets
@app.route('/event_filter_tweets', methods=['POST'])
def event_filter_tweets():
    data = request.form
    source_index = data['index']
    state = data['state']
    session = data['session']
    event = json.loads(data['obj'])
    main_term = event['main_term'].replace(",", " ")
    related_terms = event['related_terms']
    tweets = functions.get_event_filter_tweets(source_index, main_term, related_terms, state, session)
    clusters = functions.get_event_clusters(source_index, main_term, related_terms)
    clusters_stats = functions.get_event_image_clusters_stats(source_index, main_term, related_terms, session)
    return jsonify({"tweets": tweets, "clusters": clusters, "clusters_stats": clusters_stats})


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
    s_name = data['s_name']
    event = json.loads(data['obj'])
    main_term = event['main_term'].replace(",", " ")
    related_terms = event['related_terms']
    image = functions.get_event_image(index, main_term, related_terms, s_name)
    res = False
    if image:
        image = image['hits']['hits'][0]['_source']
        res = True
    return jsonify({"result":res, "image": image})

@app.route('/all_events_images', methods=['POST'])
# @cross_origin()
def all_events_images():
    data = request.form
    index = data['index']
    s_name = data['s_name']
    events = json.loads(data['events'])
    images_by_event = []

    for event in events:
        main_term = event['main_term'].replace(",", " ")
        related_terms = event['related_terms']
        image = functions.get_event_image(index, main_term, related_terms, s_name)
        if image:
            image_src = image['hits']['hits'][0]['_source']['extended_entities']['media'][0]["media_url"]
            image_id = image['hits']['hits'][0]['_source']['id_str']
        else:
            image_src = "static/images/img.jpg"

        images_by_event.append({"cid": event["cid"], "image_id": image_id, "image_src": image_src})

    return jsonify(images_by_event)


# TODO replace hard coded options
# Test & Debug
@app.route('/mark_valid', methods=['POST', 'GET'])
# @cross_origin()
def mark_valid():
    data = request.form
    res = functions.set_all_status(default_source, default_session, "proposed")
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
    print(request.form)
    functions.set_tweet_state(index, session, tid, val)
    return jsonify(data)


@app.route('/mark_retweets', methods=['POST', 'GET'])
# @cross_origin()
def mark_retweets():
    data = request.form
    res = functions.set_retweets_state(index=data['index'], session=data['session'], tag=data['tag'], text=data['text'])
    return jsonify(res)


@app.route('/mark_bigram_tweets', methods=['POST', 'GET'])
# @cross_origin()
def mark_bigram_tweets():
    data = request.form
    propName=data["n-grams-to-generate"] + "grams"
    word = (request.form.get('word', '')).strip()
    full_search = len(word) == 0
    res = ngram_classifier.update_tweets_state_by_ngram(index=data['index'], word=word, session=data['session'],
                                               query_label=data['query_label'], new_label=data['new_label'],
                                               ngram=data['ngram'], ngramsPropName=propName, full_search=full_search)

    return jsonify(res)


@app.route('/mark_event_ngram_tweets', methods=['POST', 'GET'])
# @cross_origin()
def mark_event_ngram_tweets():
    data = request.form
    event = json.loads(data['event'])
    main_term = event['main_term'].replace(",", " ")
    related_terms = event['related_terms']
    target_terms = functions.get_retated_terms(main_term, related_terms)
    prop_name = request.form.get('n-grams-to-generate', '2') + "grams"

    res = ngram_classifier.update_tweets_state_by_event_ngram(index=data['index'], session=data['session'],
                                                              query_label=data['search_by_label'],
                                                              new_label=data['new_label'], target_terms=target_terms,
                                                              ngram=data['ngram'], ngramsPropName=prop_name)

    return jsonify(res)


@app.route('/mark_unlabeled_tweets', methods=['POST', 'GET'])
# @cross_origin()
def mark_unlabeled_tweets():
    data = request.form
    index = data['index']
    session = data['session']
    word= data['word']
    state = data['state']
    functions.mark_unlabeled_tweets(index, session, state, word)
    return jsonify(data)


@app.route('/mark_all_matching_tweets', methods=['POST', 'GET'])
def mark_all_matching_tweets():
    data = request.form
    index = data['index']
    session = data['session']
    word= data['word']
    state = data['state']
    functions.mark_all_matching_tweets(index, session, state, word)
    return jsonify(data)

# TODO replace hard coded options
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

# TODO replace hard coded options
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

    kn = KneeLocator(x, y2,direction="decreasing", curve='convex')  # invert=False was replaced by curve='convex'

    # print("kn.knee")
    # print(kn.knee)
    elbow = kn.knee
    if not elbow:
        elbow = KneeLocator(x, y2,direction="decreasing", curve='concave').knee

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
    total = functions.get_event_state_tweets_count(index, session, finalwords, "confirmed")
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

    # all_count = functions.get_all_count(index)
    # percentage = 100 * (count / all_count)
    # res = {'count': count}
    return jsonify({'results':results, 'elbow':sse_points2, 'newlist': newlist, 'step5':step5})


# ==================================================================
# Indexes
# ==================================================================

# Get available indexes
@app.route('/available_indexes', methods=['GET'])
def available_indexes():
    res = []
    for source in config['elastic_search_sources']:
        res.append(source['index'])
    print("Available indexes:", res)
    return jsonify(res);

# @app.route('/get_app_url', methods=['GET'])
# def get_app_url():
#
#     with open('config.json', 'r') as f:
#         config = json.load(f)
#
#     app_url = 'http://localhost:5000/'
#     print("APP URL: ", app_url)
#
#     return app_url
#     # return config['default']['app_url']

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
    s_index = data['s_index']
    app.backend_logger.clear_logs()
    res = functions.add_session(name, s_index, logger=app.backend_logger)
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
    session = {}
    if res:
        status = True
        for es_sources in config['elastic_search_sources']:
            if es_sources['index'] == res['_source']['s_index']:
                try:
                    session["images_folder"] = es_sources['images_folder']
                except KeyError:
                    # raise KeyError("Check config.json images_folder not set for index ", es_sources['index'])
                    print("Warning: the currnt session doesn't have an images_folder defined, and this might leat to some execution errors.")

    session["result"] = status
    session["body"] = res

    return jsonify(session)


# Get Session
@app.route('/get_mapping_spec', methods=['POST'])
# @cross_origin()
def get_mapping_spec():
    data = request.form
    return jsonify(functions.get_mapping_spec(data["index"], "tweet"))


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
    #
    # app.run(debug=True, host='localhost', port=5000, threaded=True, ssl_context=())
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
    # app.run(debug=False, host='mediamining.univ-lyon2.fr', port=5000, threaded=True)
