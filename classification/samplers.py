import numpy as np
from mabed.es_connector import Es_connector
import os
from sklearn.svm import LinearSVC

# Sampling methods: UncertaintySampler, JackardBasedUncertaintySampler, BigramsRetweetsSampler, DuplicatedDocsSampler

class ActiveLearningSampler:

    def set_classifier(self, classifier):
        self.classifier = classifier

    def get_samples(self, num_questions):
        pass

    def post_sampling(self, answers=None):
        pass

    def update_docs_by_ids(self, docs_matches, pred_labed):

        if len(docs_matches)>0:

            my_connector = Es_connector(index=self.index)  # , config_relative_path='../')
            query = {
                "query": {
                    "bool": {
                        "should": docs_matches,
                        "minimum_should_match": 1
                    }
                }
            }
            script = "ctx._source." + self.session + " = '" + pred_labed + "'"
            my_connector.update_by_query(query, script)

class UncertaintySampler(ActiveLearningSampler):

    def __init__(self, **kwargs):
        self.model = LinearSVC(loss='squared_hinge', penalty='l2', dual=False, tol=1e-3)
        return

    def get_samples(self, num_questions):

        # keep all the sorted samples
        self.last_samples = np.argsort(self.classifier.last_confidences)  # argsort returns the indices that would sort the array

        # get the N required samples for user validation
        sub_samples = self.last_samples[0:num_questions].tolist()

        # format the samples
        return self.classifier.fill_questions(sub_samples, self.classifier.last_predictions, self.classifier.last_confidences, self.classifier.categories)

    def post_sampling(self, answers=None):
        print("Persisting answers so they have an infuelce on the ngrams")

        positive_docs_ids_matches = [{"match": {"id_str": ans["str_id"]}} for ans in answers if ans["pred_label"] == "confirmed"]
        negative_docs_ids_matches = [{"match": {"id_str": ans["str_id"]}} for ans in answers if
                                      ans["pred_label"] == "negative"]

        self.update_docs_by_ids(positive_docs_ids_matches, "confirmed")
        self.update_docs_by_ids(positive_docs_ids_matches, "negative")


class BigramsRetweetsSampler(ActiveLearningSampler):

    def __init__(self, **kwargs):
        self.max_samples_to_sort = kwargs["max_samples_to_sort"]
        self.index = kwargs["index"]
        self.session = kwargs["session"]
        self.text_field = kwargs["text_field"]
        self.cnf_weight = kwargs["cnf_weight"]
        self.ret_weight = kwargs["ret_weight"]
        self.bgr_weight = kwargs["bgr_weight"]
        self.model = LinearSVC(loss='squared_hinge', penalty='l2', dual=False, tol=1e-3)
        return

    def get_samples(self, num_questions):

        # Getting
        top_bigrams = self.classifier.get_top_bigrams(index=self.index, session=self.session, results_size=self.max_samples_to_sort)  # session=kwargs["session"] + "_tmp"
        top_retweets = self.classifier.get_top_retweets(index=self.index, session=self.session, results_size=self.max_samples_to_sort)  # session=kwargs["session"] + "_tmp"

        self.last_samples = np.argsort(self.classifier.last_confidences)  # argsort returns the indices that would sort the array

        question_samples = self.classifier.get_unique_sorted_samples_by_conf(self.last_samples,
                                                                             self.classifier.data_unlabeled,
                                                                  self.max_samples_to_sort)  # returns just unique (removes duplicated files)

        formatted_samples = self.classifier.fill_questions(question_samples, self.classifier.last_predictions, self.classifier.last_confidences,
                                                self.classifier.categories, top_retweets,
                                                top_bigrams, self.max_samples_to_sort, self.text_field)

        selected_samples = sorted(formatted_samples, key=lambda k: ( self.cnf_weight * k["cnf_pos"] +
                                                                     self.ret_weight * k["ret_pos"] +
                                                                     self.bgr_weight * k["bgr_pos"]), reverse=False)
        self.last_questions = selected_samples[0:num_questions]
        return self.last_questions

    def post_sampling(self, answers=None):
        print("Persisting answers so they have an infuelce on the ngrams")

        positive_docs_ids_matches = [{"match": {"id_str": ans["str_id"]}} for ans in answers if ans["pred_label"] == "confirmed"]
        negative_docs_ids_matches = [{"match": {"id_str": ans["str_id"]}} for ans in answers if
                                      ans["pred_label"] == "negative"]

        self.update_docs_by_ids(positive_docs_ids_matches, "confirmed")
        self.update_docs_by_ids(positive_docs_ids_matches, "negative")


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

class MoveDuplicatedDocsSampler(ActiveLearningSampler):

    def __init__(self, **kwargs):

        self.index = kwargs["index"]
        self.session = kwargs["session"]
        self.text_field = kwargs["text_field"]
        self.similarity_percentage = kwargs["similarity_percentage"]
        self.model = LinearSVC(loss='squared_hinge', penalty='l2', dual=False, tol=1e-3)
        return

    def get_samples(self, num_questions):

        sorted_samples = np.argsort(self.classifier.last_confidences)  # argsort returns the indices that would sort the array
        question_samples = sorted_samples[0:num_questions].tolist()
        selected_samples = self.classifier.fill_questions(question_samples, self.classifier.last_predictions, self.classifier.last_confidences,
                                                          self.classifier.categories)

        self.last_samples = sorted_samples
        self.last_questions = selected_samples

        return selected_samples

    def post_sampling(self, answers=None):
        print("Moving duplicated documents")
        duplicated_answers = self.get_similar_docs(questions=self.last_questions,
                                                                    index=self.index,
                                                                    session=self.session,
                                                                    text_field=self.text_field,
                                                                    similarity_percentage=self.similarity_percentage)

        self.classifier.move_answers_to_training_set(duplicated_answers)


    def get_similar_docs(self, **kwargs):

        my_connector = Es_connector(index=kwargs["index"])  # , config_relative_path='../')
        duplicated_docs = []

        # IT SHOULD BE BETTER TO TRY GETTING THE DUPLICATES FROM THE MATRIX
        splitted_questions = []
        target_bigrams = []
        # Process by 90
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
            #bigrams_matches = []

            if isinstance(field_content, list):
                #for f_content in field_content:
                    #bigrams_matches.append({"match": {field + ".keyword": f_content}})
                raise NameError('Hi there. Please implement this or just use a non-array field. E.g. text or text_images instead of 2grams.')

            query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "more_like_this": {
                                    "fields": [
                                        "text_images"
                                    ],
                                    "like": field_content,
                                    "min_term_freq": 1,
                                    "max_query_terms": 25,
                                    "minimum_should_match": similarity_percentage
                                }
                            },
                            {
                                "match": {session: "proposed"}
                            },
                            {
                                "exists": {"field": field}
                            }
                        ]
                    }
                }
            }
            #print("TARGET QUERY:\n", query)
            #print(similarity_percentage)

            docs_with_noise = my_connector.search(query)

            if len(docs_with_noise["hits"]["hits"]) > 1:

                for tweet in docs_with_noise["hits"]["hits"]:

                    label = [doc for doc in splitted_questions if
                             doc_bigrams["_source"]["id_str"] == doc["str_id"]][0]["label"]

                    if tweet["_source"]["id_str"] not in concatenated_ids:
                        duplicated_docs.append({
                            "filename": tweet["_source"]["id_str"],
                            "target_label": label,
                            "text_images": tweet["_source"]["text_images"]
                        })
                        #print(tweet["_source"]["text_images"])

        return duplicated_docs

# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


class JackardBasedUncertaintySampler(MoveDuplicatedDocsSampler):

    def __init__(self, **kwargs):

        #super(UncertaintySampler, self).__init__()
        MoveDuplicatedDocsSampler.__init__(self, **kwargs)
        self.low_confidence_limit = float(kwargs["low_confidence_limit"])
        return

    def get_samples(self, num_questions):

        sorted_samples = np.argsort(self.classifier.last_confidences)  # argsort returns the indices that would sort the array
        question_samples = sorted_samples.tolist()
        selected_samples = self.classifier.fill_questions(question_samples, self.classifier.last_predictions, self.classifier.last_confidences, self.classifier.categories)

        # Filter and get all the tweets with a low confidence
        full_low_level_confidency=[]
        for sample in selected_samples:
            if sample["confidence"]<self.low_confidence_limit:
                full_low_level_confidency.append(sample)

        if(len(full_low_level_confidency)<num_questions):
            #full_low_level_confidency = selected_samples.clone()
            raise Exception('ERROR: the number of low-level-confidence predictions is not enough to retrieve ' + str(num_questions) + ' samples.')


        # Get the accumulated jackard score of each document respect to the remaining ones
        for sample in full_low_level_confidency:
            for anotherSample in full_low_level_confidency:
                if sample != anotherSample:
                    if "jackard_score" not in sample:
                        sample["jackard_score"] = self.get_jaccard_sim(sample["analyzed_content"], anotherSample["analyzed_content"])
                    else:
                        sample["jackard_score"] += self.get_jaccard_sim(sample["analyzed_content"], anotherSample["analyzed_content"])

        # Sort the documents according to the highest jackard score
        re_sorted_samples = sorted(full_low_level_confidency, key=lambda k: (k["jackard_score"]), reverse=True)

        # Get 20 non repeated documents
        selected_samples = []
        top_samples_text = []
        for sample in re_sorted_samples:
                if sample["analyzed_content"] not in top_samples_text:  # text
                    selected_samples.append(sample)
                    top_samples_text.append(sample["analyzed_content"])
                if len(selected_samples) >= num_questions:
                    break

        self.last_samples = sorted_samples
        self.last_questions = selected_samples  # to be used in the post sampling

        return selected_samples

    def get_jaccard_sim(self, str1, str2):
        a = set(str1.split())
        b = set(str2.split())
        c = a.intersection(b)
        return float(len(c)) / (len(a) + len(b) - len(c))

    def post_sampling(self, answers=None):

        duplicated_answers = self.get_similar_docs(questions=self.last_questions,
                                                                    index=self.index,
                                                                    session=self.session,
                                                                    text_field=self.text_field,
                                                                    similarity_percentage=self.similarity_percentage)
        if len(duplicated_answers):
            print("Moving duplicated documents")
            self.classifier.move_answers_to_training_set(duplicated_answers)

    def get_similar_docs(self, **kwargs):

        if len(kwargs["questions"]) == 0:
            return []

        my_connector = Es_connector(index=kwargs["index"])  # , config_relative_path='../')
        duplicated_docs = []

        docs_ids_matches = [{"match": {"id_str": {"query": question["str_id"] }}} for question in kwargs["questions"]]

        docs_original_textual_content = my_connector.search({
            "query": {
                "bool": {
                    "should": docs_ids_matches,
                    "minimum_should_match": 1,
                    "must": [
                        {
                            "match": {
                                kwargs["session"]: "proposed"
                            }
                        }
                    ]
                }
            }
        })

        for doc in docs_original_textual_content["hits"]["hits"]:
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "term": {
                                    "text.keyword": {
                                        "value": doc["_source"][kwargs["text_field"]]
                                    }
                                }
                            }
                        ]
                    }
                }
            }

            matching_docs = my_connector.search(query)
            if matching_docs["hits"]["total"]>1:

                label = [question for question in kwargs["questions"] if question["str_id"] == doc["_source"]["id_str"]][0]["label"]

                for dup_doc in matching_docs["hits"]["hits"]:
                    duplicated_docs.append({
                        "filename": dup_doc["_source"]["id_str"],
                        "label": label,
                        kwargs["text_field"]: dup_doc["_source"][kwargs["text_field"]]
                    })

        return duplicated_docs




class ConsecutiveDeferredMovDuplicatedDocsSampler(MoveDuplicatedDocsSampler):

    def __init__(self, **kwargs):

        MoveDuplicatedDocsSampler.__init__(self, **kwargs)

        self.target_min_confidence = kwargs["target_min_confidence"]
        self.similar_docs = {}
        self.confident_loop = kwargs["confident_loop"]
        self.model = LinearSVC(loss='squared_hinge', penalty='l2', dual=False, tol=1e-3)
        return

    def post_sampling(self, answers=None):

        # Getting similar docs
        docs = self.get_similar_docs(questions=self.last_questions, index=self.index, session=self.session,
                                             text_field=self.text_field, similarity_percentage=self.similarity_percentage)

        # docs = self.fill_docs_with_predictions(docs, self.classifier.last_confidences, self.classifier.last_predictions, self.classifier.categories)
        self.append_similar_docs(docs)
        self.process_all_similar_docs()

    def fill_docs_with_predictions(self, docs, confidences, predictions, categories):

        print("Filling duplicated documents with predictions. Total docs: ", len(docs))
        #total_documents = len(docs)
        #accum_docs = 0



        found_docs_predictions = []  # If you are using the debu version, you may not found all the duplicated docs (since your unlabeled set is smaller, but we are looking for duplicated docs in the full unlabeled set)
        for doc in docs:

            # filtered_doc = [f_path for f_path in self.classifier.data_unlabeled.filenames if
            # os.path.splitext(os.path.basename(f_path))[0] == doc["filename"]]

            for f_path in self.classifier.data_unlabeled.filenames:
                f_name = os.path.splitext(os.path.basename(os.path.normpath(f_path)))[0]

                if f_name == doc["filename"]:
                    f_index, = np.where(self.classifier.data_unlabeled.filenames == f_path)[0]

                    doc["confidence"] = confidences[f_index]
                    doc["label"] = categories[int(predictions[f_index])]
                    #f_text_images = self.classifier.data_unlabeled.data[f_index]

                    found_docs_predictions.append(doc)

                    break

            #accum_docs+=1
            #print(accum_docs*100/total_documents, "%")

        return found_docs_predictions

    def get_unique_docs(self, new_similar_docs):

        unique_ids = set()
        unique_docs = set()

        for doc in new_similar_docs:
            if doc["filename"] not in unique_ids:
                unique_ids.add(doc["filename"])
                unique_docs.add(doc)

        return list(unique_docs)

    def append_similar_docs(self, docs):

        #For a matter of performance, we do not traverse the array twice
        for doc in docs:
            doc_id = doc["filename"]

            self.similar_docs[doc_id] = {
                "accum": self.similar_docs.get(doc_id, {"accum":0})["accum"],
                "label": None, # doc["label"], We'll do it later to avoid doing it twice
                "confidence": None,
                "text_images": doc["text_images"] # doc["confidence"]
            }

    def process_all_similar_docs(self):

        docs_ready_to_move = []
        print("Updating similar docs. Total: ", len(self.similar_docs))

        min_conf = min(self.classifier.last_confidences)
        max_conf = max(self.classifier.last_confidences)

        for doc_id in self.similar_docs.copy():

            # Get the predictions on this loop...
            prev_label = self.similar_docs[doc_id]["label"]
            prediction = self.get_prediction(doc_id)

            # Remove those docs which labeld do not match from loop to loop. Increase the others',
            # and add the label and confidence
            # prediction could be None if we are in debug mode

            if prediction == None or (prev_label != None and prev_label != prediction["label"]):
                del self.similar_docs[doc_id]
            else:

                scaled_confidence = prediction["confidence"] - min_conf / max_conf - min_conf

                if scaled_confidence < self.target_min_confidence:
                    del self.similar_docs[doc_id]

                else:
                    self.similar_docs[doc_id]["accum"] += 1
                    self.similar_docs[doc_id]["label"] = prediction["label"]
                    self.similar_docs[doc_id]["confidence"] = prediction["confidence"]

                    self.similar_docs[doc_id]["text_images_real"] = self.similar_docs[doc_id]["text_images"]
                    self.similar_docs[doc_id]["text_images"] = prediction["text_images"]

                    # Collect and remove those docs which are there for more than X loops
                    if self.similar_docs[doc_id]["accum"] >= self.confident_loop:
                        # docs_ready_to_move[doc_id] = self.similar_docs[doc_id]
                        self.similar_docs[doc_id]["str_id"] = doc_id
                        self.similar_docs[doc_id]["filename"] = prediction["filename"]
                        docs_ready_to_move.append(self.similar_docs[doc_id])
                        del self.similar_docs[doc_id]

        print("Kept docs: ", len(self.similar_docs))

        if len(docs_ready_to_move)>0:

            print("Moving docs with conf. " + str(self.target_min_confidence) + ": ", len(docs_ready_to_move))
            self.classifier.move_answers_to_training_set(docs_ready_to_move)

    def get_prediction(self, doc_id):

        pred = None

        for f_path in self.classifier.data_unlabeled.filenames:
            f_name = os.path.splitext(os.path.basename(os.path.normpath(f_path)))[0]

            if f_name == doc_id:
                f_index, = np.where(self.classifier.data_unlabeled.filenames == f_path)[0]

                pred = {}
                pred["confidence"] = self.classifier.last_confidences[f_index]
                pred["label"] = self.classifier.categories[int(self.classifier.last_predictions[f_index])]
                pred["filename"] = self.classifier.data_unlabeled.filenames[f_index]
                pred["text_images"] = self.classifier.data_unlabeled.data[f_index]
                break

        return pred
