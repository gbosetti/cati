# TfidfBasedLinearModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn import preprocessing
from sklearn import metrics
from sklearn.svm import LinearSVC
import numpy as np

#Word2Vec
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from sklearn.linear_model import LogisticRegression
import multiprocessing
from tqdm import tqdm

class AbstractLearner():

    def __init__(self):
        self.model = LinearSVC(loss='squared_hinge', penalty='l2', dual=False, tol=1e-3)

    def train_model(self, data_train, data_test, data_unlabeled, encoding, categories):
        # data_train, data_test, data_unlabeled are the results of reading with sklearn.datasets load_files
        # Encoding is a string. e.g. 'latin1'
        # categories
        return  # last_confidences, last_predictions, X_unlabeled, scores

class TfidfBasedLinearModel(AbstractLearner):

    def vectorize(self, data_train, data_test, data_unlabeled, encoding):

        # Get the sparse matrix of each dataset
        self.data_unlabeled = data_unlabeled
        y_train = data_train.target
        y_test = data_test.target

        vectorizer = TfidfVectorizer(encoding=encoding, use_idf=True, norm='l2', binary=False, sublinear_tf=True,
                                     min_df=0.001, max_df=1.0, ngram_range=(1, 2), analyzer='word')

        # Vectorizing the TRaining subset Lears the vocabulary Gets a sparse csc matrix with fit_transform(data_train.data).
        # 'scale' normalizes before fitting. It is required since the LinearSVC is very sensitive to extreme values
        X_train = vectorizer.fit_transform(data_train.data)

        if (len(data_test.data) == 0):
            raise Exception('The test set is empty.')
            return

        if (len(data_unlabeled) == 0):
            raise Exception('The target (unlabeled) set is empty.')
            return

        if (len(data_train.data) == 0):
            raise Exception('The train set is empty.')
            return

        # Vectorizing the TEsting subset by using the vocabulary and document frequencies already learned by fit_transform with the TRainig subset.
        #print("Vectorizing the test set")
        X_test = vectorizer.transform(data_test.data)
        print("X_test n_samples: %d, n_features: %d" % X_test.shape)
        # Extracting features from the unlabled dataset using the same vectorizer

        X_unlabeled = vectorizer.transform(data_unlabeled.data)
        print("X_unlabeled n_samples: %d, n_features: %d" % X_unlabeled.shape)
        # fits the model according to the training set (passing its data and the vectorized feature)
        # 'scale' normalizes before fitting. It is required since the LinearSVC is very sensitive to extreme values
        # normalized_X_train = scale(X_train, with_mean=False)
        scaler = preprocessing.StandardScaler(with_mean=False)
        scaler = scaler.fit(X_train)

        X_train = scaler.transform(X_train)
        self.model.fit(X_train, y_train)

        X_test = scaler.transform(X_test)
        X_unlabeled = scaler.transform(X_unlabeled)

        return X_test, y_test, X_unlabeled

    def predict(self, conf_matrix):
        return self.model.predict(conf_matrix)  # may be the X_test or X_unlabeled

    def get_prediction_scores(self, pred_on_X_test, y_test):

        score = metrics.f1_score(y_test, pred_on_X_test)
        accscore = metrics.accuracy_score(y_test, pred_on_X_test)
        recall_score = metrics.recall_score(y_test, pred_on_X_test)
        precision_score = metrics.precision_score(y_test, pred_on_X_test)

        return {
            "f1": score,
            "accuracy": accscore,
            "recall": recall_score,
            "precision": precision_score
        }

    def train_model(self, data_train, data_test, data_unlabeled, encoding, categories, scores_generation=True):

        X_test, y_test, X_unlabeled = self.vectorize(data_train, data_test, data_unlabeled, encoding)

        # Predicts annotations on the test set to get the scores
        scores=None
        if scores_generation:
            pred_on_X_test = self.predict(X_test)
            scores = self.get_prediction_scores(pred_on_X_test, y_test)

        # Predicts annotations on the unlabeled set and get the confidence
        decision = self.decision_function(X_unlabeled)

        last_confidences = np.abs(decision) # Calculates the absolute value element-wise
        last_predictions = self.predict(X_unlabeled)

        return last_confidences, last_predictions, X_unlabeled, scores

    def decision_function(self, X_unlabeled):

        # compute absolute confidence for each unlabeled sample in each class
        # decision_function gets "the confidence score for a sample is the signed distance of that sample to the hyperplane" https://scikit-learn.org/stable/modules/generated/sklearn.svm.LinearSVC.html
        # Predicts confidence scores for samples. X_Unlabeled is a csr_matrix. Scipy offers variety of sparse matrices functions that store only non-zero elements.
        return self.model.decision_function(X_unlabeled)

class Word2VecBasedLinearModel(AbstractLearner):

    def train_model(self, data_train, data_test, data_unlabeled, encoding, categories, scores_generation=True):

        cores = multiprocessing.cpu_count()

        model_dbow = Doc2Vec(dm=0, vector_size=300, negative=5, hs=0, min_count=2, sample=0, workers=cores)
        model_dbow.build_vocab([x for x in tqdm(train_tagged.values)])


        y_train, X_train = self.vec_for_learning(model_dbow, train_tagged)
        y_test, X_test = self.vec_for_learning(model_dbow, test_tagged)

        logreg = LogisticRegression(n_jobs=1, C=1e5)
        logreg.fit(X_train, y_train)
        y_pred = logreg.predict(X_test)

        scores = self.get_prediction_scores(y_pred, y_test)

    def vec_for_learning(model, tagged_docs):
        sents = tagged_docs.values
        targets, regressors = zip(*[(doc.tags[0], model.infer_vector(doc.words, steps=20)) for doc in sents])
        return targets, regressors




