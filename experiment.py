from classification.active_learning_no_ui import ActiveLearningNoUi
import argparse
import itertools
import os
import shutil

# PARAMS
# ----------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------

# Instantiating the parser
parser = argparse.ArgumentParser(description="CATI's Active Learning module")

# General & mandatory arguments (with a default value so we can run it also through the PyCharm's UI

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

parser.add_argument("-tfa",
                    "--is_field_array",
                    dest="is_field_array",
                    help="Is the document field a String or an array of strings?",
                    default=True)

parser.add_argument("-smss",
                    "--selected_max_samples_to_sort",
                    dest="selected_max_samples_to_sort",
                    help="The list of max number of sorted documents (according to their distance to the hyperplane) to score, as well as the maximum number of retweets and bigrams to consider for the scoring. E.g. [100, 500]",
                    default=[500])

parser.add_argument("-cr",
                    "--clear_results",
                    dest="clear_results",
                    help="Do you want to clear all folders with the generated results?",
                    default=True)

args = parser.parse_args()

if args.index is None or args.session is None or args.gt_session is None:
    raise Exception('You are missing some required params')




# Different configurations to run the algorythm.
# The weight of the position of the tweet according to it's distance to the hyperplane, or the position of the top-bigram/top-retweet it contains (if any).
# It is mandatory just when you use the closer_to_hyperplane_bigrams_rt strategy.
# ----------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------
all_percentages = [round(x * 0.1,2) for x in range(0, 11)]  # [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
all_combinations = list(itertools.permutations(all_percentages, 3))  # not combinations_with_replacement
selected_combinations = [x for x in all_combinations if x[0] + x[1] + x[2] == 1 or x[0] + x[1] + x[2] == 1.0]


# Running the algorythm with all the configurations
# ----------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------

# Deleting previous results
def delete_folder(path):
    if os.path.exists(path):
        #os.remove(path)
        shutil.rmtree(path)

if args.clear_results:
    delete_folder(os.path.join(os.getcwd(), "classification", "logs"))
    delete_folder(os.path.join(os.getcwd(), "classification", "images"))
    delete_folder(os.path.join(os.getcwd(), "classification", "tmp_data"))

# Running the algorythm multiple times
for max_samples_to_sort in args.selected_max_samples_to_sort:

    # First, closer_to_hyperplane (the sampling sorting by distance to the hyperplane)
    learner = ActiveLearningNoUi()
    logs_filename = args.gt_session + "_HYP_" + str(max_samples_to_sort) + "_mda" + str(args.min_diff_accuracy) + "_smss" + str(args.selected_max_samples_to_sort) + ".txt"
    learner.run(sampling_strategy="closer_to_hyperplane", index=args.index, session=args.session,
                gt_session=args.gt_session, min_diff_accuracy=args.min_diff_accuracy, logs_filename=logs_filename,
                download_files=args.download_files, debug_limit=args.debug_limit, num_questions=args.num_questions,
                text_field=args.text_field, is_field_array=args.is_field_array, max_samples_to_sort=max_samples_to_sort)

    # Then, closer_to_hyperplane_bigrams_rt with all the possibilities of weights (summing 1)
    for weights in selected_combinations:

        learner = ActiveLearningNoUi()
        logs_filename = args.gt_session + "_OUR_" + str(max_samples_to_sort) + "_" + \
                        "_cnf" + str(weights[0]) + "_ret" + str(weights[1]) + "_bgr" + str(weights[2]) +\
                        "_mda" + str(args.min_diff_accuracy) + "_smss" + str(args.selected_max_samples_to_sort) + ".txt"

        learner.run(sampling_strategy="closer_to_hyperplane_bigrams_rt", index=args.index, session=args.session,
                    gt_session=args.gt_session, cnf_weight=weights[0], ret_weight=weights[1], bgr_weight=weights[2],
                    min_diff_accuracy=args.min_diff_accuracy, logs_filename=logs_filename,
                    download_files=args.download_files, debug_limit=args.debug_limit, num_questions=args.num_questions,
                    text_field=args.text_field, is_field_array=args.is_field_array, max_samples_to_sort=max_samples_to_sort)



