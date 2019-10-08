from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn import preprocessing
from gensim import utils
from gensim.models.doc2vec import LabeledSentence
from gensim.models import Doc2Vec
import numpy
from random import shuffle
import os
import shutil
import numpy as np

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

    def __init__(self):
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
        X_train = self._instance.fit_transform(data_train.data)  # transforms .data (which contains text) into numbers. The it fits the model to these numbers.

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

    def __init__(self, encoding=None):
        SklearnBasedVectorizer.__init__(self)
        if encoding == None:
            encoding = "latin1"
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

class LabeledLineSentence(object):   # HELPER; NOT A VECTORIZER
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
        self.vector_size = 100  # Dimensionality of the feature vectors
        self.model = None

    def vectorize(self, data_train, data_test, data_unlabeled):

        self._check_input_data(data_train, data_test, data_unlabeled)
        categories = data_train.target_names
        sentences = self._load_docs_in_category_files(data_train.data, data_train.target, data_test.data, data_test.target, data_unlabeled.data, categories)
        #if self.model.vocabulary.raw_vocab == None:  # Just when loading the first time

        self.model = self._get_trained_model(sentences, use_existing=False, epoch=5)  # Around 4 minutes to get a trained model with 2 epoch

        train_arrays, train_labels = self.get_labeled_vectors(categories, sentences.sentences, 'TRAIN_POS_', 'TRAIN_NEG_')
        test_arrays, test_labels = self.get_labeled_vectors(categories, sentences.sentences, 'TEST_POS_', 'TEST_NEG_')
        unlabeled_arrays = self.get_unlabeled_vectors(sentences.sentences, 'TRAIN_UNS_')

        return train_arrays, train_labels, test_arrays, test_labels, unlabeled_arrays  # data_unlabeled.data

    def get_labeled_vectors(self, categories, sentences, pos_label, neg_label):

        total_docs = test_size = len([stc for stc in sentences if
                          stc.tags[0].startswith(pos_label) or stc.tags[0].startswith(
                              neg_label)])  # len(data_train.data) returns 3000

        # train_size = self.model.corpus_count
        train_arrays = numpy.zeros((total_docs, self.vector_size))  # Its taking just the 100 top vectors
        train_labels = numpy.zeros(total_docs)

        train_idx = 0
        pos_index = [index for index, label in enumerate(categories) if label == "confirmed"][0]
        train_idx = self.extract_vectors_to(pos_label, train_idx, train_arrays, train_labels, pos_index)

        neg_index = [index for index, label in enumerate(categories) if label == "negative"][0]
        train_idx = self.extract_vectors_to(neg_label, train_idx, train_arrays, train_labels, neg_index)

        return train_arrays, train_labels

    def get_unlabeled_vectors(self, sentences, prefix_label):

        total_docs = test_size = len([stc for stc in sentences if
                          stc.tags[0].startswith(prefix_label)])
        vectors = numpy.zeros((total_docs, self.vector_size))  # Its taking just the 100 top vectors

        prefix_idx = 0
        keep_retrieving = True
        while keep_retrieving == True:
            prefix_train_pos = prefix_label + str(prefix_idx)
            try:
                vectors[prefix_idx] = self.model[prefix_train_pos]
                prefix_idx += 1
            except KeyError as ke:
                print("Stop retrieving docs at ", prefix_idx)
                keep_retrieving = False

        return vectors

    def extract_vectors_to(self, prefix_label, train_index, train_arrays, train_labels, label):

        prefix_idx=0
        keep_retrieving = True
        while keep_retrieving == True:
            prefix_train_pos = prefix_label + str(prefix_idx)
            try:
                vec_doc = self.model[prefix_train_pos]
                train_arrays[train_index] = vec_doc
                train_labels[train_index] = label
                prefix_idx += 1
                train_index += 1
            except KeyError as ke:
                #print("break!")
                keep_retrieving = False
            except IndexError as ke:
                keep_retrieving = False
                print("*** Be careful, this error might indicate that the model has loaded other data than the one you are trying to use")

        return train_index

    def train_vectors(self, total_docs):

        train_arrays = numpy.zeros((total_docs, self.vector_size))
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


    def _get_trained_model(self, sentences, use_existing=True, epoch=None):

        # model_filename = os.path.join("classification", 'doc2vec_cati.d2v')
        # if use_existing and os.path.exists(model_filename):
        #     model = Doc2Vec.load(model_filename)
        #     if model:
        #         return model
        # if self.model == None:

        self.model = Doc2Vec(min_count=1, window=10, vector_size=self.vector_size, sample=1e-4, negative=5,
                             workers=8)
        target_sentences = sentences.to_array()  # this must be executed, otherwise the sentences_perm() cannot be called
        self.model.build_vocab(target_sentences)

        if epoch == None:
            epoch = self.model.epochs

        # This may take some mins. So indicate if you want to reuse an existing model (if any available)
        # for epoch in range(10):
        perm_sentences = sentences.sentences_perm()
        self.model.train(perm_sentences, total_examples=self.model.corpus_count, epochs=epoch)
        # self.model.save(model_filename)
        return self.model

    def _load_docs_in_category_files(self, X_train, y_train, X_test, y_test, X_unlabeled, categories):

        subfolder = os.path.join("classification", "tmp_doc2vec")
        if os.path.exists(subfolder):
            shutil.rmtree(subfolder)
        os.makedirs(subfolder)

        sources = {
            os.path.join(subfolder, 'test-neg.txt'): 'TEST_NEG',
            os.path.join(subfolder, 'test-pos.txt'): 'TEST_POS',
            os.path.join(subfolder, 'train-neg.txt'): 'TRAIN_NEG',
            os.path.join(subfolder, 'train-pos.txt'): 'TRAIN_POS',
            os.path.join(subfolder, 'train-unsup.txt'): 'TRAIN_UNS'
        }

        self._download_files(categories, "confirmed", X_test, y_test, subfolder, 'test-pos.txt')
        self._download_files(categories, "negative", X_test, y_test, subfolder, 'test-neg.txt')
        self._download_files(categories, "confirmed", X_train, y_train, subfolder, 'train-pos.txt')
        self._download_files(categories, "negative", X_train, y_train, subfolder, 'train-neg.txt')
        self._download_files(categories, None, X_unlabeled, None, subfolder, 'train-unsup.txt')

        return LabeledLineSentence(sources)

    def _download_files(self, categories, target_label_name, X_data, y_labels, subfolder, filename_to_write):

        if target_label_name != None:
            pos_index = [index for index, label in enumerate(categories) if label == target_label_name][0]
            test_pos = [X_data[index] for index, label in enumerate(y_labels) if label == pos_index]
        else:
            test_pos = X_data

        filename_to_write = os.path.join(subfolder, filename_to_write)
        file = open(filename_to_write, "a", encoding="utf-8")

        for index, line in enumerate(test_pos):
            line = line.replace('\n', '').replace('\r', '')
            file.write(line)
            if (index < len(test_pos) - 1):
                file.write('\n')

        file.close()

    def _write_docs_in_categories(self, sources):
        print("Writting")

        for attr, value in sources.items():
            print(attr, value)
