from classification.active_learning import ActiveLearning
from datetime import datetime
from mabed.es_connector import Es_connector
import json
import ast

index="experiment_lyon_2017"
session="session_lyon2017_test_01"
gt_session="session_lyon2017"
num_questions=20
min_acceptable_accuracy=0.9
min_diff_accuracy=0.02
text_field="2grams"

#min_high_confidence=0.75

def get_answers(**kwargs):

    my_connector = Es_connector(index=kwargs["index"], config_relative_path='../')
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

    # print(json.dumps(kwargs["questions"], indent=4, sort_keys=True))
    return kwargs["questions"]

def loop(**kwargs):

    classifier = kwargs["classifier"]

    # Building the model and getting the questions
    model, X_train, X_test, y_train, y_test, X_unlabeled, categories, scores = classifier.build_model(num_questions=kwargs["num_questions"], remove_stopwords=False)

    #classifier.get_samples_closer_to_hyperplane(clf, X_train, X_test, y_train, y_test, X_unlabeled, categories, num_questions)
    questions = classifier.get_samples_closer_to_hyperplane_bigrams_rt(model, X_train, X_test, y_train, y_test, X_unlabeled, categories, num_questions, max_samples_to_sort=kwargs["max_samples_to_sort"], index=index, session=session, text_field=kwargs["text_field"])

    # Asking the user (gt_dataset) to answer the questions
    answers = get_answers(index=kwargs["index"], questions=questions, gt_session=kwargs["gt_session"], classifier=classifier)

    # Injecting the answers in the training set, and re-training the model
    classifier.move_answers_to_training_set(answers)
    #classifier.remove_matching_answers_from_test_set(answers)

    # Present visualization to the user, so he can explore the proposed classification
    # ...
    # Moving the tweets of those quartiles with a high accuracy
    # classifier.classify_accurate_quartiles(min_acceptable_accuracy=min_acceptable_accuracy, min_high_confidence=min_high_confidence)

    return scores

# ----------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------

print("Process starting at ", datetime.now())

classifier = ActiveLearning()

# Downloading the data from elasticsearch into a folder structure that sklearn can understand
download_files=False
if download_files:
    debug_limit=True
    classifier.clean_directories()
    classifier.download_training_data(index=index, session=session, field=text_field, is_field_array=True, debug_limit=debug_limit)
    classifier.download_unclassified_data(index=index, session=session, field=text_field, is_field_array=True, debug_limit=debug_limit)
    classifier.download_testing_data(index=index, session=gt_session, field=text_field, is_field_array=True, debug_limit=debug_limit)

diff_accuracy = 0
accuracy = 0
prev_accuracy = 0
stage_scores = []

while accuracy < min_acceptable_accuracy:  # and diff_accuracy>min_diff_accuracy:

    print("\n---------------------------------")
    scores = loop(classifier=classifier, index=index, gt_session=gt_session, num_questions=num_questions, text_field=text_field, max_samples_to_sort=500)

    if len(stage_scores) > 0:
        accuracy = scores["accuracy"]
        prev_accuracy = stage_scores[-1]["accuracy"]
        diff_accuracy = abs(accuracy - prev_accuracy)

    print("\naccuracy: ", scores["accuracy"], " diff_accuracy: ", diff_accuracy)
    stage_scores.append(scores)

print("Process finished at ", datetime.now())







