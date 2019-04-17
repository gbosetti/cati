from classification.active_learning import ActiveLearning
from datetime import datetime
from mabed.es_connector import Es_connector
from BackendLogger import BackendLogger
import json
import ast
import plotly.plotly as py
import plotly.graph_objs as go
import plotly.io as pio
import os

index="experiment_lyon_2017"
session="session_lyon2017_test_01"
gt_session="session_lyon2017"
num_questions=20
min_diff_accuracy=0.02
text_field="2grams"

#min_high_confidence=0.75

def draw_accuracy_scatterplot(logs):

    x_axis = [log["loop"] for log in logs if 'loop' in log]   # datetime
    y_axis = [log["accuracy"] for log in logs if 'loop' in log]

    fig = go.Figure()
    fig.add_scatter(x=x_axis,
                    y=y_axis,
                    mode='markers');

    if not os.path.exists('images'):
        os.mkdir('images')

    pio.write_image(fig, 'images/fig1.png')


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
        questions = classifier.get_samples_closer_to_hyperplane_bigrams_rt(model, X_train, X_test, y_train, y_test, X_unlabeled, categories, num_questions, max_samples_to_sort=kwargs["max_samples_to_sort"], index=index, session=session, text_field=kwargs["text_field"])

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



classifier = ActiveLearning()
diff_accuracy = None
start_time = datetime.now()
accuracy = 0
prev_accuracy = 0
stage_scores = []
backend_logger = BackendLogger("active_learning-logs.txt")
backend_logger.clear_logs() #Just in case there is a file with the same name
loop_index = 0
looping_clicks = 0



# Downloading the data from elasticsearch into a folder structure that sklearn can understand
download_files=True
if download_files:
    debug_limit=True
    backend_logger.add_raw_log('{ "cleaning_dirs": "' + str(datetime.now()) + '"} \n')
    classifier.clean_directories()
    backend_logger.add_raw_log('{ "start_downloading": "' + str(datetime.now()) + '"} \n')
    classifier.download_training_data(index=index, session=session, field=text_field, is_field_array=True, debug_limit=debug_limit)
    classifier.download_unclassified_data(index=index, session=session, field=text_field, is_field_array=True, debug_limit=debug_limit)
    classifier.download_testing_data(index=index, session=gt_session, field=text_field, is_field_array=True, debug_limit=debug_limit)

backend_logger.add_raw_log('{ "start_looping": "' + str(datetime.now()) + '"} \n')

while diff_accuracy is None or diff_accuracy > 0.005:

    print("\n---------------------------------")
    loop_index+=1
    # sampling_strategy = "closer_to_hyperplane" or "closer_to_hyperplane_bigrams_rt"
    try:
        scores, wrong_pred_answers = loop(sampling_strategy="closer_to_hyperplane_bigrams_rt", classifier=classifier, index=index, gt_session=gt_session, num_questions=num_questions, text_field=text_field, max_samples_to_sort=500)
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

logs = json.loads(backend_logger.get_logs().replace('\n', ','))
loop_logs = [log for log in logs if 'loop' in log]
draw_accuracy_scatterplot(loop_logs)

print("\n\n", loop_logs)




