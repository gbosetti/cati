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

import os
import string
from time import time
import numpy as np
import pylab as pl
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.linear_model import RidgeClassifier
from sklearn.svm import LinearSVC
from sklearn.linear_model import SGDClassifier
from sklearn.linear_model import Perceptron
from sklearn.linear_model import PassiveAggressiveClassifier
from sklearn.naive_bayes import BernoulliNB, MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neighbors import NearestCentroid
from sklearn.ensemble import RandomForestClassifier
from sklearn.utils.extmath import density
from sklearn import metrics
from sklearn.model_selection import cross_validate  #by Gabi
import itertools
import shutil
from sklearn.feature_extraction import text
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
nltk.download('stopwords')

from sklearn.datasets import load_files
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import Counter
from elasticsearch import Elasticsearch
import elasticsearch.helpers
from elasticsearch_dsl import Search
from elasticsearch_dsl.connections import connections

class ActiveLearning:

    def __init__(self, train_folder="train", test_folder="test", unlabeled_folder="unlabeled"):

        DATA_FOLDER = os.path.join(os.getcwd(), "tmp_data")

        self.TRAIN_FOLDER = os.path.join(DATA_FOLDER, train_folder)
        self.TEST_FOLDER = os.path.join(DATA_FOLDER, test_folder)
        self.UNLABELED_FOLDER = os.path.join(DATA_FOLDER, unlabeled_folder)

        self.POS_CLASS_FOLDER = "confirmed"
        self.NEG_CLASS_FOLDER = "negative"
        self.NO_CLASS_FOLDER = "proposed"

        self.ENCODING = 'latin1'  # latin1

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

        if not os.path.exists(folder):
            os.makedirs(folder)

        for the_file in os.listdir(folder):
            file_path = os.path.join(folder, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                # elif os.path.isdir(file_path): shutil.rmtree(file_path)
            except Exception as e:
                print(e)


    def writeFile(self, fullpath, content):
        file = open(fullpath, "w", encoding='utf-8')
        file.write(content)
        file.close()

    ###############################################################################
    # Benchmark classifiers
    def benchmark(self, clf, X_train, X_test, y_train, y_test, X_unlabeled, categories, num_questions, sampling_method):

        self.num_questions = num_questions
        t0 = time()
        clf.fit(X_train, y_train) # fits the model according to the training set (passing its data and the vectorized feature)

        pred = clf.predict(X_test)
        score = metrics.f1_score(y_test, pred)
        accscore = metrics.accuracy_score(y_test, pred)

        scores = {
            "f1": score,
            "accuracy": accscore
        }

        if (sampling_method == "closer_to_hyperplane"):
            question_samples, confidences, predictions = self.get_samples_closer_to_hyperplane(clf, num_questions, X_unlabeled, categories)

        return question_samples, confidences, predictions, scores




    def get_samples_closer_to_hyperplane(self, clf, num_questions, X_unlabeled, categories):

        # compute absolute confidence for each unlabeled sample in each class
        decision = clf.decision_function(
            X_unlabeled)  # Predicts confidence scores for samples. X_Unlabeled is a csr_matrix. Scipy offers variety of sparse matrices functions that store only non-zero elements.
        confidences = np.abs(decision)  # Calculates the absolute value element-wise
        predictions = clf.predict(X_unlabeled)
        # average abs(confidence) over all classes for each unlabeled sample (if there is more than 2 classes)
        if (len(categories) > 2):
            confidences = np.average(confidences, axix=1)
            print("when categories are more than 2")

        sorted_samples = np.argsort(confidences)  # argsort returns the indices that would sort the array

        question_samples = []
        # num_questions = int(num_questions / 2)
        # # select top k low confidence unlabeled samples
        # low_confidence_samples = sorted_confidences[0:num_questions]
        # # select top k high confidence unlabeled samples
        # high_confidence_samples = sorted_confidences[-num_questions:]
        # question_samples.extend(low_confidence_samples.tolist())
        # question_samples.extend(high_confidence_samples.tolist())
        question_samples = sorted_samples[0:num_questions].tolist()

        return question_samples, confidences, predictions

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

        # if not os.path.exists(DATA_FOLDER):
        #     os.makedirs(DATA_FOLDER)

        self.delete_folder_contents(os.path.join(self.TRAIN_FOLDER, self.POS_CLASS_FOLDER))
        self.delete_folder_contents(os.path.join(self.TRAIN_FOLDER, self.NEG_CLASS_FOLDER))
        self.delete_folder_contents(os.path.join(self.TEST_FOLDER, self.POS_CLASS_FOLDER))
        self.delete_folder_contents(os.path.join(self.TEST_FOLDER, self.NEG_CLASS_FOLDER))
        self.delete_folder_contents(os.path.join(self.UNLABELED_FOLDER, self.NO_CLASS_FOLDER))

    def read_test_data_from_dataset(self, **kwargs):

        target_source = ["id_str", kwargs["field"], "imagesCluster", kwargs["session"]]
        matching_queries = []

        for tweet in kwargs["matching_data"]:
            matching_queries.append({"match": {"id_str": {"query": tweet["_source"]["id_str"] }}})

        # Getting a sample from elasticsearch to classify
        confirmed_data = self.read_raw_tweets_from_elastic(
            index= kwargs["index"],
            doc_type="tweet",
            host="localhost",
            port="9200",
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
            _source=target_source,
            request_timeout=30
        )
        negative_data = self.read_raw_tweets_from_elastic(
            index=kwargs["index"],
            doc_type="tweet",
            host="localhost",
            port="9200",
            query={
                "query": {
                    "bool": {
                        "should": matching_queries,
                        "minimum_should_match": 1,
                        "must":[{
                            "match":{ kwargs["session"] :"negative" }
                        }]
                    }
                }
            },
            _source=target_source,
            request_timeout=30
        )
        proposed_data = self.read_raw_tweets_from_elastic(
            index=kwargs["index"],
            doc_type="tweet",
            host="localhost",
            port="9200",
            query={
                "query": {
                    "bool": {
                        "should": matching_queries,
                        "minimum_should_match": 1,
                        "must":[{
                            "match":{ kwargs["session"] :"proposed" }
                        }]
                    }
                }
            },
            _source=target_source,
            request_timeout=30
        )

        return confirmed_data, negative_data, proposed_data

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

    def stringuify(self, field, is_field_array):

        if is_field_array:
            return " ".join(field)
        else: return field

    def write_data_in_folders(self, field, is_field_array, path, dataset):

        for tweet in dataset:
            self.writeFile(os.path.join(path, tweet['_source']['id_str'] + ".txt"), self.stringuify(tweet['_source'][field], is_field_array))

    def size_mb(self, docs):
        return sum(len(s.encode('utf-8')) for s in docs) / 1e6

    def loading_tweets_from_files(self):

        # Loading the datasets
        data_train = load_files(self.TRAIN_FOLDER, encoding=self.ENCODING)  # data_train
        data_test = load_files(self.TEST_FOLDER, encoding=self.ENCODING)
        unlabeled = load_files(self.UNLABELED_FOLDER, encoding=self.ENCODING)
        categories = data_train.target_names

        data_train_size_mb = self.size_mb(data_train.data)
        data_test_size_mb = self.size_mb(data_test.data)
        unlabeled_size_mb = self.size_mb(unlabeled.data)

        print("%d documents - %0.3fMB (training set)" % (
            len(data_train.data), data_train_size_mb))
        print("%d documents - %0.3fMB (test set)" % (
            len(data_test.data), data_test_size_mb))
        print("%d documents - %0.3fMB (unlabeled set)" % (
            len(unlabeled.data), unlabeled_size_mb))
        #print("%d categories" % len(categories), categories)

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

    def download_testing_data(self, ** kwargs):

        print("Getting TEsting data from the elastic index: ", kwargs["index"])
        confirmed_data, negative_data, proposed_data = self.read_test_data_from_dataset(**kwargs)

        if (len(confirmed_data) == 0 or len(negative_data) == 0) or len(proposed_data) > 0:
            raise Exception('Check your test set. You need a groundtruth dataset fully classified ')
            return

        # Writing the retrieved files into the folders
        self.write_data_in_folders(kwargs["field"], kwargs["is_field_array"], os.path.join(self.TEST_FOLDER, self.NEG_CLASS_FOLDER), negative_data)
        self.write_data_in_folders(kwargs["field"], kwargs["is_field_array"], os.path.join(self.TEST_FOLDER, self.POS_CLASS_FOLDER), confirmed_data)

    def download_training_data(self, **kwargs):

        print("Getting TRaining data from the elastic index: ", kwargs["index"])
        confirmed_data, negative_data = self.read_data_from_dataset(**kwargs)

        if len(confirmed_data) == 0 or len(negative_data) == 0:
            raise Exception('You need to have some already classified data in your dataset')
            return

        # Writing the retrieved files into the folders
        self.write_data_in_folders(kwargs["field"], kwargs["is_field_array"], os.path.join(self.TRAIN_FOLDER, self.NEG_CLASS_FOLDER), negative_data)
        self.write_data_in_folders(kwargs["field"], kwargs["is_field_array"], os.path.join(self.TRAIN_FOLDER, self.POS_CLASS_FOLDER), confirmed_data)

    def download_unclassified_data(self, **kwargs):

        print("Getting UNclassified data from the elastic index: ", kwargs["index"])

        target_source = ["id_str", kwargs["field"], "imagesCluster", kwargs["session"]]
        proposed_data = self.read_raw_tweets_from_elastic(
            index=kwargs["index"],
            doc_type="tweet",
            host="localhost",
            port="9200",
            query={"query": {
                "match": {
                    kwargs["session"]: "proposed"
                }
            }},
            _source=target_source,
            request_timeout=30
        )

        if len(proposed_data) == 0:
            raise Exception('You need to have some data to classify in your dataset')
            return

        # Writing the retrieved files into the folders
        self.write_data_in_folders(kwargs["field"], kwargs["is_field_array"], os.path.join(self.UNLABELED_FOLDER, self.NO_CLASS_FOLDER), proposed_data)

        return proposed_data

    def build_model(self, **kwargs):

        # Keep track of the last used params
        self.num_questions = kwargs["num_questions"]
        self.remove_stopwords = kwargs["remove_stopwords"]

        # Starting the process
        data_train, data_test, self.data_unlabeled, self.categories = self.loading_tweets_from_files()

        # Get the sparse matrix of each dataset
        y_train = data_train.target
        y_test = data_test.target

        vectorizer = TfidfVectorizer(encoding=self.ENCODING, use_idf=True, norm='l2', binary=False, sublinear_tf=True,
                                     min_df=0.001, max_df=1.0, ngram_range=(1, 2), analyzer='word')

        # Vectorizing the TRaining subset Lears the vocabulary Gets a sparse csc matrix with fit_transform(data_train.data).
        X_train = vectorizer.fit_transform(data_train.data)

        # Vectorizing the TEsting subset by using the vocabulary and document frequencies already learned by fit_transform with the TRainig subset.
        X_test = vectorizer.transform(data_test.data)

        print("n_samples: %d, n_features: %d" % X_test.shape)

        # Extracting features from the unlabled dataset using the same vectorizer
        X_unlabeled = vectorizer.transform(self.data_unlabeled.data)
        print("n_samples: %d, n_features: %d" % X_unlabeled.shape)  # X_unlabeled.shape = (samples, features) = ej.(4999, 4004)

        # Benchmarking
        #print("Training")
        # results = []
        # results.append(self.benchmark(
        #     LinearSVC(loss='squared_hinge', penalty='l2', dual=False, tol=1e-3), # class_weight='balanced'
        #     X_train, X_test, y_train, y_test, X_unlabeled, self.categories, kwargs["num_questions"], kwargs["sampling_method"]
        # ))  # auto > balanced   .  loss='12' > loss='squared_hinge'

        questions, confidences, predictions, scores = self.benchmark(
            LinearSVC(loss='squared_hinge', penalty='l2', dual=False, tol=1e-3),  # class_weight='balanced'
            X_train, X_test, y_train, y_test, X_unlabeled, self.categories, kwargs["num_questions"],
            kwargs["sampling_method"]
        )  # auto > balanced   .  loss='12' > loss='squared_hinge'

        #questions, confidences, predictions, scores = [[x[i] for x in results] for i in range(4)]
        formatted_questions = self.format_questions(questions, predictions, confidences)

        return formatted_questions, confidences, predictions, scores


    def format_questions(self, question_samples, predictions, confidences):
        # AT THIS POINT IT LEARNS OR IT USES THE DATA
        complete_question_samples = []
        for index in question_samples:
            complete_question_samples.append({
                "filename": self.data_unlabeled.filenames[index],
                "text": self.data_unlabeled.data[index],
                "pred_label":  int(predictions[index]),
                "data_unlabeled_index": index,
                "confidence": confidences[index],
            })
        self.confidences = confidences

        return complete_question_samples


    def move_answers_to_training_set(self, labeled_questions):

        # print("Moving the user labeled questions into the proper folders")
        for question in labeled_questions:
            dstDir = os.path.join(self.TRAIN_FOLDER, question["label"])
            # print("Moving", question["filename"], " to ", dstDir)
            shutil.move(question["filename"], dstDir)

    def classify_accurate_quartiles(self, **kwargs):  # min_acceptable_accuracy min_high_confidence


        return

    def suggest_classification(self, predictions, confidences, **kwargs):

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
        print(full_text)

        if remove_stopwords:
            punctuation = list(string.punctuation + "…" + "..." + "’" + "️" + "'" + '🔴' + '•')
            multilang_stopwords = self.get_stopwords_for_langs(self.langs) + ["Ã", "RT"] + punctuation
            tokenized_text = word_tokenize(full_text)  # tknzr = TweetTokenizer()             tokenized_text = tknzr.tokenize(full_text)
            print("Detected tokens:", len(tokenized_text), tokenized_text)
            filtered_words = list(filter(lambda word: word not in multilang_stopwords, tokenized_text))
            print("Tokens after removing stop-words:", len(filtered_words), filtered_words)
            full_text = " ".join(filtered_words)
            print("FULL TEXT", full_text)

        ngram_counts = Counter(self.n_grams(full_text.split(), length))
        return ngram_counts.most_common(top_ngrams_to_retrieve)


# classifier = ActiveLearning()
# classifier.get_langs_from_unlabeled_tweets(
#     index="twitterfdl2017",
#     doc_type="tweet",
#     host="localhost",
#     port="9200"
# )
# classifier.start_learning()
# classifier.clean_directories();
# classifier.get_tweets_with_high_confidence();
