from classification.active_learning_no_ui import ActiveLearningNoUi
import classification.samplers as samplers_module
import classification.learners as learners_module
import classification.vectorizers as vectorizers_module
import json

class Ariadne:

    def __init__(self, samplers, learners, vectorizers):
        self.samplers = ariadne.module_to_dict(samplers)
        self.vectorizers = ariadne.module_to_dict(vectorizers)
        self.learners = ariadne.module_to_dict(learners)

    def module_to_dict(self, module):
        return {key: getattr(module, key) for key in dir(module)}

    def to_boolean(self, str_param):
        if isinstance(str_param, bool):
            return str_param
        elif str_param.lower() in ('yes', 'true', 't', 'y', '1'):
            return True
        else:
            return False

    def get_script_params(self, learners):

        with open('ariadne_config.json', 'r') as f:
            config = json.load(f)

            LinearSVCBasedModel = self.learners["LinearSVCBasedModel"]
            model = LinearSVCBasedModel()

        return config

ariadne = Ariadne()

args = ariadne.get_script_params(samplers=samplers_module, learners=learners_module, vectorizers=vectorizers_module)