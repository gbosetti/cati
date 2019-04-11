from classification.active_learning import ActiveLearning
from datetime import datetime

index="experiment_lyon_2017"
session="session_2017_fdl_test1"
gt_session="lyon2017"
num_questions=10
min_accuracy=90

def get_answers(**kwargs):

    kwargs["questions"]
    kwargs["gt_session"]

    return

def loop(classifier):

    # Building the model
    full_question_samples, confidences, predictions = classifier.build_model(num_questions=num_questions, remove_stopwords=False)

    # Getting the questions and asking the user (gt_dataset) to answer them
    questions = classifier.generating_questions(full_question_samples, predictions, confidences)
    answers = get_answers(questions=questions, gt_session=gt_session)

    # Injecting the answers in the training set, and re-training the model
    classifier.move_answers_to_training_set(answers)
    full_question_samples, confidences, predictions = classifier.build_model(num_questions=num_questions,
                                                                             remove_stopwords=False)

    # Present visualization to the user.
    # Moving the tweets of those quartiles with a high accuracy
    classifier.move_answers_from_accurate_quartiles(answers_above=min_accuracy)

    return accuracy

# ----------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------

print("Process starting at ", datetime.now())

classifier = ActiveLearning()

# Downloading the data from elasticsearch into a folder structure that sklearn can understand
classifier.download_data_into_files(index=index, session=session)

accuracy = 0
while accuracy >= min_accuracy:
    accuracy = loop(classifier)

print("Process finished at ", datetime.now())







