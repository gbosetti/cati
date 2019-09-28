from classification.active_learning import ActiveLearning
from datetime import datetime
from mabed.es_connector import Es_connector
from BackendLogger import BackendLogger
import os
import time

class ActiveLearningNoUi:

    def __init__(self, **kwargs):

        logs_path = os.path.join(os.getcwd(), "classification", "logs", kwargs["logs_filename"])
        folder = os.path.dirname(logs_path)
        if not os.path.exists(folder):
            os.makedirs(folder)
        self.backend_logger = BackendLogger(logs_path)

        self.classifier = ActiveLearning()

        if kwargs.get("sampler", None) != None:
            self.classifier.set_sampling_strategy(kwargs["sampler"])

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

    def loop(self, **kwargs):

        # Building the model and getting the questions
        self.classifier.build_model(remove_stopwords=False)  # From the UI it is required to use the build_model_no_test instead
        questions = self.classifier.get_samples(kwargs["num_questions"])

        if len(questions)>0:

            # Asking the user (gt_dataset) to answer the questions
            answers, wrong_pred_answers = self.get_answers(index=kwargs["index"], questions=questions, gt_session=kwargs["gt_session"], classifier=self.classifier)

            # Injecting the answers in the training set, and re-training the model
            self.classifier.move_answers_to_training_set(answers)
            self.classifier.post_sampling(answers=answers) #In case you want, e.g., to move duplicated content

            return self.classifier.scores, wrong_pred_answers

        else: raise Exception('ERROR: the number of low-level-confidence predictions is not enough to retrieve any sample question.')

    def download_data(self, **kwargs):

        if kwargs["download_files"]:
            self.backend_logger.add_raw_log('{ "cleaning_dirs": "' + str(datetime.now()) + '"} \n')
            self.classifier.clean_directories()
            self.backend_logger.add_raw_log('{ "start_downloading": "' + str(datetime.now()) + '"} \n')

            self.classifier.download_training_data(index=kwargs["index"], session=kwargs["session"],
                                              field=kwargs["text_field"],
                                              debug_limit=kwargs["debug_limit"])
            self.classifier.download_unclassified_data(index=kwargs["index"], session=kwargs["session"],
                                                  field=kwargs["text_field"],
                                                  debug_limit=kwargs["debug_limit"])
            self.classifier.download_testing_data(index=kwargs["index"], session=kwargs["gt_session"],
                                             field=kwargs["text_field"],
                                             debug_limit=kwargs["debug_limit"])
            self.classifier.remove_docs_absent_in_training()

    def clear_temporary_labels(self, index, session):

        Es_connector(index=index).update_by_query({
            "query": {
                "exists" : { "field" : session + "_tmp" }  # e.g. session_lyon2015_test_01_tmp
            }
        }, "ctx._source.remove('" + session + "_tmp')")

    def split_list(self, alist, wanted_parts=1):
        length = len(alist)
        return [alist[i * length // wanted_parts: (i + 1) * length // wanted_parts]
                for i in range(wanted_parts)]

    def delete_temporary_labels(self, index, session, docs):

        matching_ids = set()
        for doc in docs:
            doc_id = os.path.basename(doc["filename"]).split(".")[0]
            matching_ids.add(doc_id)

        parts = len(matching_ids) / 1000
        if int(parts) != parts:
            parts = int(parts) + 1
        else:
            parts = int(parts)

        paginated_ids = self.split_list(list(matching_ids), parts)

        print("Deleting temp vars")

        for page_ids in paginated_ids:

            matching_ids = []
            for doc_id in page_ids:
                matching_ids.append({"match": {"id_str": doc_id}})

            try:
                query = {
                    "query": {
                        "bool": {
                            "should": matching_ids,
                            "minimum_should_match": 1
                        }
                    }
                }
                Es_connector(index=index).update_by_query(query, "ctx._source.remove('" + session + "_tmp')")
                #time.sleep(1)
            except Exception as e:
                print(e)
        #     self.backend_logger.add_raw_log('{ "error": "' + str(e) + '"} \n')
        #     return [],[]

    def add_temporary_labels(self, index, session, duplicated_ids):

        parts = len(duplicated_ids)/1000
        if int(parts) != parts:
            parts = int(parts) + 1
        else: parts = int(parts)

        paginated_ids = self.split_list(duplicated_ids, parts)

        for page_ids in paginated_ids:

            matching_ids = []
            for id in page_ids:
                matching_ids.append({"match": {"id_str": id}})

            Es_connector(index=index).update_by_query({
                "query": {
                  "bool": {
                    "should": matching_ids,
                    "minimum_should_match": 1
                  }
                }
            }, "ctx._source." + session + "_tmp = 'unlabeled'")

    def run(self, **kwargs):

        self.backend_logger.clear_logs()  # Just in case there is a file with the same name
        # Copy downloaded files
        self.classifier.clone_original_files()
        self.backend_logger.add_raw_log('{ "start_looping": "' + str(datetime.now()) + '"} \n')

        loop_index = 0
        looping_clicks = 0
        while loop_index in range(kwargs["max_loops"]):  # and accuracy<1:  /// max_loops default is 100

            print("\n---------------------------------")
            loop_index+=1
            self.classifier.loop_index = loop_index
            scores, wrong_pred_answers = self.loop(**kwargs)
            looping_clicks += wrong_pred_answers

            self.backend_logger.add_raw_log('{ "loop": ' + str(loop_index) +
                                            ', "datetime": "' + str(datetime.now()) +
                                            '", "accuracy": ' + str(scores["accuracy"]) +
                                            ', "f1": ' + str(scores["f1"]) +
                                            ', "recall": ' + str(scores["recall"]) +
                                            ', "precision": ' + str(scores["precision"]) +
                                            ', "positive_precision": ' + str(scores["positive_precision"]) +
                                            ', "wrong_pred_answers": ' + str(wrong_pred_answers) + ' } \n')

        self.backend_logger.add_raw_log('{ "looping_clicks": ' + str(looping_clicks) + '} \n')
        self.backend_logger.add_raw_log('{ "end_looping": "' + str(datetime.now()) + '"} \n')
