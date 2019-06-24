import numpy as np

class ActiveLearningSampler:

    def set_classifier(self, classifier):
        self.classifier = classifier

    def get_samples(self, num_questions):

        # compute absolute confidence for each unlabeled sample in each class
        # decision_function gets "the confidence score for a sample is the signed distance of that sample to the hyperplane" https://scikit-learn.org/stable/modules/generated/sklearn.svm.LinearSVC.html
        decision = self.classifier.model.decision_function(self.classifier.X_unlabeled)  # Predicts confidence scores for samples. X_Unlabeled is a csr_matrix. Scipy offers variety of sparse matrices functions that store only non-zero elements.
        confidences = np.abs(decision)  # Calculates the absolute value element-wise
        predictions = self.classifier.model.predict(self.classifier.X_unlabeled)

        # average abs(confidence) over all classes for each unlabeled sample (if there is more than 2 classes)
        if (len(self.classifier.categories) > 2):
            confidences = np.average(confidences, axix=1)
            print("when categories are more than 2")

        sorted_samples = np.argsort(confidences)  # argsort returns the indices that would sort the array
        question_samples = sorted_samples[0:num_questions].tolist()

        selected_samples = self.classifier.fill_questions(question_samples, predictions, confidences, self.classifier.categories)

        self.classifier.last_samples = sorted_samples
        self.classifier.last_confidences = confidences
        self.classifier.last_predictions = predictions

        return selected_samples

    def post_sampling(self):
        return

class UncertaintySampler(ActiveLearningSampler):

    def __init__(self, **kwargs):
        return



class BigramsRetweetsSampler(ActiveLearningSampler):

    def __init__(self, **kwargs):
        self.max_samples_to_sort = kwargs["max_samples_to_sort"]
        self.index = kwargs["index"]
        self.session = kwargs["session"]
        self.text_field = kwargs["text_field"]
        self.cnf_weight = kwargs["cnf_weight"]
        self.ret_weight = kwargs["ret_weight"]
        self.bgr_weight = kwargs["bgr_weight"]
        self.similarity_percentage = "75%"
        return

    def get_samples(self, num_questions):
        # retrieve from the classifier:
        # model, X_train, X_test, y_train, y_test, X_unlabeled, categories

        # Getting
        top_bigrams = self.classifier.get_top_bigrams(index=self.index, session=self.session, results_size=self.max_samples_to_sort)  # session=kwargs["session"] + "_tmp"
        top_retweets = self.classifier.get_top_retweets(index=self.index, session=self.session, results_size=self.max_samples_to_sort)  # session=kwargs["session"] + "_tmp"

        # compute absolute confidence for each unlabeled sample in each class
        decision = self.classifier.model.decision_function(
            self.classifier.X_unlabeled)  # Predicts confidence scores for samples. X_Unlabeled is a csr_matrix. Scipy offers variety of sparse matrices functions that store only non-zero elements.
        confidences = np.abs(decision)  # Calculates the absolute value element-wise
        predictions = self.classifier.model.predict(self.classifier.X_unlabeled)
        # average abs(confidence) over all classes for each unlabeled sample (if there is more than 2 classes)
        if (len(self.classifier.categories) > 2):
            confidences = np.average(confidences, axix=1)
            print("when categories are more than 2")

        sorted_samples_by_conf = np.argsort(confidences)  # argsort returns the indices that would sort the array

        self.classifier.last_samples = sorted_samples_by_conf
        self.classifier.last_confidences = confidences
        self.classifier.last_predictions = predictions

        question_samples = self.classifier.get_unique_sorted_samples_by_conf(sorted_samples_by_conf, self.classifier.data_unlabeled,
                                                                  self.max_samples_to_sort)  # returns just unique (removes duplicated files)
        formatted_samples = self.classifier.fill_questions(question_samples, predictions, confidences,
                                                self.classifier.categories, top_retweets,
                                                top_bigrams, self.max_samples_to_sort, self.text_field)

        selected_samples = sorted(formatted_samples, key=lambda k: ( self.cnf_weight * k["cnf_pos"] +
                                                                     self.ret_weight * k["ret_pos"] +
                                                                     self.bgr_weight * k["bgr_pos"]), reverse=False)
        self.last_questions = selected_samples[0:num_questions]
        return self.last_questions

    def post_sampling(self):
        print("Moving duplicated documents")
        duplicated_answers = self.classifier.get_duplicated_answers(questions=self.last_questions, index=self.index,
                                                                    session=self.session, text_field=self.text_field, similarity_percentage=self.similarity_percentage)
        self.classifier.move_answers_to_training_set(duplicated_answers)