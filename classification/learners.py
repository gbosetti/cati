# TfidfBasedLinearModel
from sklearn import metrics
from sklearn.svm import LinearSVC
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
# from sklearn.ensemble import RandomForestClassifier
from classification.vectorizers import *


#Word2Vec
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from sklearn.linear_model import LogisticRegression
import multiprocessing
from tqdm import tqdm

class AbstractLearner():

    def __init__(self):
        self.init_model()

    def init_model(self):
        #self.model = LinearSVC(loss='squared_hinge', penalty='l2', dual=False, tol=1e-3)
        return

    def train_model(self, data_train, data_test, data_unlabeled, encoding, categories):
        # data_train, data_test, data_unlabeled are the results of reading with sklearn.datasets load_files
        # Encoding is a string. e.g. 'latin1'
        # categories
        return  # last_confidences, last_predictions, X_unlabeled, scores


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


class SklearnBasedModel(AbstractLearner):

    def predict(self, conf_matrix):
        return self.model.predict(conf_matrix)  # may be the X_test or X_unlabeled

    def get_prediction_scores(self, pred_on_X_test, y_test):

        score = metrics.f1_score(y_test, pred_on_X_test)
        accscore = metrics.accuracy_score(y_test, pred_on_X_test)
        recall_score = metrics.recall_score(y_test, pred_on_X_test)

        precision = metrics.precision_score(y_test, pred_on_X_test, pos_label=1, average='binary')
        precision_score = metrics.precision_score(y_test, pred_on_X_test)

        return {
            "f1": score,
            "accuracy": accscore,
            "recall": recall_score,
            "precision": precision_score
        }

    def _train(self, X_train, y_train):
        # TRAIN THE MODEL BEFORE PREDICTING
        self.model.fit(X_train, y_train)

    def train_model(self, data_train, data_test, data_unlabeled, encoding, categories, scores_generation=True):

        self.data_unlabeled = data_unlabeled

        X_train, y_train, X_test, y_test, X_unlabeled = self.vectorize(data_train, data_test, data_unlabeled, encoding)
        self._train(X_train, y_train)

        # Predicts annotations on the test set to get the scores
        scores=None
        if scores_generation:
            pred_on_X_test = self.predict(X_test)
            scores = self.get_prediction_scores(pred_on_X_test, y_test)

        # Predicts annotations on the unlabeled set and get the confidence
        last_predictions = self.predict(X_unlabeled)
        last_confidences = self.decision_function(X_unlabeled, last_predictions)

        return last_confidences, last_predictions, X_unlabeled, scores

    def vectorize(self, data_train, data_test, data_unlabeled, encoding):

        # return TfidfBasedVectorizer(encoding=encoding).vectorize(data_train, data_test, data_unlabeled)
        return CountBasedVectorizer().vectorize(data_train, data_test, data_unlabeled)


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


class TfidfBasedLinearModel(SklearnBasedModel):

    def init_model(self):
        self.model = LinearSVC(loss='squared_hinge', penalty='l2', dual=False, tol=1e-3)

    def decision_function(self, X_unlabeled, predicted_labels):

        # compute absolute confidence for each unlabeled sample in each class
        # decision_function gets "the confidence score for a sample is the signed distance of that sample to the hyperplane" https://scikit-learn.org/stable/modules/generated/sklearn.svm.LinearSVC.html
        # Predicts confidence scores for samples. X_Unlabeled is a csr_matrix. Scipy offers variety of sparse matrices functions that store only non-zero elements.
        decision = self.model.decision_function(X_unlabeled)
        return np.abs(decision)  # Calculates the absolute value element-wise



class SklearnProbaBasedModel(SklearnBasedModel):

    def decision_function(self, X_unlabeled, predicted_labels):

        pred_confidences = predicted_labels.astype(np.float64) # np.copy(predicted_labels)
        all_classes_confidences = self.model.predict_proba(X_unlabeled)  # clsas_1_pred = pred_1[:,1]

        for i, tuple in enumerate(all_classes_confidences):
            selected_class_index = int(pred_confidences[i])
            pred_confidences[i] = tuple[selected_class_index]

        return pred_confidences

# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


class DecisionTreeBasedModel(SklearnProbaBasedModel):  # DecisionTreeClassifierModel
    # Unsupervised Outlier Detection.
    def init_model(self):
        self.model = DecisionTreeClassifier(random_state=0) # OneClassSVM(gamma='auto')


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


class KNeighborsBasedModel(SklearnProbaBasedModel):  # DecisionTreeClassifierModel
    # Unsupervised Outlier Detection.
    def init_model(self):
        self.model = KNeighborsClassifier(n_neighbors=2)


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
















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




