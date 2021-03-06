'''
This is an extension of the work of:
@author: afshin rahimi
Created on Jul 4, 2014
For more information about the original code, please visit:
https://github.com/afshinrahimi/activelearning
'''
import matplotlib
# matplotlib.use('Agg')
import json
import shutil
from mabed.functions import Functions

import os
import string
from time import time
import numpy as np
import pylab as pl
# from sklearn.feature_selection import SelectKBest, chi2
# from sklearn.linear_model import RidgeClassifier
# from sklearn.linear_model import SGDClassifier
# from sklearn.linear_model import Perceptron
# from sklearn.linear_model import PassiveAggressiveClassifier
# from sklearn.naive_bayes import BernoulliNB, MultinomialNB
# from sklearn.neighbors import KNeighborsClassifier
# from sklearn.neighbors import NearestCentroid
# from sklearn.ensemble import RandomForestClassifier
from sklearn.utils.extmath import density
from sklearn import metrics
from sklearn.model_selection import cross_validate  #by Gabi
import itertools
import shutil
from sklearn.feature_extraction import text
from classification.ngram_based_classifier import NgramBasedClasifier
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from mabed.functions import Functions
nltk.download('stopwords')

from sklearn.datasets import load_files
from collections import Counter
from elasticsearch import Elasticsearch
from elasticsearch import helpers
from mabed.es_connector import Es_connector
import elasticsearch.helpers
from elasticsearch_dsl import Search
from elasticsearch_dsl.connections import connections
# from sklearn.preprocessing import scale
from sklearn import preprocessing
#from elasticsearch.client import SnapshotClient


class ActiveLearning:

    # def __new__(cls):
    #     try:
    #         it = cls.__it__
    #     except AttributeError:
    #         it = cls.__it__ = object.__new__(cls)
    #     return it
    #
    # def __repr__(self):
    #     return '<{}>'.format(self.__class__.__name__.upper())
    #
    # def __eq__(self, other):
    #     return other is self

    def __init__(self, train_folder="train", test_folder="test", unlabeled_folder="unlabeled", session_folder_name="tmp_data", download_folder_name="original_tmp_data", sampler="", learner=""):
        # If session_folder and download_folder are different, donot forget to use clone_original_files to move the ones in the download folder to the session folder (the target one)

        self.DATA_FOLDER = os.path.join(os.getcwd(), "classification", session_folder_name)
        self.ORIGINAL_DATA_FOLDER = os.path.join(os.getcwd(), "classification", download_folder_name)

        self.ORIGINAL_TRAIN_FOLDER = os.path.join(self.ORIGINAL_DATA_FOLDER, train_folder)
        self.ORIGINAL_TEST_FOLDER = os.path.join(self.ORIGINAL_DATA_FOLDER, test_folder)
        self.ORIGINAL_UNLABELED_FOLDER = os.path.join(self.ORIGINAL_DATA_FOLDER, unlabeled_folder)

        self.TRAIN_FOLDER = os.path.join(self.DATA_FOLDER, train_folder)
        self.TEST_FOLDER = os.path.join(self.DATA_FOLDER, test_folder)
        self.TEST_FOLDER = os.path.join(self.DATA_FOLDER, test_folder)
        self.UNLABELED_FOLDER = os.path.join(self.DATA_FOLDER, unlabeled_folder)

        self.POS_CLASS_FOLDER = "confirmed"
        self.NEG_CLASS_FOLDER = "negative"
        self.NO_CLASS_FOLDER = "proposed"
        self.ENCODING = 'latin1'  # latin1
        self.loop_index = 0
        self.learner = learner

    def get_samples(self, num_questions):
        return self.sampler.get_samples(num_questions)

    def post_sampling(self, answers=None, config_relative_path=""):
        return self.sampler.post_sampling(answers=answers, config_relative_path=config_relative_path)

    def initialize(self, sampler, learner):
        self.sampler = sampler
        self.learner = learner
        sampler.set_classifier(self)

    def clone_original_files(self):
        #try:
        self.delete_folder_contents(self.DATA_FOLDER)

        shutil.copytree(self.ORIGINAL_DATA_FOLDER, self.DATA_FOLDER)
        # # Directories are the same
        # except shutil.Error as e:
        #     print('Directory not copied. Error: %s' % e)
        # # Any error saying that the directory doesn't exist
        # except OSError as e:
        #     print('Directory not copied. Error: %s' % e)

    def read_raw_tweets_from_elastic(self, **kwargs):

        elastic = Elasticsearch([{'host': kwargs["host"], 'port': kwargs["port"]}])

        raw_tweets = elastic.search(
            index=kwargs["index"],
            doc_type="tweet",
            body=kwargs["query"],
            _source=kwargs["_source"],
            request_timeout=kwargs["request_timeout"]
        )

        return raw_tweets['hits']['hits']

    def download_tweets_from_elastic(self, **kwargs):

        debug_limit = kwargs.get("debug_limit", False)
        log_enabled = kwargs.get("log_enabled", True)

        if "config_relative_path" in kwargs:
            my_connector = Es_connector(index=kwargs["index"], doc_type="tweet", config_relative_path=kwargs["config_relative_path"])
        else: my_connector = Es_connector(index=kwargs["index"], doc_type="tweet")  #  config_relative_path='../')

        res = my_connector.init_paginatedSearch(kwargs["query"])
        sid = res["sid"]
        scroll_size = res["scroll_size"]
        total = int(res["total"])
        processed=len(res["results"])

        self.write_data_in_folders(kwargs["field"], kwargs["folder"], res["results"])

        while scroll_size > 0:
            res = my_connector.loop_paginatedSearch(sid, scroll_size)
            scroll_size = res["scroll_size"]
            processed += len(res["results"])

            # Writing the retrieved files into the folders
            self.write_data_in_folders(kwargs["field"], kwargs["folder"], res["results"])
            if log_enabled:
                print("Downloading: ", round(processed * 100 / total, 2), "%")

            if debug_limit:
                print("\nDEBUG LIMIT\n")
                res = my_connector.loop_paginatedSearch(sid, scroll_size)
                self.write_data_in_folders(kwargs["field"], kwargs["folder"], res["results"])
                scroll_size = 0

        return total

    def get_langs_from_unlabeled_tweets(self, **kwargs):

        # TODO: we need to execute this in case the user doesn't have it enabled. I can't find the
        # PUT / twitterfdl2017 / _mapping / tweet
        # {
        #     "properties": {
        #         "lang": {
        #             "type": "text",
        #             "fielddata": true
        #         }
        #     }
        # }

        the_host = "http://" + kwargs["host"] + ":" + kwargs["port"]
        client = connections.create_connection(hosts=[the_host])
        s = Search(using=client, index=kwargs["index"], doc_type="tweet")

        body = {
            "size": 0,
            "aggs": {
                "distinct_lang": {
                    "terms": {
                        "field": "lang",
                        "size": 1000
                    }
                }
            }
        }

        s = Search.from_dict(body)
        s = s.index(kwargs["index"])
        s = s.doc_type("tweet")
        body = s.to_dict()

        t = s.execute()

        distinct_langs = []
        for item in t.aggregations.distinct_lang:
            # print(item.key, item.doc_count)
            distinct_langs.append(item.key)


        return distinct_langs

    def delete_folder_contents(self, folder):

        print("Removing folder: ", folder)
        if os.path.exists(folder):
            # os.remove(folder)
            shutil.rmtree(folder)

            # for the_file in os.listdir(folder):
            #     file_path = os.path.join(folder, the_file)
            #     try:
            #         if os.path.isfile(file_path):
            #             os.unlink(file_path)
            #         # elif os.path.isdir(file_path): shutil.shutil.rmtree(file_path)(file_path)
            #     except Exception as e:
            #         print(e)


    def writeFile(self, fullpath, content):
        file = open(fullpath, "w", encoding='utf-8')
        file.write(content)
        file.close()

    def get_unlabeled_ids(self):

        proposed_path = os.path.join(self.UNLABELED_FOLDER, self.NO_CLASS_FOLDER)
        unlabeled_files = [f.path for f in os.scandir(proposed_path)]
        unlabeled_ids = []

        for file_path in unlabeled_files:
            name = os.path.basename(os.path.normpath(file_path))
            name = os.path.splitext(name)[0]
            unlabeled_ids.append(name)

        return unlabeled_ids

    def get_unique_sorted_samples_by_conf(self, sorted_samples_by_conf, data_unlabeled, max_docs):

        top_samples_indexes = []
        top_samples_text = []

        for index in sorted_samples_by_conf.tolist(): # Sorted from lower to higher confidence (lower = closer to the hyperplane)

            file_textual_content = self.data_unlabeled.data[index]
            if file_textual_content not in top_samples_text:  # text
                top_samples_text.append(file_textual_content)
                top_samples_indexes.append(index)

            if len(top_samples_indexes) == max_docs:
                break

        return top_samples_indexes

    def get_top_retweets(self, **kwargs):

        functions = Functions()  # config_relative_path='../')
        retweets = functions.top_retweets(index=kwargs['index'], session=kwargs['session'], full_search=True,
                                          label='proposed', retweets_number=kwargs['results_size'])

        try:
            buckets = []
            for bucket in retweets["aggregations"]["top_text"]["buckets"]:
                if bucket["doc_count"] > 1:
                    buckets.append(bucket)

            return buckets
        except KeyError as e:
            return []

    def get_top_bigrams(self, **kwargs):

        ngram_classifier = NgramBasedClasifier() #  config_relative_path='../')
        matching_ngrams = ngram_classifier.get_ngrams(index=kwargs['index'], session=kwargs['session'],
                                                      label='proposed', results_size=kwargs['results_size'],
                                                      n_size="2", full_search=True)

        try:
            return matching_ngrams["aggregations"]["ngrams_count"]["buckets"]
        except KeyError as e:
            return []

    # def classify_accurate_quartiles(self, **kwargs):  # min_acceptable_accuracy min_high_confidence
    #
    #
    #     return
    #
    # def get_quartiles(self, sorted_samples):
    #
    #     min_high_conf = round(sorted_samples.size * 0.75)
    #     high_conf_samples = sorted_samples[-min_high_conf:]

    def clean_directories(self):
        print("Cleaning directories")
        # Used in the experiment
        # self.delete_folder_contents(os.path.join(self.ORIGINAL_TRAIN_FOLDER, self.POS_CLASS_FOLDER))
        # self.delete_folder_contents(os.path.join(self.ORIGINAL_TRAIN_FOLDER, self.NEG_CLASS_FOLDER))
        # self.delete_folder_contents(os.path.join(self.ORIGINAL_TEST_FOLDER, self.POS_CLASS_FOLDER))
        # self.delete_folder_contents(os.path.join(self.ORIGINAL_TEST_FOLDER, self.NEG_CLASS_FOLDER))
        # self.delete_folder_contents(os.path.join(self.ORIGINAL_UNLABELED_FOLDER, self.NO_CLASS_FOLDER))
        self.delete_folder_contents(self.ORIGINAL_DATA_FOLDER)
        self.delete_folder_contents(self.DATA_FOLDER)

    def read_data_from_dataset(self, **kwargs):

        target_source = ["id_str", kwargs["field"], "imagesCluster", kwargs["session"]]

        # Getting a sample from elasticsearch to classify
        confirmed_data = self.read_raw_tweets_from_elastic(
            index= kwargs["index"],
            doc_type="tweet",
            host="localhost",
            port="9200",
            query={
            "query": {
                    "match": {
                        kwargs["session"]: "confirmed"
                    }
                }
            },
            _source=target_source,
            request_timeout=30
        )
        negative_data = self.read_raw_tweets_from_elastic(
            index=kwargs["index"],
            doc_type="tweet",
            host="localhost",
            port="9200",
            query={"query": {
                "match": {
                    kwargs["session"]: "negative"
                }
            }},
            _source=target_source,
            request_timeout=30
        )

        return confirmed_data, negative_data

    def stringuify(self, field):

        if isinstance(field, list):
            return " ".join(field)
        else: return field

    def write_data_in_folders(self, field, path, dataset):

        if not os.path.exists(path):
             os.makedirs(path)

        for tweet in dataset:
            try:
                self.writeFile(os.path.join(path, tweet['_source']['id_str'] + ".txt"), self.stringuify(tweet['_source'][field]))
            except KeyError as ke:
               print("Key value missing, maybe this document doesn't have the 'id_str' or the '" + field + "' fields.")

    def size_mb(self, docs):
        return sum(len(s.encode('utf-8')) for s in docs) / 1e6

    def loading_tweets_from_files(self, download_test=True):

        # Loading the datasets
        print("Loading training data from ", self.TRAIN_FOLDER)
        data_train = load_files(self.TRAIN_FOLDER, encoding=self.ENCODING)  # data_train

        if download_test:
            print("Loading testing data from ", self.TEST_FOLDER)
            data_test = load_files(self.TEST_FOLDER, encoding=self.ENCODING)
        else: data_test = None

        print("Loading target data from ", self.UNLABELED_FOLDER)
        unlabeled = load_files(self.UNLABELED_FOLDER, encoding=self.ENCODING)

        print("Loading categories")
        categories = data_train.target_names

        # data_train_size_mb = self.size_mb(data_train.data)
        # data_test_size_mb = self.size_mb(data_test.data)
        # unlabeled_size_mb = self.size_mb(unlabeled.data)
        #
        # print("%d documents - %0.3fMB (training set)" % (
        #     len(data_train.data), data_train_size_mb))
        # print("%d documents - %0.3fMB (test set)" % (
        #     len(data_test.data), data_test_size_mb))
        # print("%d documents - %0.3fMB (unlabeled set)" % (
        #     len(unlabeled.data), unlabeled_size_mb))
        # print("%d categories" % len(categories), categories)

        return data_train, data_test, unlabeled, categories

    def get_langs_from_unlabeled_data(self, **kwargs):

        try:
            langs = self.get_langs_from_unlabeled_tweets(
                index=kwargs["index"],
                doc_type="tweet",
                host="localhost",
                port="9200"
            )
            return langs
        except:
            print("An exception occurred with get_langs_from_unlabeled_tweets. Using english and french stopwords instead.")
            return ["en", "fr"]

    def get_stopwords_for_langs(self, langs):

        swords = []
        if "en" in langs:
            swords = swords + stopwords.words('english')
        if "fr" in langs:
            swords = swords + stopwords.words('french')
        if "ar" in langs:
            swords = swords + stopwords.words('arabic')
        if "nl" in langs:
            swords = swords + stopwords.words('dutch')
        if "id" in langs:
            swords = swords + stopwords.words('indonesian')
        if "fi" in langs:
            swords = swords + stopwords.words('Finnish')
        if "de" in langs:
            swords = swords + stopwords.words('German')
        if "hu" in langs:
            swords = swords + stopwords.words('Hungarian')
        if "it" in langs:
            swords = swords + stopwords.words('Italian')
        if "nb" in langs:
            swords = swords + stopwords.words('Norwegian')
        if "pt" in langs:
            swords = swords + stopwords.words('Portuguese')
        if "ro" in langs:
            swords = swords + stopwords.words('Romanian')
        if "ru" in langs:
            swords = swords + stopwords.words('Russian')
        if "es" in langs:
            swords = swords + stopwords.words('spanish')
        if "sv" in langs:
            swords = swords + stopwords.words('Swedish')
        if "tr" in langs:
            swords = swords + stopwords.words('Turkish')

        # TODO: complete with the full list of supported langs (there are some langs supported but miissing  and not documented. E.g. Bulgarian or Ukrainian https://pypi.org/project/stop-words/ )
        # The full list of languages may be found in C:/Users/username/AppData/Roming/nltk_data/corpora/stopwords

        return swords

    def save_classification(self, **kwargs):

        # Update the status of the training folder (since we moved some unlabeled files there)
        self.save_training_classification(**kwargs)

        #
        # this.get_classified_document_ids();

    def save_training_classification(self, **kwargs):

        # Update the status of the training folder (since we moved some unlabeled files there)

        confirmed_ids = []
        for file in os.listdir(os.path.join(self.TRAIN_FOLDER, self.POS_CLASS_FOLDER)):
            if file.endswith(".txt"):
                confirmed_ids.append(os.path.splitext(file)[0])

        self.update_documents_status_by_id(docs_ids=confirmed_ids, tag="confirmed", **kwargs)

        negative_ids = []
        for file in os.listdir(os.path.join(self.TRAIN_FOLDER, self.NEG_CLASS_FOLDER)):
            if file.endswith(".txt"):
                negative_ids.append(os.path.splitext(file)[0])

        self.update_documents_status_by_id(docs_ids=negative_ids, tag="negative", **kwargs)

    def update_documents_status_by_id(self, **kwargs):

        if len(kwargs["docs_ids"]) == 0:
            return

        # print("Recording...", kwargs["tag"], kwargs["docs_ids"])
        matching_queries = []
        for doc_id in kwargs["docs_ids"]:
            matching_queries.append({"match": {"id_str": doc_id }})

            if len(matching_queries) == 500:
                self.update_documents_status_by_match(matching_queries=matching_queries, **kwargs)
                matching_queries = []

        if len(matching_queries) > 0:
            self.update_documents_status_by_match(matching_queries=matching_queries, **kwargs)


    def update_documents_status_by_match(self, **kwargs):

        my_connector = Es_connector(index=kwargs["index"], doc_type="tweet")  # config_relative_path='../')
        query = {
            "query": {
                "bool": {
                    "should": kwargs["matching_queries"],
                    "minimum_should_match": 1,
                    "must": [{
                        "match": {kwargs["session"]: "proposed"}
                    }]
                }
            }
        }
        return my_connector.update_by_query(query, "ctx._source." + kwargs["session"] + " = '" + kwargs["tag"] + "'")

    def download_data(self, **kwargs):

        self.clean_directories()
        self.download_training_data(index=kwargs["index"], session=kwargs["session"],
                                               field=kwargs["text_field"],
                                               debug_limit=kwargs["debug_limit"])
        self.download_unclassified_data(index=kwargs["index"], session=kwargs["session"],
                                                   field=kwargs["text_field"],
                                                   debug_limit=kwargs["debug_limit"])
        self.download_testing_data(index=kwargs["index"], session=kwargs["gt_session"],
                                              field=kwargs["text_field"],
                                              debug_limit=kwargs["debug_limit"])
        self.remove_docs_absent_in_training()

    def remove_docs_absent_in_training(self):

        dirs_to_check = [
            os.path.join(self.ORIGINAL_UNLABELED_FOLDER, self.NO_CLASS_FOLDER),
            os.path.join(self.ORIGINAL_TEST_FOLDER, self.NEG_CLASS_FOLDER),
            os.path.join(self.ORIGINAL_TEST_FOLDER, self.POS_CLASS_FOLDER)
        ]
        train_pos_folder = os.path.join(self.ORIGINAL_TRAIN_FOLDER, self.POS_CLASS_FOLDER)
        train_neg_folder = os.path.join(self.ORIGINAL_TRAIN_FOLDER, self.NEG_CLASS_FOLDER)

        filenames = [file for file in os.listdir(train_pos_folder)] + [file for file in os.listdir(train_neg_folder)]
        files_ignored = set()

        for training_file in filenames:
            file_exists = False

            for dir_to_check in dirs_to_check:
                file_exists = os.path.exists(os.path.join(dir_to_check, training_file))
                if not file_exists:
                    files_ignored.add(training_file)
                    self.delete_file(filename=training_file, dir=dir_to_check)

        print("\n\nIgnoring unclassified tweets from groundtruth. Total ignored: ", len(files_ignored))
        #print("\nFiles: ", files_ignored, "\n\n")

    def delete_file(self, filename, dir):

        path = os.path.join(dir, filename)
        if os.path.exists(path):
            os.remove(path)

    def download_testing_data(self, **kwargs):

        unlabeled_dir = os.path.join(self.ORIGINAL_UNLABELED_FOLDER, self.NO_CLASS_FOLDER)
        # Traversing all unlabeled files to download the testing set accordingly
        accum_ids = []
        processed = 0
        total = len(os.listdir(unlabeled_dir)) # dir is your directory path

        print("Getting (+) TEsting data from the elastic index: ", kwargs["index"])
        for file in os.listdir(unlabeled_dir):
            if file.endswith(".txt"):
                accum_ids.append({
                    "_source": {
                        "id_str": os.path.splitext(file)[0]
                    }
                })
                if len(accum_ids)==500:
                    self.download_paginated_testing_data(log_enabled=False, target_tweets=accum_ids, **kwargs)
                    processed = processed + len(accum_ids)
                    accum_ids = []
                    print("Downloading: ", round(processed * 100 / total, 2), "%")

        if len(accum_ids)>0:
            self.download_paginated_testing_data(log_enabled=False, target_tweets=accum_ids, **kwargs)
            processed = processed + len(accum_ids)
            print("Downloading: ", round(processed * 100 / total, 2), "%")

        # if confirmed_data == 0 or negative_data == 0:
        #     raise Exception('You need to have some already classified data in your testing/groundtruth dataset')
        #

    def download_paginated_testing_data(self, ** kwargs):

        matching_queries = []
        for tweet in kwargs["target_tweets"]:
            matching_queries.append({"match": {"id_str": tweet["_source"]["id_str"]}})

        confirmed_data = self.download_tweets_from_elastic(
            log=False,
            folder=os.path.join(self.ORIGINAL_TEST_FOLDER, self.POS_CLASS_FOLDER),
            query={
                "query": {
                    "bool": {
                        "should": matching_queries,
                        "minimum_should_match": 1,
                        "must":[{
                            "match":{ kwargs["session"] :"confirmed" }
                        }]
                    }
                }
            },
            **kwargs
        )

        negative_data = self.download_tweets_from_elastic(
            folder=os.path.join(self.ORIGINAL_TEST_FOLDER, self.NEG_CLASS_FOLDER),
            query={
                "query": {
                    "bool": {
                        "should": matching_queries,
                        "minimum_should_match": 1,
                        "must": [{
                            "match": {kwargs["session"]: "negative"}
                        }]
                    }
                }
            },
            **kwargs
        )

    def download_training_data(self, **kwargs):

        print("Getting (+) TRaining data from the elastic index: ", kwargs["index"])
        confirmed_data = self.download_tweets_from_elastic(
            folder=os.path.join(self.ORIGINAL_TRAIN_FOLDER, self.POS_CLASS_FOLDER),
            query={"query": {
                "match": {
                    kwargs["session"]: "confirmed"
                }
            }},
            **kwargs
        )

        print("Getting (-) TRaining data from the elastic index: ", kwargs["index"])
        negative_data = self.download_tweets_from_elastic(
            folder=os.path.join(self.ORIGINAL_TRAIN_FOLDER, self.NEG_CLASS_FOLDER),
            query={"query": {
                "match": {
                    kwargs["session"]: "negative"
                }
            }},
            **kwargs
        )

        if confirmed_data == 0 or negative_data == 0:
            raise Exception('You need to have some already classified data in your dataset')


    def download_unclassified_data(self, **kwargs):

        print("Getting UNclassified data from the elastic index: ", kwargs["index"])

        total_proposed_data = self.download_tweets_from_elastic(
            folder=os.path.join(self.ORIGINAL_UNLABELED_FOLDER, self.NO_CLASS_FOLDER),
            query={"query": {
                "match": {
                    kwargs["session"]: "proposed"
                }
            }},
            **kwargs
        )

        if total_proposed_data == 0:
            raise Exception('You need to have some data to classify in your dataset')

    def build_model(self, **kwargs): # to use from the experiment

        # Keep track of the last used params
        self.remove_stopwords = kwargs["remove_stopwords"]

        # Starting the process
        data_train, data_test, self.data_unlabeled, self.categories = self.loading_tweets_from_files()

        # Train the model: vectorize, make predictions, get scores, confidences, etc
        self.last_confidences, self.last_predictions, self.X_unlabeled, self.scores = self.learner.train_model(data_train, data_test, self.data_unlabeled, self.ENCODING, self.categories)


    def fill_questions(self, conf_sorted_question_samples, predictions, confidences, categories, top_retweets=[], top_bigrams=[], max_samples_to_sort=500, text_field=""):

        # AT THIS POINT IT LEARNS OR IT USES THE DATA
        # print("max_samples_to_sort: ", max_samples_to_sort)
        complete_question_samples = []
        i=0

        get_confidences = False
        if isinstance(confidences,np.ndarray):
            get_confidences = True

        for index in conf_sorted_question_samples: # Sorted from lower to higher confidence (lower = closer to the hyperplane)

            conf = None
            if get_confidences:
                conf = confidences[index]

            question ={
                "filename": self.data_unlabeled.filenames[index],
                "analyzed_content": self.data_unlabeled.data[index],
                "str_id": self.extract_filename_no_ext(self.data_unlabeled.filenames[index]),
                "pred_label": categories[int(predictions[index])],
                "data_unlabeled_index": index,
                "confidence": conf,
                "cnf_pos": i,
                "ret_pos": max_samples_to_sort,
                "bgr_pos": max_samples_to_sort,
            }
            i+=1

            #Adding the score according to teh retweets
            j=0
            for retweet in top_retweets:  # Sorted from most to lower retweets
                try:
                    target_field = retweet["top_text_hits"]["hits"]["hits"][0]["_source"][text_field]
                    if isinstance(target_field, list):
                        analyzed_content = ' '.join(target_field)  # TODO: FIXED POINT! this will fail if we download the text of the tweet instead of the bigram. We are receiving this field as text_field
                    else: analyzed_content = target_field

                    if analyzed_content == question["analyzed_content"]:
                        question["ret_pos"] = j
                    break
                except KeyError:
                    raise Exception("Tweet without a 2gram")
                j+=1

            #Adding the score according to the bigrams
            j = 0
            for bigram in top_bigrams:  # Sorted from most to lower retweets

                if bigram["key"] in question["analyzed_content"]:
                    question["bgr_pos"] = j
                    break

                j += 1

            complete_question_samples.append(question)

        return complete_question_samples


    # def update_answers_labels_in_index(self, labeled_questions, index, session):
    #
    #     print("Marking answers in elastic")
    #     for question in labeled_questions:
    #         #print("Moving", question["filename"], " to ", dstDir)
    #         try:
    #             Es_connector(index=index).update_by_query({
    #                 "query": {
    #                     "match": {
    #                         "id_str": question["filename"]
    #                     }
    #                 }
    #             }, "ctx._source." + session + " = '" + question["label"] + "'")
    #         except:
    #             print("...")
    #
    #             {
    #                 "script": {
    #                     "source": "ctx._source.session_lyon2017_test_03 = params.label",
    #                     "params": {
    #                         "label": "proposed"
    #                     }
    #                 },
    #                 "query": {
    #                     "match": {
    #                         "id_str": "..."
    #                     }
    #                 }
    #             }

    def move_answers_to_training_set(self, labeled_questions):

        print("Moving docs into the training subfolders")
        for question in labeled_questions:
            basename = os.path.basename(question["filename"])
            dstDir = os.path.join(self.TRAIN_FOLDER, question["label"], basename)
            #print("Moving", question["filename"], " to ", dstDir)
            try:
                shutil.move(question["filename"], dstDir)
            except:
                pass  # print("...") #""Error: the file was not found in the training folder")  # This may happen since we are retrieving all the docs (we do not make changes in the dataset until the end of the process)

    def remove_matching_answers_from_test_set(self, labeled_questions):

        # print("Moving the user labeled questions into the proper folders")
        for question in labeled_questions:
            basename = os.path.basename(question["filename"])
            file_path = os.path.join(self.TEST_FOLDER, question["label"], basename)
            if os.path.exists(file_path):
                os.remove(file_path)

    def get_tweets_for_validation(self):

        full_queries = self.get_full_queries()
        return

    # def get_classified_queries_ids(self):
    #     positives = []
    #     negatives = []
    #
    #     for index in self.last_samples:
    #
    #         id_str = self.extract_filename_no_ext(self.data_unlabeled.filenames[index])
    #         pred_label = self.categories[int(self.last_predictions[index])]
    #
    #         if (pred_label == "confirmed"):
    #             positives.append(id_str)
    #         else:
    #             negatives.append(id_str)
    #
    #     return positives, negatives

    def get_config_value(self, prop_name, full_text):
        start_index = full_text.index(prop_name) + 4
        end_index = start_index + 3

        return full_text[start_index:end_index]

    def get_config_name(self, full_text):

        cnf = str(int(float(self.get_config_value("_cnf", full_text)) * 100))
        ret = str(int(float(self.get_config_value("_ret", full_text)) * 100))
        bgr = str(int(float(self.get_config_value("_bgr", full_text)) * 100))

        return cnf + "·" + ret + "·" + bgr

    def get_value_at_loop(self, prop_name, loop_index, logs):

        target_loop = [log for log in logs if log["loop"] == loop_index]

        return target_loop[0]

    def read_file(self, path):
        file = open(path, "r")
        logs = '['
        for line in file:
            line = line.replace('", "f1"', ', "f1"')
            line = line.replace('", "recall"', ', "recall"')
            line = line.replace('", "precision"', ', "precision"')
            line = line.replace('", "wrong_pred_answers"', ', "wrong_pred_answers"')

            logs = logs + line
        logs = logs[:-1]
        logs = logs + ']'
        return json.loads(logs.replace('\n', ','))

    def process_results(self, logs):
        loop_logs = [log for log in logs if 'loop' in log]

        loops_values = [log["loop"] for log in logs if 'loop' in log]  # datetime
        accuracies = [log["accuracy"] for log in logs if 'loop' in log]
        precision = [log["precision"] for log in logs if 'loop' in log]

        return loops_values, accuracies, precision

    def update_tmp_predictions(self, **kwargs):

        # self.clear_tmp_predictions(**kwargs)
        # mark all as negative
        # self.mark_full_unlabeled_set_as(as_category="negative", field=kwargs["session"] + "_tmp", **kwargs)
        self.mark_tmp_predictions(as_category="negative", field=kwargs["session"] + "_tmp", subset=kwargs["negatives"], **kwargs)
        # then mark positives
        self.mark_tmp_predictions(as_category="confirmed", field=kwargs["session"] + "_tmp", subset=kwargs["positives"], **kwargs)

    def clear_tmp_predictions(self, **kwargs):

        my_connector = Es_connector(index=kwargs["index"], doc_type="tweet")  # config_relative_path='../')
        res = my_connector.update_by_query({
            "query": {
                "exists" : { "field" : kwargs["session"] + "_tmp" }  # e.g. session_lyon2015_test_01_tmp
            }
        }, "ctx._source." + kwargs["session"] + "_tmp = 'proposed'")  #"ctx._source.remove('" + kwargs["session"] + "_tmp')")

    def remove_tmp_predictions_field(self, **kwargs):

        my_connector = Es_connector(index=kwargs["index"], doc_type="tweet")  # config_relative_path='../')

        for answer in kwargs["answers"]:
            res = my_connector.update_by_query({
                "query": {
                    "match": {
                        "_id": answer["id"]
                    }
                }
            }, "ctx._source.remove('" + kwargs["session"] + "_tmp')")

    def remove_all_tmp_predictions_field(self, **kwargs):

        print("Removing all the predictions")
        Es_connector(index=kwargs["index"], doc_type="tweet").update_by_query({
            "query": {
                "exists": { "field" : kwargs["field"]}
            }
        }, "ctx._source.remove('" + kwargs["field"] + "')")


    def mark_full_unlabeled_set_as(self, **kwargs):

        Es_connector(index=kwargs["index"], doc_type="tweet").update_by_query({
            "query": {
                "bool": {
                  "must_not": [
                    {
                      "match": {
                        kwargs["field"]: kwargs["as_category"]
                      }
                    }
                  ]
                }
            }
        }, "ctx._source." + kwargs["field"] + " = '" + kwargs["as_category"] + "'")

    def get_sampler_class_name(self):

        return self.sampler.__class__.__name__

    def get_learner_class_name(self):

        return self.learner.__class__.__name__

    def get_vectorizer_class_name(self):

        return self.learner.get_vectorizer_class_name()

    def mark_tmp_predictions(self, **kwargs):

        print("Bulk: marking " + kwargs["as_category"] + " predictions")
        # Bulk
        query_list = []
        for id in kwargs["subset"]:
            query_dict = {
                '_op_type': 'update',
                '_index': kwargs["index"],
                '_type': "tweet",
                '_id': id,
                'doc': {kwargs["field"]: kwargs["as_category"]}
            }
            query_list.append(query_dict)

        helpers.bulk(client= Es_connector(index=kwargs["index"], doc_type="tweet").es, actions=query_list)


    def get_classified_queries_ids(self, **kwargs):

        # middle_conf = np.average(self.last_confidences) # TODO: ask it from frontend
        pos_ids = []
        neg_ids = []

        confidences = []
        for index in self.sampler.last_samples:  # Sorted from lower to higher confidence (lower = closer to the hyperplane)
            confidences.append(self.last_confidences[index])
        min_conf = min(confidences)
        max_conf = max(confidences)

        for smple in self.sampler.last_samples:  # Sorted from lower to higher confidence (lower = closer to the hyperplane)

            id_str = self.extract_filename_no_ext(self.data_unlabeled.filenames[smple])
            print(id_str, "from", self.data_unlabeled.filenames[smple])
            pred_label = self.categories[int(self.last_predictions[smple])]
            scaled_confidence = (self.last_confidences[smple] - min_conf) / (max_conf - min_conf)

            if(scaled_confidence > kwargs["target_min_score"]) and (scaled_confidence < kwargs["target_max_score"]):
                if (pred_label == "confirmed"):
                    pos_ids.append(id_str)
                else:
                    neg_ids.append(id_str)

        return pos_ids, neg_ids

    def get_classified_document_ids(self, predictions, confidences, **kwargs):

        positiveTweets = {}
        positiveTweets["confidences"] = []
        positiveTweets["filenames"] = []
        positiveTweets["predictions"] = []
        positiveTweets["texts"] = []

        negativeTweets = {}
        negativeTweets["confidences"] = []
        negativeTweets["filenames"] = []
        negativeTweets["predictions"] = []
        negativeTweets["texts"] = []

        # TODO: check that 1 = positive and 0 = negative in the model updating function
        for idx, val in enumerate(predictions[0]):
            if predictions[0][idx] == 1:
                positiveTweets["confidences"].append(str(confidences[0][idx]))
                positiveTweets["filenames"].append(self.extract_filename_no_ext(self.data_unlabeled.filenames[idx]))
                positiveTweets["predictions"].append(str(predictions[0][idx]))
                positiveTweets["texts"].append(self.data_unlabeled.data[idx]) # self.data_unlabeled is updated when updating the model > self.build_model

            elif predictions[0][idx] == 0:
                negativeTweets["confidences"].append(str(confidences[0][idx]))
                negativeTweets["filenames"].append(self.extract_filename_no_ext(self.data_unlabeled.filenames[idx]))
                negativeTweets["predictions"].append(str(predictions[0][idx]))
                negativeTweets["texts"].append(self.data_unlabeled.data[idx])

        return {"positiveTweets": positiveTweets, "negativeTweets": negativeTweets}

    def extract_filename_no_ext(self, fullpath):
        base = os.path.basename(fullpath)
        return os.path.splitext(base)[0]

    def n_grams(self, text, length=2):
        return zip(*[text[i:] for i in range(length)])

        # word_data = "The best performance can bring in sky high success."
        # nltk_tokens = nltk.word_tokenize(word_data)
        #
        # print(list(nltk.bigrams(nltk_tokens)))

    def most_frequent_n_grams(self, tweet_texts, length=2, top_ngrams_to_retrieve=None, remove_stopwords=True, stemming=True):

        full_text = "".join(tweet_texts)
        #print(full_text)

        if remove_stopwords:
            punctuation = list(string.punctuation + "…" + "..." + "’" + "️" + "'" + '🔴' + '•')
            multilang_stopwords = self.get_stopwords_for_langs(self.langs) + ["Ã", "RT"] + punctuation
            tokenized_text = word_tokenize(full_text)  # tknzr = TweetTokenizer()             tokenized_text = tknzr.tokenize(full_text)
            #print("Detected tokens:", len(tokenized_text), tokenized_text)
            filtered_words = list(filter(lambda word: word not in multilang_stopwords, tokenized_text))
            #print("Tokens after removing stop-words:", len(filtered_words), filtered_words)
            full_text = " ".join(filtered_words)
            #print("FULL TEXT", full_text)

        ngram_counts = Counter(self.n_grams(full_text.split(), length))
        return ngram_counts.most_common(top_ngrams_to_retrieve)

    def get_duplicated_answers(self, **kwargs):

        my_connector = Es_connector(index=kwargs["index"])  # , config_relative_path='../')
        duplicated_docs=[]

        # IT SHOULD BE BETTER TO TRY GETTING THE DUPLICATES FROM THE MATRIX
        splitted_questions = []
        target_bigrams = []
        for question in kwargs["questions"]:

            splitted_questions.append(question)
            if(len(splitted_questions)>99):
                matching_docs = self.process_duplicated_answers(my_connector, kwargs["session"], splitted_questions, kwargs["text_field"], kwargs["similarity_percentage"])
                duplicated_docs += matching_docs
                splitted_questions=[] # re init

        if len(splitted_questions)>0:
            matching_docs = self.process_duplicated_answers(my_connector, kwargs["session"], splitted_questions, kwargs["text_field"], kwargs["similarity_percentage"])
            duplicated_docs += matching_docs

        return duplicated_docs


