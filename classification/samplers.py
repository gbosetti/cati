import numpy as np
from mabed.es_connector import Es_connector

# Sampling methods: UncertaintySampler, BigramsRetweetsSampler, DuplicatedDocsSampler

class ActiveLearningSampler:

    def set_classifier(self, classifier):
        self.classifier = classifier

    def get_samples(self, num_questions):
        pass

    def post_sampling(self):
        pass

class UncertaintySampler(ActiveLearningSampler):

    def __init__(self, **kwargs):
        return

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



class BigramsRetweetsSampler(ActiveLearningSampler):

    def __init__(self, **kwargs):
        self.max_samples_to_sort = kwargs["max_samples_to_sort"]
        self.index = kwargs["index"]
        self.session = kwargs["session"]
        self.text_field = kwargs["text_field"]
        self.cnf_weight = kwargs["cnf_weight"]
        self.ret_weight = kwargs["ret_weight"]
        self.bgr_weight = kwargs["bgr_weight"]
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


class DuplicatedDocsSampler(ActiveLearningSampler):

    def __init__(self, **kwargs):

        self.index = kwargs["index"]
        self.session = kwargs["session"]
        self.text_field = kwargs["text_field"]
        self.similarity_percentage = "75%"
        return

    def get_samples(self, num_questions):

        decision = self.classifier.model.decision_function(self.classifier.X_unlabeled)  # Predicts confidence scores for samples. X_Unlabeled is a csr_matrix. Scipy offers variety of sparse matrices functions that store only non-zero elements.
        confidences = np.abs(decision)  # Calculates the absolute value element-wise
        predictions = self.classifier.model.predict(self.classifier.X_unlabeled)

        sorted_samples = np.argsort(confidences)  # argsort returns the indices that would sort the array
        question_samples = sorted_samples[0:num_questions].tolist()
        selected_samples = self.classifier.fill_questions(question_samples, predictions, confidences,
                                                          self.classifier.categories)

        self.classifier.last_samples = sorted_samples
        self.classifier.last_confidences = confidences
        self.classifier.last_predictions = predictions

        self.last_questions = selected_samples

        return selected_samples

    def post_sampling(self):
        print("Moving duplicated documents")
        duplicated_answers = self.get_duplicated_answers(questions=self.last_questions,
                                                                    index=self.index,
                                                                    session=self.session,
                                                                    text_field=self.text_field,
                                                                    similarity_percentage=self.similarity_percentage)
        self.classifier.move_answers_to_training_set(duplicated_answers)

    def get_duplicated_answers(self, **kwargs):

        my_connector = Es_connector(index=kwargs["index"])  # , config_relative_path='../')
        duplicated_docs = []

        # IT SHOULD BE BETTER TO TRY GETTING THE DUPLICATES FROM THE MATRIX
        splitted_questions = []
        target_bigrams = []
        for question in kwargs["questions"]:

            splitted_questions.append(question)
            if (len(splitted_questions) > 99):
                matching_docs = self.process_duplicated_answers(my_connector, kwargs["session"], splitted_questions,
                                                                kwargs["text_field"],
                                                                kwargs["similarity_percentage"])
                duplicated_docs += matching_docs
                splitted_questions = []  # re init

        if len(splitted_questions) > 0:
            matching_docs = self.process_duplicated_answers(my_connector, kwargs["session"], splitted_questions,
                                                            kwargs["text_field"], kwargs["similarity_percentage"])
            duplicated_docs += matching_docs

        return duplicated_docs

    def join_ids(self, questions, field_name="filename"):

        # print("all the questions", kwargs["questions"])
        all_ids = ""
        for question in questions:
            # Adding the label field
            question_id = self.classifier.extract_filename_no_ext(question[field_name])
            all_ids += question_id + " or "

        all_ids = all_ids[:-3]

        return all_ids

    def process_duplicated_answers(self, my_connector, session, splitted_questions, field, similarity_percentage):

        duplicated_docs = []
        concatenated_ids = self.join_ids(splitted_questions)
        matching_docs = my_connector.search({
            "query": {
                "match": {
                    "id_str": concatenated_ids
                }
            }
        })

        for doc_bigrams in matching_docs["hits"]["hits"]:

            field_content = doc_bigrams["_source"][field]
            bigrams_matches = []

            if isinstance(field_content, list):
                for f_content in field_content:
                    bigrams_matches.append({"match": {field + ".keyword": f_content}})

            else:
                bigrams_matches.append({"match": {field + ".keyword": field_content}})

            query = {
                "query": {
                    "bool": {
                        "should": bigrams_matches,
                        "minimum_should_match": similarity_percentage,
                        "must": [{
                            "exists": {"field": field}
                        }, {
                            "match": {
                                session: "proposed"
                            }
                        }]
                    }
                }
            }
            # print("TARGET QUERY:\n", query)

            docs_with_noise = my_connector.search(query)

            if len(docs_with_noise["hits"]["hits"]) > 1:

                for tweet in docs_with_noise["hits"]["hits"]:

                    label = [doc for doc in splitted_questions if
                             doc_bigrams["_source"]["id_str"] == doc["str_id"]][0]["label"]

                    if tweet["_source"]["id_str"] not in concatenated_ids:
                        duplicated_docs.append({
                            "filename": tweet["_source"]["id_str"],
                            "label": label
                        })

        return duplicated_docs
