import nltk
from nltk.corpus import stopwords
nltk.download('stopwords')


class LangBasedStopWords:

    def stop_words(self):
        return self.stopwords

    def name(self):
        return self.name


class EnglishStopWords(LangBasedStopWords):

    def __init__(self, extension_list=None):
        self.name = "en"
        if extension_list:
            self.stopwords = stopwords.words('english') + extension_list  # e.g. ['a', 'La']
        else:
            self.stopwords = stopwords.words('english')


class FrenchStopWords(LangBasedStopWords):

    def __init__(self, extension_list=None):
        self.name = "fr"
        if extension_list:
            self.stopwords = stopwords.words('french') + ['a', 'La', 'les', 'é', 'c\'est', 'j\'ai', 'ça', 'rt', 'via', '’']
        else:
            self.stopwords = stopwords.words('french')

