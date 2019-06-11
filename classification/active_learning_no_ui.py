from classification.active_learning import ActiveLearning
from datetime import datetime
from mabed.es_connector import Es_connector
from BackendLogger import BackendLogger
import os

class ActiveLearningNoUi:

    def __init__(self, **kwargs):

        logs_path = os.path.join(os.getcwd(), "classification", "logs", kwargs["logs_filename"])
        folder = os.path.dirname(logs_path)
        if not os.path.exists(folder):
            os.makedirs(folder)
        self.backend_logger = BackendLogger(logs_path)

        self.classifier = ActiveLearning()

    def clean_logs(self, **kwargs):

        self.backend_logger.clear_logs()

    def join_ids(self, questions, field_name="filename"):

        # print("all the questions", kwargs["questions"])
        all_ids = ""
        for question in questions:
            # Adding the label field
            question_id = self.classifier.extract_filename_no_ext(question[field_name])
            all_ids += question_id + " or "

        all_ids = all_ids[:-3]

        return all_ids

    def get_answers(self, **kwargs):

        my_connector = Es_connector(index=kwargs["index"])  # , config_relative_path='../')
        wrong_labels=0

        all_ids = self.join_ids(kwargs["questions"])

        res = my_connector.search({
            "query": {
                "match": {
                    "id_str": all_ids
                }
            }
        })

        for question in kwargs["questions"]:

            question_id = self.classifier.extract_filename_no_ext(question["filename"])
            gt_tweet = [tweet for tweet in res["hits"]["hits"] if tweet["_source"]["id_str"] == question_id]
            question["label"] = gt_tweet[0]["_source"][kwargs["gt_session"]]

            if question["pred_label"] != question["label"]:
                wrong_labels += 1

        # print(json.dumps(kwargs["questions"], indent=4, sort_keys=True))
        return kwargs["questions"], wrong_labels

    def get_duplicated_answers(self, **kwargs):

        my_connector = Es_connector(index=kwargs["index"])  # , config_relative_path='../')
        duplicated_docs=[]

        # IT SHOULD BE BETTER TO TRY GETTING THE DUPLICATES FROM THE MATRIX
        splitted_questions = []
        target_bigrams = []
        for question in kwargs["questions"]:

            splitted_questions.append(question)
            if(len(splitted_questions)>99):
                matching_docs = self.process_duplicated_answers(my_connector, kwargs["session"], splitted_questions)
                duplicated_docs += matching_docs
                splitted_questions=[] # re init

        if len(splitted_questions)>0:
            matching_docs = self.process_duplicated_answers(my_connector, kwargs["session"], splitted_questions)
            duplicated_docs += matching_docs

        return duplicated_docs

    def process_duplicated_answers(self, my_connector, session, splitted_questions):

        duplicated_docs = []
        concatenated_ids = self.join_ids(splitted_questions)
        matching_bigrams = my_connector.search({
            "query": {
                "match": {
                    "id_str": concatenated_ids
                }
            }
        })

        for doc_bigrams in matching_bigrams["hits"]["hits"]:

            bigrams = doc_bigrams["_source"]["2grams"]
            bigrams_matches = []
            for bigram in bigrams:
                bigrams_matches.append({"match": {"2grams.keyword": bigram}})

            # query = {
            #     "query": {
            #         "bool": {
            #             "must": bigrams_matches
            #         }
            #     }
            # }
            query = {
                #"_source": ["2grams", "text", "id_str"],
                "query": {
                    "bool": {
                        "should": bigrams_matches,
                        "minimum_should_match": "75%",
                        "must": [{
                            "exists" : { "field" : "2grams" }
                        },{
                            "match":{
                                session:"proposed"
                            }
                        }]
                    }
                }
            }

            docs_with_noise = my_connector.search(query)

            if len(docs_with_noise["hits"]["hits"]) > 1:

                # print("\nMatching: ", bigrams)
                for tweet in docs_with_noise["hits"]["hits"]:

                    #if len(bigrams) == len(tweet["_source"]["2grams"]):
                    #print("...", tweet["_source"]["id_str"])
                    label = [doc for doc in splitted_questions if
                             doc_bigrams["_source"]["id_str"] == doc["str_id"]][0]["label"]
                    duplicated_docs.append({
                        "filename": tweet["_source"]["id_str"],
                        "2grams": tweet["_source"]["2grams"],
                        "label": label
                    })

        return duplicated_docs

    def loop(self, **kwargs):

        # Building the model and getting the questions
        model, X_train, X_test, y_train, y_test, X_unlabeled, categories, scores = self.classifier.build_model(num_questions=kwargs["num_questions"], remove_stopwords=False)

        if (kwargs["sampling_strategy"] == "closer_to_hyperplane"):
            questions = self.classifier.get_samples_closer_to_hyperplane(model, X_train, X_test, y_train, y_test, X_unlabeled, categories, kwargs["num_questions"])
        elif (kwargs["sampling_strategy"] == "closer_to_hyperplane_bigrams_rt"):
            questions = self.classifier.get_samples_closer_to_hyperplane_bigrams_rt(model, X_train, X_test, y_train, y_test,
                                                                               X_unlabeled, categories, kwargs["num_questions"],
                                                                               max_samples_to_sort=kwargs["max_samples_to_sort"],
                                                                               index=kwargs["index"], session=kwargs["session"], text_field=kwargs["text_field"],
                                                                               cnf_weight=kwargs["cnf_weight"], ret_weight=kwargs["ret_weight"], bgr_weight=kwargs["bgr_weight"])

        # Asking the user (gt_dataset) to answer the questions
        answers, wrong_pred_answers = self.get_answers(index=kwargs["index"], questions=questions, gt_session=kwargs["gt_session"], classifier=self.classifier)

        # Injecting the answers in the training set, and re-training the model
        self.classifier.move_answers_to_training_set(answers)
        self.classifier.remove_matching_answers_from_test_set(answers)

        # self training
        duplicated_answers = self.get_duplicated_answers(questions=answers, **kwargs)
        self.classifier.move_answers_to_training_set(duplicated_answers)
        self.classifier.remove_matching_answers_from_test_set(duplicated_answers)

        # Present visualization to the user, so he can explore the proposed classification
        # ...

        return scores, wrong_pred_answers

    def download_data(self, **kwargs):

        if kwargs["download_files"]:
            self.backend_logger.add_raw_log('{ "cleaning_dirs": "' + str(datetime.now()) + '"} \n')
            self.classifier.clean_directories()
            self.backend_logger.add_raw_log('{ "start_downloading": "' + str(datetime.now()) + '"} \n')

            self.classifier.download_training_data(index=kwargs["index"], session=kwargs["session"],
                                              field=kwargs["text_field"], is_field_array=kwargs["is_field_array"],
                                              debug_limit=kwargs["debug_limit"])
            self.classifier.download_unclassified_data(index=kwargs["index"], session=kwargs["session"],
                                                  field=kwargs["text_field"], is_field_array=kwargs["is_field_array"],
                                                  debug_limit=kwargs["debug_limit"])
            self.classifier.download_testing_data(index=kwargs["index"], session=kwargs["gt_session"],
                                             field=kwargs["text_field"], is_field_array=kwargs["is_field_array"],
                                             debug_limit=kwargs["debug_limit"])

    def run(self, **kwargs):

        diff_accuracy = None
        start_time = datetime.now()
        accuracy = 0
        prev_accuracy = 0
        # stage_scores = []

        loop_index = 0
        looping_clicks = 0
        self.backend_logger.clear_logs()  # Just in case there is a file with the same name

        # Copy downloaded files
        self.classifier.clone_original_files()
        self.backend_logger.add_raw_log('{ "start_looping": "' + str(datetime.now()) + '"} \n')

        #while diff_accuracy is None or diff_accuracy > kwargs["min_diff_accuracy"]:
        loop_index = 0
        while loop_index in range(100):  # and accuracy<1:

            print("\n---------------------------------")
            loop_index+=1
            scores, wrong_pred_answers = self.loop(**kwargs)
            looping_clicks += wrong_pred_answers

            # if len(stage_scores) > 0:
            #     accuracy = scores["accuracy"]
            #     prev_accuracy = stage_scores[-1]["accuracy"]
            #     diff_accuracy = abs(accuracy - prev_accuracy)

            self.backend_logger.add_raw_log('{ "loop": ' + str(loop_index) +
                                            ', "datetime": "' + str(datetime.now()) +
                                            '", "accuracy": ' + str(scores["accuracy"]) +
                                            ', "f1": ' + str(scores["f1"]) +
                                            ', "recall": ' + str(scores["recall"]) +
                                            ', "precision": ' + str(scores["precision"]) +
                                            ', "positive_precision": ' + str(scores["positive_precision"]) +
                                            ', "wrong_pred_answers": ' + str(wrong_pred_answers) + ' } \n')
            # stage_scores.append(scores)

        self.backend_logger.add_raw_log('{ "looping_clicks": ' + str(looping_clicks) + '} \n')
        self.backend_logger.add_raw_log('{ "end_looping": "' + str(datetime.now()) + '"} \n')






