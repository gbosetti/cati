'''
Created on Jul 4, 2014
based on http://scikit-learn.org/stable/auto_examples/document_classification_20newsgroups.html

This program implements active learning (http://en.wikipedia.org/wiki/Active_learning_(machine_learning))
for text classification tasks with scikit-learn's LinearSVC classifier. Despite differences this can also be called
incremental training.
Instead of using Stochastic Gradient Descent we used the batch mode because the data is not that big
and accuracy here was more of concern than efficiency.

The algorithm trains the model based on a train dataset and evaluates using a test dataset.
After each evaluation algorithm selects 2*NUM_QUESTIONS samples from unlabeled dataset in order
to be labeled by a user/expert. The labeled sample is then moved to the corresponding directory in
the train dataset and the model will start training again with the new improved training set.

The selection of unlabeled samples is based on decision_function of SVM which is
the distance of the samples X to the separating hyperplane. This distance is between
[-1, 1] but because we need confidence levels we use absolute values. In case the classes
are more than two, the decision function will return a confidence level for each class and for each sample
so in case we have more than 2 classes we average over the absolute values of confidence over all the classes.

We use top NUM_QUESTIONS samples with highest average absolute confidence and also top NUM_QUESTIONS
samples with lowest average absolute confidence for expert labeling. This procedure can be easily changed
by modifying the code in benchmark function.

This program requires a directory structure similar to what is shown below:
    mainDirectory
       train
           pos
               1.txt
               2.txt
           neg
               3.txt
               4.txt
       test
           pos
               5.txt
               6.txt
           neg
               7.txt
               8.txt
       unlabeled
           unlabeled
               9.txt
               10.txt
               11.txt
The filenames in unlabeled should not be a duplicate of filenames in train directory because every time we label a file
we will move that file into the corresponding class directory in train directory.

The pos and neg categories are arbitrary and both the number of the classes and their name can be different with what is shown here.
The classifier can also be changed to any other classifier in scikit-learn.


@author: afshin rahimi
https://github.com/afshinrahimi/activelearning

'''
import matplotlib
# matplotlib.use('Agg')
import json
import shutil

import os
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
from nltk.corpus import stopwords
nltk.download('stopwords')

from sklearn.datasets import load_files
from sklearn.feature_extraction.text import TfidfVectorizer

from elasticsearch import Elasticsearch
import elasticsearch.helpers
from elasticsearch_dsl import Search
from elasticsearch_dsl.connections import connections

ACTIVE = False
DATA_FOLDER = os.path.join(os.getcwd(), "classification")  # E.g. C:\Users\gbosetti\Desktop\MABED-master\classification "C:\\Users\\gbosetti\\PycharmProjects\\auto-learning\\data"
TRAIN_FOLDER = os.path.join(DATA_FOLDER, "train")
TEST_FOLDER = os.path.join(DATA_FOLDER, "test")
UNLABELED_FOLDER = os.path.join(DATA_FOLDER, "unlabeled")
ENCODING = 'latin1'  #latin1

print("DATA_FOLDER", DATA_FOLDER)

class ActiveLearning:

    def read_raw_tweets_from_elastic(self, **kwargs):
        elastic = Elasticsearch([{'host': kwargs["host"], 'port': kwargs["port"]}])

        raw_tweets = elastic.search(
            index=kwargs["index"],
            doc_type="tweet",
            size=kwargs["size"],
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
    def benchmark(self, clf, X_train, X_test, y_train, y_test, X_unlabeled, categories, num_questions):

        print("Training. Classifier: ", clf)
        num_questions = int(num_questions)
        t0 = time()
        clf.fit(X_train, y_train) # matches the matrix with the array of matching cases. Case 1-> label a ... ( [[1],[2],[3]], ["a","b","a"] )

        # t0 = time()
        pred = clf.predict(X_test)
        score = metrics.f1_score(y_test, pred)
        accscore = metrics.accuracy_score(y_test, pred)
        print("------------------------------------------")
        print("pred count is %d" % len(pred))
        print('accuracy score:     %0.3f' % accscore)
        print("f1-score:   %0.3f" % score)
        print("------------------------------------------")

        # if hasattr(clf, 'coef_'):
        #     print("dimensionality: %d" % clf.coef_.shape[1])
        #     print("density: %f" % density(clf.coef_))
        #
        # print("classification report:")
        # print(metrics.classification_report(y_test, pred, target_names=categories))
        #
        # print("confusion matrix:")
        # print(metrics.confusion_matrix(y_test, pred))

        print("confidence for unlabeled data:")
        # compute absolute confidence for each unlabeled sample in each class
        decision = clf.decision_function(X_unlabeled)  # Predicts confidence scores for samples. X_Unlabeled is a csr_matrix. Scipy offers variety of sparse matrices functions that store only non-zero elements.
        confidences = np.abs(decision)  # Calculates the absolute value element-wise
        predictions = clf.predict(X_unlabeled)
        # average abs(confidence) over all classes for each unlabeled sample (if there is more than 2 classes)
        if (len(categories) > 2):
            confidences = np.average(confidences, axix=1)
            print("when categories are more than 2")

        sorted_confidences = np.argsort(confidences)  # argsort returns the indices that would sort the array

        question_samples = []
        num_questions = int(num_questions / 2)
        # select top k low confidence unlabeled samples
        low_confidence_samples = sorted_confidences[0:num_questions]
        # select top k high confidence unlabeled samples
        high_confidence_samples = sorted_confidences[-num_questions:]
        question_samples.extend(low_confidence_samples.tolist())
        question_samples.extend(high_confidence_samples.tolist())

        clf_descr = str(clf).split('(')[0]

        return clf_descr, question_samples, confidences, predictions  # sorted_confidences added by Gabi

    def get_tweets_with_high_confidence(self):

        top_confidence_tweets = self.sorted_confidences[0][:20]
        for i in top_confidence_tweets:
            print("i:", i)
            print("filename", self.data_unlabeled.data[i])
            print("filename", self.data_unlabeled.filenames[i])

    def clean_directories(self):
        print("Cleaning directories")
        self.delete_folder_contents(os.path.join(TRAIN_FOLDER, "pos"))
        self.delete_folder_contents(os.path.join(TRAIN_FOLDER, "neg"))
        self.delete_folder_contents(os.path.join(TEST_FOLDER, "pos"))
        self.delete_folder_contents(os.path.join(TEST_FOLDER, "neg"))
        self.delete_folder_contents(os.path.join(UNLABELED_FOLDER, "unlabeled"))

    def read_data_from_dataset(self):

        target_source = ["id_str", "text", "imagesCluster", "session_twitterfdl2017"]

        # Getting a sample from elasticsearch to classify
        confirmed_data = self.read_raw_tweets_from_elastic(
            index="twitterfdl2017",
            doc_type="tweet",
            host="localhost",
            port="9200",
            size=5000,
            query={"query": {
                "match": {
                    "session_twitterfdl2017": "confirmed"
                }
            }},
            _source=target_source,
            request_timeout=30
        )
        negative_data = self.read_raw_tweets_from_elastic(
            index="twitterfdl2017",
            doc_type="tweet",
            host="localhost",
            port="9200",
            size=5000,
            query={"query": {
                "match": {
                    "session_twitterfdl2017": "negative"
                }
            }},
            _source=target_source,
            request_timeout=30
        )
        proposed_data = self.read_raw_tweets_from_elastic(
            index="twitterfdl2017",
            doc_type="tweet",
            host="localhost",
            port="9200",
            size=2500,
            query={"query": {
                "match": {
                    "session_twitterfdl2017": "proposed"
                }
            }},
            _source=target_source,
            request_timeout=30
        )

        return confirmed_data, negative_data, proposed_data

    def write_data_in_folders(self, negative_data_test, confirmed_data_test, negative_data_train, confirmed_data_train, proposed_data):

        for tweet in negative_data_test:
            self.writeFile(os.path.join(TEST_FOLDER, "neg", tweet['_source']['id_str'] + ".txt"), tweet['_source']['text'])

        for tweet in confirmed_data_test:
            self.writeFile(os.path.join(TEST_FOLDER, "pos", tweet['_source']['id_str'] + ".txt"), tweet['_source']['text'])

        for tweet in negative_data_train:
            self.writeFile(os.path.join(TRAIN_FOLDER, "neg", tweet['_source']['id_str'] + ".txt"), tweet['_source']['text'])

        for tweet in confirmed_data_train:
            self.writeFile(os.path.join(TRAIN_FOLDER, "pos", tweet['_source']['id_str'] + ".txt"), tweet['_source']['text'])

        for tweet in proposed_data:
            self.writeFile(os.path.join(UNLABELED_FOLDER, "unlabeled", tweet['_source']['id_str'] + ".txt"),
                      tweet['_source']['text'])

    def loading_tweets_from_files(self):

        # Loading the datasets
        data_train = load_files(TRAIN_FOLDER, encoding=ENCODING)
        data_test = load_files(TEST_FOLDER, encoding=ENCODING)
        unlabeled = load_files(UNLABELED_FOLDER, encoding=ENCODING)
        categories = data_train.target_names

        def size_mb(docs):
            return sum(len(s.encode('utf-8')) for s in docs) / 1e6

        data_train_size_mb = size_mb(data_train.data)
        data_test_size_mb = size_mb(data_test.data)
        unlabeled_size_mb = size_mb(unlabeled.data)

        print("%d documents - %0.3fMB (training set)" % (
            len(data_train.data), data_train_size_mb))
        print("%d documents - %0.3fMB (test set)" % (
            len(data_test.data), data_test_size_mb))
        print("%d documents - %0.3fMB (unlabeled set)" % (
            len(unlabeled.data), unlabeled_size_mb))
        print("%d categories" % len(categories))

        return data_train, data_test, unlabeled, categories

    def get_langs_from_unlabeled_data(self):

        try:
            langs = self.get_langs_from_unlabeled_tweets(
                index="twitterfdl2017",
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

    def start_learning(self, num_questions, remove_stopwords):

        print("Starting...")
        self.clean_directories()
        # Getting a sample from elasticsearch to classify
        print("Getting data from elastic")
        confirmed_data, negative_data, proposed_data = self.read_data_from_dataset()

        # Slice the classified data to fill the test and train datasts
        index = int(len(negative_data) / 2)
        negative_data_test = negative_data[index:]
        negative_data_train = negative_data[:index]
        index = int(len(confirmed_data) / 2)
        confirmed_data_test = confirmed_data[index:]
        confirmed_data_train = confirmed_data[:index]

        # Writing the retrieved files into the folders
        print("Writting data from elastic into folders")
        self.write_data_in_folders(negative_data_test, confirmed_data_test, negative_data_train, confirmed_data_train, proposed_data)

        print("Updating model")
        clf_names, question_samples, confidences, predictions = self.updating_model(num_questions, remove_stopwords)

        print("Generating questions")
        return self.generating_questions(question_samples, predictions, confidences)


    def updating_model(self, num_questions, remove_stopwords):

        # Keep track of the last used params
        self.num_questions = num_questions
        self.remove_stopwords = remove_stopwords

        # Starting the process
        data_train, data_test, self.data_unlabeled, self.categories = self.loading_tweets_from_files()

        # split a training set and a test set
        y_train = data_train.target
        y_test = data_test.target  # 'target': array([1, 1, 1, ..., 1, 1, 1]) according to the labels (pos, neg)

        # Extracting features from the training dataset using a sparse vectorizer
        print("Extracting features")
        langs = self.get_langs_from_unlabeled_data()

        # Getting the list of available stopwords, if the user asked for it
        if remove_stopwords.lower() in ("yes", "true", "t", "1"):
            print("Generating stopwords")
            multilang_stopwords = self.get_stopwords_for_langs(langs)
        else:
            print("Ignoring stopwords")
            multilang_stopwords = None

        # TOPRINT vectorizer.get_feature_names(), vectorizer.idf_

        vectorizer = TfidfVectorizer(encoding=ENCODING, use_idf=True, norm='l2', binary=False, sublinear_tf=True,
                                     min_df=0.001, max_df=1.0, ngram_range=(1, 2), analyzer='word', stop_words=multilang_stopwords)

        # Getting a sparse csc matrix.
        X_train = vectorizer.fit_transform(data_train.data)

        # Extracting features from the test dataset using the same vectorizer
        X_test = vectorizer.transform(data_test.data)

        print("n_samples: %d, n_features: %d" % X_test.shape)

        # Extracting features from the unlabled dataset using the same vectorizer
        X_unlabeled = vectorizer.transform(self.data_unlabeled.data)
        print("n_samples: %d, n_features: %d" % X_unlabeled.shape)  # X_unlabeled.shape = (samples, features) = ej.(4999, 4004)

        # Benchmarking
        print("Benchmarking")
        results = []
        results.append(self.benchmark(
            LinearSVC(loss='squared_hinge', penalty='l2', dual=False, tol=1e-3, class_weight='balanced'),
            X_train, X_test, y_train, y_test, X_unlabeled, self.categories, num_questions
        ))  # auto > balanced   .  loss='12' > loss='squared_hinge'
        return [[x[i] for x in results] for i in range(4)]


    def generating_questions(self, question_samples, predictions, confidences):
        # AT THIS POINT IT LEARNS OR IT USES THE DATA
        complete_question_samples = []
        for index in question_samples[0]:
            complete_question_samples.append({
                "filename": self.data_unlabeled.filenames[index],
                "text": self.data_unlabeled.data[index],
                "pred_label":  int(predictions[0][index]),
                "data_unlabeled_index": index,
                "confidence": confidences[0][index],
            })
        self.confidences = confidences

        return complete_question_samples


    def suggest_classification(self, labeled_questions):

        print("Moving the user labeled questions into the proper folders")
        for question in labeled_questions:
            # index = int(question["id"])
            # self.data_unlabeled.filenames[index]
            dstDir = os.path.join(TRAIN_FOLDER, question["label"])
            print("Moving", question["filename"], " to ", dstDir)
            shutil.move(question["filename"], dstDir)

        # classified_sample = self.confidences

        # Updating the model
        clf_names, question_samples, confidences, predictions = self.updating_model(self.num_questions, self.remove_stopwords)

        positiveTweets = []
        negativeTweets = []

        # TODO: check that 1 = positive and 0 = negative in the model updating function
        for idx, val in enumerate(predictions[0]):
            if predictions[0][idx] == 1:
                positiveTweets.append({
                    "confidence": str(confidences[0][idx]),
                    "prediction": "positive"
                })
            elif predictions[0][idx] == 0:
                negativeTweets.append({
                    "confidence": str(confidences[0][idx]),
                    "prediction": "negative"
                })

        return {"positiveTweets": positiveTweets, "negativeTweets": negativeTweets}

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
