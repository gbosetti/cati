from classification.active_learning import ActiveLearning
from datetime import datetime
from mabed.es_connector import Es_connector
from BackendLogger import BackendLogger
import os
import argparse

# Instantiating the parser
parser = argparse.ArgumentParser(description="CATI's Active Learning module")

# General & mandatory arguments
parser.add_argument("-ss",
                    "--sampling_strategy",
                    dest="sampling_strategy",
                    help="The sampling strategy. It could be 'closer_to_hyperplane' or 'closer_to_hyperplane_bigrams_rt'.")

parser.add_argument("-i",
                    "--index",
                    dest="index",
                    help="The target index to classify")

parser.add_argument("-s",
                    "--session",
                    dest="session",
                    help="The target session to classify")

parser.add_argument("-gts",
                    "--gt_session",
                    dest="gt_session",
                    help="The grountruth session to simulate the user's answer and to measure accuracy")


# Optional arguments
parser.add_argument("-cw",
                    "--cnf_weight",
                    dest="cnf_weight",
                    help="The weight of the position of the tweet according to it's distance to the hyperplane. You need to use this just when you use the closer_to_hyperplane_bigrams_rt strategy.",
                    default=0.5)

parser.add_argument("-rw",
                    "--ret_weight",
                    dest="ret_weight",
                    help="The weight of the position of the tweet according to the ranking of top unlabeled retweets. You need to use this just when you use the closer_to_hyperplane_bigrams_rt strategy.",
                    default=0.4)

parser.add_argument("-bw",
                    "--bgr_weight",
                    dest="bgr_weight",
                    help="The weight of the position of the tweet according to the ranking of top unlabeled bigrams. You need to use this just when you use the closer_to_hyperplane_bigrams_rt strategy.",
                    default=0.1)

parser.add_argument("-mda",
                    "--min_diff_accuracy",
                    dest="min_diff_accuracy",
                    help="The minimum acceptable difference between the accuracy of 2 consecutive loops",
                    default=0.005)

parser.add_argument("-df",
                    "--download_files",
                    dest="download_files",
                    help="Boolean indicating whether new documents should be downloaded to build new training, test and target sets.",
                    default=True)

parser.add_argument("-dl",
                    "--debug_limit",
                    dest="debug_limit",
                    help="Boolean indicating if the download of documents may be limited of not (approx. 500 documents for each category). If False, the full dataset is downloaded.",
                    default=False)

parser.add_argument("-q",
                    "--num_questions",
                    dest="num_questions",
                    help="Integer indicating the number of queries that the user should answer for each loop.",
                    default=20)

parser.add_argument("-tf",
                    "--text_field",
                    dest="text_field",
                    help="The document field that will be processed (used as the content of the tweet when downloading). It's a textal field defined in _source.",
                    default="2grams")





#Params
sampling_strategy = "closer_to_hyperplane_bigrams_rt"  # "closer_to_hyperplane" or "closer_to_hyperplane_bigrams_rt"
min_diff_accuracy = 0.005
download_files=True
debug_limit=True
index="experiment_lyon_2017"
session="session_lyon2017_test_01"
gt_session="session_lyon2017"
num_questions=20
text_field="2grams"
cnf_weight = 0.5
ret_weight = 0.4
bgr_weight = 0.1

# ----------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------

def get_answers(**kwargs):

    my_connector = Es_connector(index=kwargs["index"], config_relative_path='../')
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

def loop(**kwargs):

    classifier = kwargs["classifier"]

    # Building the model and getting the questions
    model, X_train, X_test, y_train, y_test, X_unlabeled, categories, scores = classifier.build_model(num_questions=kwargs["num_questions"], remove_stopwords=False)

    if (kwargs["sampling_strategy"] == "closer_to_hyperplane"):
        questions = classifier.get_samples_closer_to_hyperplane(model, X_train, X_test, y_train, y_test, X_unlabeled, categories, num_questions)
    elif (kwargs["sampling_strategy"] == "closer_to_hyperplane_bigrams_rt"):
        questions = classifier.get_samples_closer_to_hyperplane_bigrams_rt(model, X_train, X_test, y_train, y_test,
                                                                           X_unlabeled, categories, num_questions,
                                                                           max_samples_to_sort=kwargs["max_samples_to_sort"],
                                                                           index=index, session=session, text_field=kwargs["text_field"],
                                                                           cnf_weight=cnf_weight, ret_weight=ret_weight, bgr_weight=bgr_weight)

    # Asking the user (gt_dataset) to answer the questions
    answers, wrong_pred_answers = get_answers(index=kwargs["index"], questions=questions, gt_session=kwargs["gt_session"], classifier=classifier)

    # Injecting the answers in the training set, and re-training the model
    classifier.move_answers_to_training_set(answers)
    classifier.remove_matching_answers_from_test_set(answers)

    # Present visualization to the user, so he can explore the proposed classification
    # ...

    return scores, wrong_pred_answers

# ----------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------

# Variables
classifier = ActiveLearning()
diff_accuracy = None
start_time = datetime.now()
accuracy = 0
prev_accuracy = 0
stage_scores = []
logs_filename = session + "_" + sampling_strategy + "_logs.txt"
logs_path = os.path.join(os.getcwd(), "logs", logs_filename)
backend_logger = BackendLogger(logs_path)
loop_index = 0
looping_clicks = 0

# Downloading the data from elasticsearch into a folder structure that sklearn can understand
backend_logger.clear_logs() #Just in case there is a file with the same name
#.delete_folder_contents(os.path.join(os.getcwd(), "images"))

if download_files:
    backend_logger.add_raw_log('{ "cleaning_dirs": "' + str(datetime.now()) + '"} \n')
    classifier.clean_directories()
    backend_logger.add_raw_log('{ "start_downloading": "' + str(datetime.now()) + '"} \n')
    classifier.download_training_data(index=index, session=session, field=text_field, is_field_array=True, debug_limit=debug_limit)
    classifier.download_unclassified_data(index=index, session=session, field=text_field, is_field_array=True, debug_limit=debug_limit)
    classifier.download_testing_data(index=index, session=gt_session, field=text_field, is_field_array=True, debug_limit=debug_limit)

backend_logger.add_raw_log('{ "start_looping": "' + str(datetime.now()) + '"} \n')

while diff_accuracy is None or diff_accuracy > min_diff_accuracy:

    print("\n---------------------------------")
    loop_index+=1
    try:
        scores, wrong_pred_answers = loop(sampling_strategy=sampling_strategy, classifier=classifier, index=index, gt_session=gt_session, num_questions=num_questions, text_field=text_field, max_samples_to_sort=500)
        looping_clicks += wrong_pred_answers

        if len(stage_scores) > 0:
            accuracy = scores["accuracy"]
            prev_accuracy = stage_scores[-1]["accuracy"]
            diff_accuracy = abs(accuracy - prev_accuracy)

        backend_logger.add_raw_log('{ "loop": ' + str(loop_index) + ', "datetime": "' + str(datetime.now()) + '", "accuracy": ' + str(scores["accuracy"]) + ', "diff_accuracy": "' + str(diff_accuracy) + '", "wrong_pred_answers": ' + str(wrong_pred_answers) + " } \n")
        stage_scores.append(scores)

    except Exception as e:
        backend_logger.add_raw_log('{ "error": ' + str(e) + '} \n')
        break

backend_logger.add_raw_log('{ "looping_clicks": ' + str(looping_clicks) + '} \n')
backend_logger.add_raw_log('{ "end_looping": "' + str(datetime.now()) + '"} \n')






