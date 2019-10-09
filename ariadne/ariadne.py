from classification.active_learning_no_ui import ActiveLearningNoUi
import classification.samplers as samplers_module
import classification.learners as learners_module
import classification.vectorizers as vectorizers_module
import json
import os
import shutil
from mabed.es_connector import Es_connector
import elasticsearch

class Ariadne:

    def __init__(self, samplers, learners, vectorizers):

        self.all_samplers = self.module_to_dict(samplers)
        self.all_vectorizers = self.module_to_dict(vectorizers)
        self.all_learners = self.module_to_dict(learners)

        self.target_samplers = []
        self.target_vectorizers = []
        self.target_learners = []

    def module_to_dict(self, module):
        return {key: getattr(module, key) for key in dir(module)}

    def to_boolean(self, str_param):
        if isinstance(str_param, bool):
            return str_param
        elif str_param.lower() in ('yes', 'true', 't', 'y', '1'):
            return True
        else:
            return False

    def get_script_params(self):

        config = self.read_config_file()

        for index, learner in enumerate(config["learners"]):
            config["learners"][index] = self.all_learners[learner]

        for index, vectorizer in enumerate(config["vectorizers"]):
            config["vectorizers"][index] = self.all_vectorizers[vectorizer]

        for index, sampler_config in enumerate(config["samplers"]):
            config["samplers"][index]["class"] = self.all_samplers[sampler_config["class"]]

        return config

    def read_config_file(self):
        config = None
        with open('ariadne_config.json', 'r') as f:
            config = json.load(f)

        return config

    def delete_folder(self, path):
        if os.path.exists(path):
            # os.remove(path)
            print("Deleting folder: ", path)
            shutil.rmtree(path)

    def download_base_data(self, index, session, gt_session, field, download_limit=False):

        classifier = ActiveLearningNoUi(logs_filename="download.txt")
        classifier.download_data(index=index, session=session,
                                 gt_session=gt_session, download_files=True, debug_limit=download_limit,
                                 text_field=field, config_relative_path='../')
        classifier.clean_logs()

    def delete_index(self, index, timeout="2m"):

        try:
            res = Es_connector(index=index, config_relative_path='../').es.indices.delete(index=index, timeout=timeout)
            print("The index ", index, " was removed")
            return res
        except elasticsearch.exceptions.NotFoundError as e:
            return e

    def restore_index(self, index, repo_name, snapshot_name, timeout="2m"):

        res = Es_connector(index=index, config_relative_path='../').es.snapshot.restore(repository=repo_name, snapshot=snapshot_name,
                                                             wait_for_completion=True, master_timeout=timeout)
        print("The index ", index, " was restored")
        return res

    def run(self):

        args = self.get_script_params()

        self.delete_folder(os.path.join(os.getcwd(), "classification", "logs"))
        self.delete_folder(os.path.join(os.getcwd(), "classification", "tmp_data"))
        self.delete_folder(os.path.join(os.getcwd(), "classification", "original_tmp_data"))

        i=0
        for field in args["fields"]:
            for VectorizerClass in args["vectorizers"]:
                for LearnerClass in args["learners"]:
                    for sampler_config in args["samplers"]:

                        response = self.delete_index(args["index"])
                        response = self.restore_index(args["index"], args["repo_name"], args["snapshot_name"])

                        self.download_base_data(args["index"], args["session"], args["gt_session"], field,
                                                download_limit=args["download_limit"])

                        learner = LearnerClass(vectorizer=VectorizerClass())
                        sampler = sampler_config["class"](**sampler_config["params"])
                        logs_filename = "best_config_" + format(i, '03') + ".txt"

                        classifier = ActiveLearningNoUi(logs_filename=logs_filename, sampler=sampler, learner=learner)
                        classifier.run(index=args["index"], session=args["session"], gt_session=args["gt_session"],
                                       num_questions=args["num_sampling_questions"], text_field=field,
                                       max_loops=args["max_sampling_loops"], config_relative_path="../")
                        i+=1





#Instantiating the class and running the tests
Ariadne(samplers=samplers_module, learners=learners_module, vectorizers=vectorizers_module).run()