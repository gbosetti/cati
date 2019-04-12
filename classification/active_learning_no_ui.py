from classification.active_learning import ActiveLearning
from datetime import datetime
from mabed.es_connector import Es_connector

index="experiment_lyon_2017"
session="session_lyon2017_test_01"
gt_session="session_lyon2017"
num_questions=10
min_accuracy=90

def get_answers(**kwargs):

    for question in kwargs["questions"]:

        print(question)
        # {'filename': 'C:\\Users\\gbosetti\\Desktop\\mabed\\classification\\classification\\unlabeled\\proposed\\941072171815854080.txt', 'text': '@brianmurphycllr-mostmost-christmaschristmas-marketsmarkets-aroundaround-europeeurope-surroundedsurrounded-anti-jihadanti-jihad-bollardsbollards-guardedguarded-heavilyheavily-armed', 'pred_label': 0, 'data_unlabeled_index': 296, 'confidence': 0.26007260204898874}
        #kwargs["gt_session"]

    my_connector = Es_connector(index=kwargs["index"], config_relative_path='../')

    return

def loop(**kwargs):

    classifier = kwargs["classifier"]

    # Building the model
    full_question_samples, confidences, predictions, scores = classifier.build_model(num_questions=num_questions, remove_stopwords=False, sampling_method="closer_to_hyperplane")

    # Getting the questions and asking the user (gt_dataset) to answer them
    questions = classifier.generating_questions(full_question_samples, predictions, confidences)
    answers = get_answers(index=kwargs["index"], questions=questions, gt_session=kwargs["gt_session"])

    # Injecting the answers in the training set, and re-training the model
    classifier.move_answers_to_training_set(answers)

    # Present visualization to the user.
    # Moving the tweets of those quartiles with a high accuracy
    classifier.move_answers_from_accurate_quartiles(answers_above=min_accuracy)

    return scores

# ----------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------

print("Process starting at ", datetime.now())

classifier = ActiveLearning()

# Downloading the data from elasticsearch into a folder structure that sklearn can understand
# classifier.download_data_into_files(index=index, session=session, field="2grams", is_field_array=True)  # field may be text, 2grams or anything else at the same level of the elastic doc

accuracy = 0
while accuracy < min_accuracy:
    scores = loop(classifier=classifier, index=index, gt_session=gt_session)
    accuracy = scores.accuracy

print("Process finished at ", datetime.now())







