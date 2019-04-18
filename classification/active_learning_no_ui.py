from classification.active_learning import ActiveLearning
from datetime import datetime
from mabed.es_connector import Es_connector
from BackendLogger import BackendLogger
import os

class ActiveLearningNoUi:

    def get_answers(self, **kwargs):

        my_connector = Es_connector(index=kwargs["index"])  # , config_relative_path='../')
        wrong_labels=0

        for question in kwargs["questions"]:

            # Adding the label field
            question_id = kwargs["classifier"].extract_filename_no_ext(question["filename"])
            res = my_connector.search({
                "query": {
                    "match": {
                        "id_str": question_id
                    }
                }
            })
            question["label"] = res["hits"]["hits"][0]["_source"][kwargs["gt_session"]]

            if question["pred_label"] != question["label"]:
                wrong_labels += 1

        # print(json.dumps(kwargs["questions"], indent=4, sort_keys=True))
        return kwargs["questions"], wrong_labels

    def loop(self, **kwargs):

        classifier = kwargs["classifier"]

        # Building the model and getting the questions
        model, X_train, X_test, y_train, y_test, X_unlabeled, categories, scores = classifier.build_model(num_questions=kwargs["num_questions"], remove_stopwords=False)

        if (kwargs["sampling_strategy"] == "closer_to_hyperplane"):
            questions = classifier.get_samples_closer_to_hyperplane(model, X_train, X_test, y_train, y_test, X_unlabeled, categories, kwargs["num_questions"])
        elif (kwargs["sampling_strategy"] == "closer_to_hyperplane_bigrams_rt"):
            questions = classifier.get_samples_closer_to_hyperplane_bigrams_rt(model, X_train, X_test, y_train, y_test,
                                                                               X_unlabeled, categories, kwargs["num_questions"],
                                                                               max_samples_to_sort=kwargs["max_samples_to_sort"],
                                                                               index=kwargs["index"], session=kwargs["session"], text_field=kwargs["text_field"],
                                                                               cnf_weight=kwargs["cnf_weight"], ret_weight=kwargs["ret_weight"], bgr_weight=kwargs["bgr_weight"])

        # Asking the user (gt_dataset) to answer the questions
        answers, wrong_pred_answers = self.get_answers(index=kwargs["index"], questions=questions, gt_session=kwargs["gt_session"], classifier=classifier)

        # Injecting the answers in the training set, and re-training the model
        classifier.move_answers_to_training_set(answers)
        classifier.remove_matching_answers_from_test_set(answers)

        # Present visualization to the user, so he can explore the proposed classification
        # ...

        return scores, wrong_pred_answers

    def run(self, **kwargs):

        diff_accuracy = None
        start_time = datetime.now()
        accuracy = 0
        prev_accuracy = 0
        stage_scores = []
        logs_path = os.path.join(os.getcwd(), "classification", "logs", kwargs["logs_filename"])
        backend_logger = BackendLogger(logs_path)
        loop_index = 0
        looping_clicks = 0
        backend_logger.clear_logs()  # Just in case there is a file with the same name
        classifier = ActiveLearning()

        if kwargs["download_files"]:
            backend_logger.add_raw_log('{ "cleaning_dirs": "' + str(datetime.now()) + '"} \n')
            classifier.clean_directories()
            backend_logger.add_raw_log('{ "start_downloading": "' + str(datetime.now()) + '"} \n')
            classifier.download_training_data(index=kwargs["index"], session=kwargs["session"], field=kwargs["text_field"], is_field_array=kwargs["is_field_array"], debug_limit=kwargs["debug_limit"])
            classifier.download_unclassified_data(index=kwargs["index"], session=kwargs["session"], field=kwargs["text_field"], is_field_array=kwargs["is_field_array"], debug_limit=kwargs["debug_limit"])
            classifier.download_testing_data(index=kwargs["index"], session=kwargs["gt_session"], field=kwargs["text_field"], is_field_array=kwargs["is_field_array"], debug_limit=kwargs["debug_limit"])

        backend_logger.add_raw_log('{ "start_looping": "' + str(datetime.now()) + '"} \n')

        while diff_accuracy is None or diff_accuracy > kwargs["min_diff_accuracy"]:

            print("\n---------------------------------")
            loop_index+=1
            #try:
            scores, wrong_pred_answers = self.loop(classifier=classifier, **kwargs)
            looping_clicks += wrong_pred_answers

            if len(stage_scores) > 0:
                accuracy = scores["accuracy"]
                prev_accuracy = stage_scores[-1]["accuracy"]
                diff_accuracy = abs(accuracy - prev_accuracy)

            backend_logger.add_raw_log('{ "loop": ' + str(loop_index) + ', "datetime": "' + str(datetime.now()) + '", "accuracy": ' + str(scores["accuracy"]) + ', "diff_accuracy": "' + str(diff_accuracy) + '", "wrong_pred_answers": ' + str(wrong_pred_answers) + " } \n")
            stage_scores.append(scores)

            # except Exception as e:
            #     backend_logger.add_raw_log('{ "error": ' + str(e) + '} \n')
            #     break

        backend_logger.add_raw_log('{ "looping_clicks": ' + str(looping_clicks) + '} \n')
        backend_logger.add_raw_log('{ "end_looping": "' + str(datetime.now()) + '"} \n')






