from classification.active_learning_no_ui import ActiveLearningNoUi
from classification.samplers import *
import argparse
import itertools
import os
import shutil
import json

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
                    dest="session")

parser.add_argument("-gts",
                    "--gt_session",
                    dest="gt_session",
                    help="The grountruth session to simulate the user's answer and to measure accuracy. E.g. session_lyon_2017")


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

parser.add_argument("-ml",
                    "--max_loops",
                    dest="max_loops",
                    help="The max amount of loops to perform",
                    default=100)

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
                    default="text")

parser.add_argument("-smss",
                    "--selected_max_samples_to_sort",
                    dest="selected_max_samples_to_sort",
                    help="The list of max number of sorted documents (according to their distance to the hyperplane) to score, as well as the maximum number of retweets and bigrams to consider for the scoring. E.g. [100, 500]",
                    default=[100])

parser.add_argument("-cr",
                    "--clear_results",
                    dest="clear_results",
                    help="Do you want to clear all folders with the generated results?",
                    default=True)

parser.add_argument("-sc",
                    "--selected_combinations",
                    dest="selected_combinations",
                    help="The combinations of weights that you want to use. Write it as a string. E.g. '[[0.9, 0.0, 0.1], [0.9, 0.1, 0.0]]' If it is not set, all the permutations of the multiples of 0.1 from 0 to 1 are used instead.",
                    default=None)

parser.add_argument("-sm",
                    "--sampling_methods",
                    dest="sampling_methods",
                    help="The list of the sampling method classes to test. E.g. UncertaintySampler, BigramsRetweetsSampler, MoveDuplicatedDocsSampler",
                    default="UncertaintySampler")

parser.add_argument("-jp",
                    "--jackard_percentages",
                    dest="jackard_percentages",
                    help="The list of the percentage of similarity to search for similar documents",
                    default="0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9")

parser.add_argument("-sp",
                    "--similarity_percentages",
                    dest="similarity_percentages",
                    help="A number followed by the % symbol. XX%. If you specify different percentages separate them with comma (not spaces)",
                    default="75%")

parser.add_argument("-cl",
                    "--confident_loops",
                    dest="confident_loops",
                    help="A number indicating at which amount of loops a similar document should be considered confident to move. If you specify different percentages separate them with comma (not spaces)",
                    default="2")

parser.add_argument("-tmc",
                    "--target_min_confidence",
                    dest="target_min_confidence",
                    help="A number between 0 and 1 indicating the minimum confidence on the predicted label to consider adding a document into the duplicated docs collection",
                    default="0.35")


def to_boolean(str_param):
    if isinstance(str_param, bool):
        return str_param
    elif str_param.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    else:
        return False

args = parser.parse_args()

if args.index is None or args.session is None or args.gt_session is None:
    raise Exception('You are missing some required params')

download_files = to_boolean(args.download_files)
debug_limit = to_boolean(args.debug_limit)
clear_results = to_boolean(args.clear_results)
sampling_methods = args.sampling_methods.split(',')
similarity_percentages = args.similarity_percentages.split(',')
confident_loops = args.confident_loops.split(',')
target_min_confidence = float(args.target_min_confidence)
max_loops = int(args.max_loops)

# Different configurations to run the algorythm.
# The weight of the position of the tweet according to it's distance to the hyperplane, or the position of the top-bigram/top-retweet it contains (if any).
# It is mandatory just when you use the closer_to_hyperplane_bigrams_rt strategy.
# ----------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------

if args.selected_combinations is None:
    # all_percentages = [round(x * 0.1,2) for x in range(0, 11)]  # [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    # all_combinations = list(itertools.permutations(all_percentages, 3))  # not combinations_with_replacement
    # [round(x * 0.2,1) for x in range(0, 6)]
    all_percentages = [round(x * 0.2,1) for x in range(0, 6)]
    all_combinations = list(itertools.combinations_with_replacement(all_percentages, 3))
    combinations= [x for x in all_combinations if x[0] + x[1] + x[2] == 1 or x[0] + x[1] + x[2] == 1.0]

    selected_combinations = []
    for comb in combinations:
        selected_combinations.extend(set(list(itertools.permutations(comb))))
    selected_combinations = sorted(set(selected_combinations))
else:
    selected_combinations = json.loads(args.selected_combinations)


# Running the algorythm with all the configurations
# ----------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------

# Deleting previous results
def delete_folder(path):
    if os.path.exists(path):
        #os.remove(path)
        print("Deleting folder: ", path)
        shutil.rmtree(path)

if clear_results:
    delete_folder(os.path.join(os.getcwd(), "classification", "logs"))
    delete_folder(os.path.join(os.getcwd(), "classification", "images"))
    delete_folder(os.path.join(os.getcwd(), "classification", "tmp_data"))
    delete_folder(os.path.join(os.getcwd(), "classification", "original_tmp_data"))

if download_files:
    print("Downloading files from session ", args.session, " and ", args.gt_session)
    learner = ActiveLearningNoUi(logs_filename="download.txt")
    learner.download_data(index=args.index, session=args.session,
                    gt_session=args.gt_session, download_files=download_files, debug_limit=debug_limit,
                    text_field=args.text_field)
    learner.clean_logs()

#  Running the algorythm multiple times
for max_samples_to_sort in args.selected_max_samples_to_sort:

    # First, closer_to_hyperplane (the sampling sorting by distance to the hyperplane)
    if 'UncertaintySampler' in sampling_methods:

        print("\nRunning hyperplane strategy\n")
        logs_filename = args.session + "_HYP" + "_smss" + str(max_samples_to_sort) + ".txt"
        sampler = UncertaintySampler()
        learner = ActiveLearningNoUi(logs_filename=logs_filename, sampler=sampler)
        learner.run(index=args.index, session=args.session, gt_session=args.gt_session,
                    min_diff_accuracy=args.min_diff_accuracy, num_questions=args.num_questions,
                    text_field=args.text_field, max_loops=max_loops)

    if 'JackardBasedUncertaintySampler' in sampling_methods:

        # jackard_percentages = all_percentages.copy()
        # jackard_percentages.remove(0)
        # jackard_percentages.remove(1)
        jackard_percentages = args.jackard_percentages.split(',')

        for confidence_limit in jackard_percentages:

            try:
                logs_filename = args.session + "_jackard" + "_cnf" + str(confidence_limit) + ".txt"
                sampler = JackardBasedUncertaintySampler(low_confidence_limit=confidence_limit, index=args.index, session=args.session,
                    text_field=args.text_field, similarity_percentage=100)

                learner = ActiveLearningNoUi(logs_filename=logs_filename, sampler=sampler)
                learner.run(index=args.index, session=args.session, gt_session=args.gt_session,
                            min_diff_accuracy=args.min_diff_accuracy, num_questions=args.num_questions,
                            text_field=args.text_field, max_loops=max_loops)
            except Exception as e:
                print(e)
                learner.backend_logger.add_raw_log('{ "error": "' + str(e) + '"} \n')

    # Then, closer_to_hyperplane_bigrams_rt with all the possibilities of weights (summing 1)
    if 'BigramsRetweetsSampler' in sampling_methods:
        for weights in selected_combinations:

            print("Looping with weights: ", weights)
            logs_filename = args.session + "_OUR" + \
                            "_cnf" + str(weights[0]) + "_ret" + str(weights[1]) + "_bgr" + str(weights[2]) +\
                            "_smss" + str(max_samples_to_sort) + ".txt"
            sampler = BigramsRetweetsSampler(max_samples_to_sort=max_samples_to_sort, index=args.index, session=args.session,
                text_field=args.text_field, cnf_weight=weights[0], ret_weight=weights[1], bgr_weight=weights[2])
            learner = ActiveLearningNoUi(logs_filename=logs_filename, sampler=sampler)

            learner.run(index=args.index, session=args.session, num_questions=args.num_questions,
                        gt_session=args.gt_session, min_diff_accuracy=args.min_diff_accuracy,
                        text_field=args.text_field, max_loops=max_loops)

    if 'MoveDuplicatedDocsSampler' in sampling_methods:

        print("\nRunning the MoveDuplicatedDocsSampler strategy\n")

        for similarity_percentage in similarity_percentages:

            print("Looping with percentages: ", similarity_percentage)
            logs_filename = args.session + "_DDS" + "_smss" + str(max_samples_to_sort) + ".txt"
            sampler = MoveDuplicatedDocsSampler(index=args.index, session=args.session,
                    text_field=args.text_field, similarity_percentage=similarity_percentage)
            learner = ActiveLearningNoUi(logs_filename=logs_filename, sampler=sampler)
            learner.run(index=args.index, session=args.session, gt_session=args.gt_session,
                        min_diff_accuracy=args.min_diff_accuracy, num_questions=args.num_questions,
                        text_field=args.text_field, max_loops=max_loops)

    if 'ConsecutiveDeferredMovDuplicatedDocsSampler' in sampling_methods:

        print("\nRunning the ConsecutiveDeferredMovDuplicatedDocsSampler strategy\n")

        for similarity_percentage in similarity_percentages:
            for confident_loop in confident_loops:

                confident_loop = int(confident_loop)

                print("Looping with percentages: ", similarity_percentage)
                logs_filename = args.session + "_DDS" + "_loops_" + str("%02d" % (confident_loop,)) + "_smss" + str(max_samples_to_sort) + ".txt"
                sampler = ConsecutiveDeferredMovDuplicatedDocsSampler(index=args.index, session=args.session,
                        text_field=args.text_field, similarity_percentage=similarity_percentage,
                        confident_loop=confident_loop, target_min_confidence=target_min_confidence)
                learner = ActiveLearningNoUi(logs_filename=logs_filename, sampler=sampler)
                learner.run(index=args.index, session=args.session, gt_session=args.gt_session,
                            min_diff_accuracy=args.min_diff_accuracy, num_questions=args.num_questions,
                            text_field=args.text_field, max_loops=max_loops)
