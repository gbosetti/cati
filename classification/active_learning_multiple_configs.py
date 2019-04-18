from classification.active_learning_no_ui import ActiveLearningNoUi
import argparse

# PARAMS
# ----------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------

# Instantiating the parser
parser = argparse.ArgumentParser(description="CATI's Active Learning module")

# General & mandatory arguments (with a default value so we can run it also through the PyCharm's UI
parser.add_argument("-ss",
                    "--sampling_strategy",
                    dest="sampling_strategy",
                    help="The sampling strategy. It could be 'closer_to_hyperplane' or 'closer_to_hyperplane_bigrams_rt'.",
                    default="closer_to_hyperplane_bigrams_rt")

parser.add_argument("-i",
                    "--index",
                    dest="index",
                    help="The target index to classify",
                    default="experiment_lyon_2017")

parser.add_argument("-s",
                    "--session",
                    dest="session",
                    help="The target session to classify",
                    default="session_lyon2017_test_01")

parser.add_argument("-gts",
                    "--gt_session",
                    dest="gt_session",
                    help="The grountruth session to simulate the user's answer and to measure accuracy",
                    default="session_lyon2017")


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
                    default=True)

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

parser.add_argument("-mss",
                    "--max_samples_to_sort",
                    dest="max_samples_to_sort",
                    help="The max number of sorted documents (according to their distance to the hyperplane) to score, as well as the maximum number of retweets and bigrams to consider for the scoring.",
                    default=500)

args = parser.parse_args()



# Running the algorythm with different configurations
# ----------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------

learner = ActiveLearningNoUi()
# learner.delete_full_image_folder_contents()
learner.run(sampling_strategy=args.sampling_strategy, index=args.index, session=args.session, gt_session=args.gt_session,
            cnf_weight=args.cnf_weight, ret_weight=args.ret_weight, bgr_weight=args.bgr_weight, min_diff_accuracy=args.min_diff_accuracy,
            download_files=args.download_files, debug_limit=args.debug_limit, num_questions=args.num_questions,
            text_field=args.text_field, is_field_array=args.is_field_array, max_samples_to_sort=args.max_samples_to_sort)

