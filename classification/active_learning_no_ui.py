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
sampling_method = "closer_to_hyperplane"

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
    questions, confidences, predictions, scores = classifier.build_model(num_questions=kwargs["num_questions"], remove_stopwords=False, sampling_method=kwargs["sampling_method"])

    # Asking the user (gt_dataset) to answer the questions
    answers = get_answers(index=kwargs["index"], questions=questions, gt_session=kwargs["gt_session"], classifier=classifier)

    # Injecting the answers in the training set, and re-training the model
    classifier.move_answers_to_training_set(answers)
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
classifier.download_training_data(index=index, session=session, field="2grams", is_field_array=True)  # field may be text, 2grams or anything else at the same level of the elastic doc

diff_accuracy = 0
accuracy = 0
stage_scores = []

while accuracy < min_acceptable_accuracy:  # and diff_accuracy>min_diff_accuracy:

    scores = loop(classifier=classifier, index=index, gt_session=gt_session, num_questions=num_questions, sampling_method=sampling_method)

    if len(stage_scores) > 1:
        accuracy = scores["accuracy"]
        prev_accuracy = stage_scores[-1]["accuracy"]
        diff_accuracy = abs(accuracy - prev_accuracy)

        print("\n---------------------------------\naccuracy: ", accuracy, " prev_accuracy: ", prev_accuracy, " diff_accuracy: ", diff_accuracy)

    stage_scores.append(scores)

print("Process finished at ", datetime.now())







