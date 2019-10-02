from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn import preprocessing

class AbstractVectorizer():

    def _check_input_data(self, data_train, data_test, data_unlabeled):

        if (len(data_test.data) == 0):
            raise Exception('The test set is empty.')

        if (len(data_unlabeled) == 0):
            raise Exception('The target (unlabeled) set is empty.')

        if (len(data_train.data) == 0):
            raise Exception('The train set is empty.')

    def _normalize_subsets(self, X_train, y_train, X_test, y_test, X_unlabeled):

        # fits the model according to the training set (passing its data and the vectorized feature)
        # 'scale' normalizes before fitting. It is required since the LinearSVC is very sensitive to extreme values
        # normalized_X_train = scale(X_train, with_mean=False)
        scaler = preprocessing.StandardScaler(with_mean=False).fit(X_train)
        X_train = scaler.transform(X_train)
        X_test = scaler.transform(X_test)
        X_unlabeled = scaler.transform(X_unlabeled)

        return X_train, y_train, X_test, y_test, X_unlabeled


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


class TfidfBasedVectorizer(AbstractVectorizer):

    def __init__(self, encoding):
        AbstractVectorizer.__init__(self)
        self._instance = TfidfVectorizer(encoding=encoding, use_idf=True, norm='l2', binary=False, sublinear_tf=True,
                                     min_df=0.001, max_df=1.0, ngram_range=(1, 2), analyzer='word')

    def vectorize(self, data_train, data_test, data_unlabeled):

        self._check_input_data(data_train, data_test, data_unlabeled)  #Check!

        X_train, y_train, X_test, y_test, X_unlabeled = self._get_sparse_matrixes(data_train, data_test, data_unlabeled)

        return self._normalize_subsets(X_train, y_train, X_test, y_test, X_unlabeled)

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


class CountBasedVectorizer(TfidfBasedVectorizer):

    def __init__(self):
        TfidfBasedVectorizer.__init__(self, encoding="") # super(MyFighters, self).__init__()
        self._instance = CountVectorizer(lowercase=False)
        # .get_feature_names()

    def _normalize_subsets(self, X_train, y_train, X_test, y_test, X_unlabeled):
        return X_train, y_train, X_test, y_test, X_unlabeled


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


class HashBasedVectorizer(AbstractVectorizer):

    def __init__(self, encoding):
        self._instance = TfidfVectorizer(encoding=encoding, use_idf=True, norm='l2', binary=False, sublinear_tf=True,
                                     min_df=0.001, max_df=1.0, ngram_range=(1, 2), analyzer='word')