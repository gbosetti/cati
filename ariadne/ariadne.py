from classification.active_learning_no_ui import ActiveLearningNoUi
import classification.samplers as samplers_module
import classification.learners as learners_module
import classification.vectorizers as vectorizers_module
import json

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

    def run(self):

        args = self.get_script_params()

        for field in args["fields"]:
            for VectorizerClass in args["vectorizers"]:
                for LearnerClass in args["learners"]:
                    for sampler_config in args["samplers"]:

                        learner = LearnerClass(vectorizer=VectorizerClass())
                        sampler = sampler_config["class"](sampler_config["params"])

                        classifier = ActiveLearningNoUi(logs_filename="logs_filename", sampler=sampler, learner=learner)
                        classifier.run(index=args["index"], session=args["session"], gt_session=args["gt_session"],
                                       num_questions=args["num_sample_questions"], text_field=field,
                                       max_loops=args["max_sampling_loops"])


ariadne = Ariadne(samplers=samplers_module, learners=learners_module, vectorizers=vectorizers_module)
ariadne.run()