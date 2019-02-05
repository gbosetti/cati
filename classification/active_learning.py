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

from sklearn.datasets import load_files
from sklearn.feature_extraction.text import TfidfVectorizer

from elasticsearch import Elasticsearch
import elasticsearch.helpers


NUM_QUESTIONS = 3
ACTIVE = False
DATA_FOLDER = os.getcwd() # E.g. C:\Users\gbosetti\Desktop\MABED-master\classification "C:\\Users\\gbosetti\\PycharmProjects\\auto-learning\\data"
TRAIN_FOLDER = os.path.join(DATA_FOLDER, "train")
TEST_FOLDER = os.path.join(DATA_FOLDER, "test")
UNLABELED_FOLDER = os.path.join(DATA_FOLDER, "unlabeled")
ENCODING = 'latin1'  #latin1

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
    def benchmark(self, clf, X_train, X_test, y_train, y_test, X_unlabeled, categories):

        print("Training: ")
        print(clf)
        t0 = time()
        clf.fit(X_train, y_train)
        train_time = time() - t0
        print("train time: %0.3fs" % train_time)

        t0 = time()
        pred = clf.predict(X_test)
        test_time = time() - t0
        print("test time:  %0.3fs" % test_time)

        score = metrics.f1_score(y_test, pred)
        accscore = metrics.accuracy_score(y_test, pred)
        print("pred count is %d" % len(pred))
        print('accuracy score:     %0.3f' % accscore)
        print("f1-score:   %0.3f" % score)

        if hasattr(clf, 'coef_'):
            print("dimensionality: %d" % clf.coef_.shape[1])
            print("density: %f" % density(clf.coef_))

        print("classification report:")
        print(metrics.classification_report(y_test, pred,
                                            target_names=categories))

        print("confusion matrix:")
        print(metrics.confusion_matrix(y_test, pred))

        print("confidence for unlabeled data:")
        # compute absolute confidence for each unlabeled sample in each class
        confidences = np.abs(clf.decision_function(X_unlabeled))
        # average abs(confidence) over all classes for each unlabeled sample (if there is more than 2 classes)
        if (len(categories) > 2):
            confidences = np.average(confidences, axix=1)
            print("when categories are more than 2")

        # print("***X_unlabeled", X_unlabeled) # , len(X_unlabeled))
        # print("***confidences", confidences) # , len(confidences))

        sorted_confidences = np.argsort(confidences)
        question_samples = []
        # select top k low confidence unlabeled samples
        low_confidence_samples = sorted_confidences[0:NUM_QUESTIONS]
        # select top k high confidence unlabeled samples
        high_confidence_samples = sorted_confidences[-NUM_QUESTIONS:]

        # print("high_confidence_samples", high_confidence_samples)
        # print("low_confidence_samples", low_confidence_samples.tolist())

        question_samples.extend(low_confidence_samples.tolist())
        question_samples.extend(high_confidence_samples.tolist())

        clf_descr = str(clf).split('(')[0]
        return clf_descr, score, train_time, test_time, question_samples, sorted_confidences  # sorted_confidences added by Gabi

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
            size=10000,
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
            size=10000,
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
            size=5000,
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
        data_unlabeled = load_files(UNLABELED_FOLDER, encoding=ENCODING)
        categories = data_train.target_names

        def size_mb(docs):
            return sum(len(s.encode('utf-8')) for s in docs) / 1e6

        data_train_size_mb = size_mb(data_train.data)
        data_test_size_mb = size_mb(data_test.data)
        data_unlabeled_size_mb = size_mb(data_unlabeled.data)

        print("%d documents - %0.3fMB (training set)" % (
            len(data_train.data), data_train_size_mb))
        print("%d documents - %0.3fMB (test set)" % (
            len(data_test.data), data_test_size_mb))
        print("%d documents - %0.3fMB (unlabeled set)" % (
            len(data_unlabeled.data), data_unlabeled_size_mb))
        print("%d categories" % len(categories))

        return data_train, data_test, data_unlabeled, categories

    def learn(self):

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

        # Starting the process
        data_train, data_test, data_unlabeled, categories = self.loading_tweets_from_files()

        # split a training set and a test set
        y_train = data_train.target
        y_test = data_test.target

        # Extracting features from the training dataset using a sparse vectorizer
        print("Extracting features")
        vectorizer = TfidfVectorizer(encoding=ENCODING, use_idf=True, norm='l2', binary=False, sublinear_tf=True,
                                     min_df=0.001, max_df=1.0, ngram_range=(1, 2), analyzer='word', stop_words=None)

        # Getting a sparse csc matrix.
        X_train = vectorizer.fit_transform(data_train.data)

        # Extracting features from the test dataset using the same vectorizer
        X_test = vectorizer.transform(data_test.data)

        print("n_samples: %d, n_features: %d" % X_test.shape)

        # Extracting features from the unlabled dataset using the same vectorizer
        X_unlabeled = vectorizer.transform(data_unlabeled.data)
        print("n_samples: %d, n_features: %d" % X_unlabeled.shape)  # X_unlabeled.shape = (samples, features) = ej.(4999, 4004)

        # Benchmarking
        results = []
        results.append(self.benchmark(
            LinearSVC(loss='squared_hinge', penalty='l2', dual=False, tol=1e-3, class_weight='balanced'),
            X_train, X_test, y_train, y_test, X_unlabeled, categories
        ))  # auto > balanced   .  loss='12' > loss='squared_hinge'
        #results = [[x[i] for x in results] for i in range(6)]
        #clf_names, score, training_time, test_time, question_samples, sorted_confidences = results
        clf_names, score, training_time, test_time, question_samples, sorted_confidences = [[x[i] for x in results] for i in range(6)]

        # AT THIS POINT IT LEARNS OR IT USES THE DATA
        for i in question_samples[0]:
            filename = data_unlabeled.filenames[i]
            print(filename)
            print('**************************content***************************')
            print(data_unlabeled.data[i])
            print('**************************content end***********************')
            print("Annotate this text (select one label):")
            for i in range(0, len(categories)):
                print("%d = %s" % (i + 1, categories[i]))
            labelNumber = input("Enter the correct label number:")  # raw_input was renamed to input https://docs.python.org/3/whatsnew/3.0.html
            while labelNumber.isdigit() == False:
                labelNumber = input("Enter the correct label number (a number please):")  # raw_input was renamed to input https://docs.python.org/3/whatsnew/3.0.html
            labelNumber = int(labelNumber)
            category = categories[labelNumber - 1]
            dstDir = os.path.join(TRAIN_FOLDER, category)
            shutil.move(filename, dstDir)


classifier = ActiveLearning()
classifier.learn()
# classifier.get_tweets_with_high_confidence();