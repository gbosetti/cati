from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn import preprocessing
from gensim import utils
from gensim.models.doc2vec import LabeledSentence
from gensim.models import Doc2Vec
import numpy
from random import shuffle
import os

class AbstractVectorizer():

    def __init__(self):
        print("Using the ", self.__class__.__name__, " vectorizer")

    def _check_input_data(self, data_train, data_test, data_unlabeled):

        if (len(data_test.data) == 0):
            raise Exception('The test set is empty.')

        if (len(data_unlabeled) == 0):
            raise Exception('The target (unlabeled) set is empty.')

        if (len(data_train.data) == 0):
            raise Exception('The train set is empty.')

    def _normalize_subsets_data(self, X_train, X_test, X_unlabeled):

        # fits the model according to the training set (passing its data and the vectorized feature)
        # 'scale' normalizes before fitting. It is required since the LinearSVC is very sensitive to extreme values
        # normalized_X_train = scale(X_train, with_mean=False)
        scaler = preprocessing.StandardScaler(with_mean=False).fit(X_train)
        X_train = scaler.transform(X_train)
        X_test = scaler.transform(X_test)
        X_unlabeled = scaler.transform(X_unlabeled)

        return X_train, X_test, X_unlabeled


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


class SklearnBasedVectorizer(AbstractVectorizer):

    def __init__(self, encoding):
        AbstractVectorizer.__init__(self)  # super(MyFighters, self).__init__()

    def vectorize(self, data_train, data_test, data_unlabeled):
        self._check_input_data(data_train, data_test, data_unlabeled)  # Check!

        X_train, y_train, X_test, y_test, X_unlabeled = self._get_sparse_matrixes(data_train, data_test,
                                                                                  data_unlabeled)
        X_train, X_test, X_unlabeled = self._normalize_subsets_data(X_train, X_test, X_unlabeled)

        return X_train, y_train, X_test, y_test, X_unlabeled

    def _get_sparse_matrixes(self, data_train, data_test, data_unlabeled):
        # Get the sparse matrix of each dataset
        # Vectorizing the TRaining subset Lears the vocabulary Gets a sparse csc matrix with fit_transform(data_train.data).
        # 'scale' normalizes before fitting. It is required since the LinearSVC is very sensitive to extreme values
        X_train = self._instance.fit_transform(data_train.data)

        # Vectorizing the TEsting subset by using the vocabulary and document frequencies already learned by fit_transform with the TRainig subset.
        # print("Vectorizing the test set")
        X_test = self._instance.transform(data_test.data)
        print("X_test n_samples: %d, n_features: %d" % X_test.shape)
        # Extracting features from the unlabled dataset using the same vectorizer

        X_unlabeled = self._instance.transform(data_unlabeled.data)
        print("X_unlabeled n_samples: %d, n_features: %d" % X_unlabeled.shape)

        return X_train, data_train.target, X_test, data_test.target, X_unlabeled

# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


class TfidfBasedVectorizer(SklearnBasedVectorizer):

    def __init__(self, encoding):
        SklearnBasedVectorizer.__init__(self)
        self._instance = TfidfVectorizer(encoding=encoding, use_idf=True, norm='l2', binary=False, sublinear_tf=True,
                                     min_df=0.001, max_df=1.0, ngram_range=(1, 2), analyzer='word')


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


class CountBasedVectorizer(SklearnBasedVectorizer):

    def __init__(self):
        SklearnBasedVectorizer.__init__(self) # super(MyFighters, self).__init__()
        self._instance = CountVectorizer(lowercase=False)
        # .get_feature_names()

    def _normalize_subsets_data(self, X_train, X_test, X_unlabeled):
        return X_train, X_test, X_unlabeled


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

class LabeledLineSentence(object):
    def __init__(self, sources):
        self.sources = sources

        flipped = {}

        # make sure that keys are unique
        for key, value in sources.items():
            if value not in flipped:
                flipped[value] = [key]
            else:
                raise Exception('Non-unique prefix encountered')

    def __iter__(self):
        for source, prefix in self.sources.items():
            with utils.smart_open(source) as fin:
                for item_no, line in enumerate(fin):
                    yield LabeledSentence(utils.to_unicode(line).split(), [prefix + '_%s' % item_no])

    def to_array(self):
        self.sentences = []
        for source, prefix in self.sources.items():
            with utils.smart_open(source) as fin:
                for item_no, line in enumerate(fin):
                    self.sentences.append(LabeledSentence(utils.to_unicode(line).split(), [prefix + '_%s' % item_no]))
        return self.sentences

    def sentences_perm(self):
        shuffle(self.sentences)
        return self.sentences


class Doc2VecBasedVectorizer(SklearnBasedVectorizer):

    def __init__(self):
        AbstractVectorizer.__init__(self)  # super(MyFighters, self).__init__()
        self.model = Doc2Vec(min_count=1, window=10, size=100, sample=1e-4, negative=5, workers=8)

    def vectorize(self, data_train, data_test, data_unlabeled):
        self._check_input_data(data_train, data_test, data_unlabeled)  # Check!

        y_train = data_train.target
        y_test = data_test.target
        X_train, X_test, X_unlabeled = self._normalize_subsets_data(data_train.data, data_test.data, data_unlabeled.data)

        sentences = self._load_docs_in_category_files(X_train, y_train, X_test, y_test, X_unlabeled)
        self.model.build_vocab(sentences.to_array())

        self.model = self._get_trained_model(sentences)

        self.get_training_vectors()

        return X_train, y_train, X_test, y_test, X_unlabeled

    def train_vectors(self, total_docs):

        train_arrays = numpy.zeros((total_docs, 100))
        train_labels = numpy.zeros(total_docs)

        # We simply put the positive ones at the first half of the array, and the negative ones at the second half.
        for i in range(12500):
            prefix_train_pos = 'TRAIN_POS_' + str(i)
            prefix_train_neg = 'TRAIN_NEG_' + str(i)
            train_arrays[i] = self.model[prefix_train_pos]
            train_arrays[12500 + i] = self.model[prefix_train_neg]
            train_labels[i] = 1
            train_labels[12500 + i] = 0

        y_train = train_labels  #TOCKECK!!!
        X_train = train_arrays  #TOCKECK!!!

        return train_arrays,


    def _get_trained_model(self, sentences, use_existing=True):

        if use_existing:
            self.model = Doc2Vec.load('./doc2vec_cati.d2v')
            if self.model:
                return self.model

        # This may take some mins. So indicate if you want to reuse an existing model (if any available)
        for epoch in range(10):
            self.model.train(sentences.sentences_perm())
        self.model.save('./doc2vec_cati.d2v')

    def _load_docs_in_category_files(self, X_train, y_train, X_test, y_test, X_unlabeled):
        sources = {
            'test-neg.txt': 'TEST_NEG',
            'test-pos.txt': 'TEST_POS',
            'train-neg.txt': 'TRAIN_NEG',
            'train-pos.txt': 'TRAIN_POS',
            'train-unsup.txt': 'TRAIN_UNS'
        }
        if not os.path.exists('test-neg.txt'):
            self._write_docs_in_categories(sources)



        return LabeledLineSentence(sources)

    def _write_docs_in_categories(self, sources):
        print("Writting")

        for attr, value in sources.__dict__.items():
            print(attr, value)
