from gensim.test.utils import common_corpus, common_dictionary
from gensim.models import HdpModel
from gensim.corpora.dictionary import Dictionary
from mabed.es_connector import Es_connector
from nltk.tokenize import TweetTokenizer
from datetime import datetime

class TobasEventDetection:

    def __init__(self):
        self.tknzr = TweetTokenizer()

    def detect_events(self, index):
        # tokenized_docs = [['human', 'interface', 'computer'],
        #  ['survey', 'user', 'computer', 'system', 'response', 'time'],
        #  ['eps', 'user', 'interface', 'system']]
        # Setting up the corpus

        tokenized_docs = self.get_tweets(index=index, doc_field="text")
        words_distribution = Dictionary(tokenized_docs) # list of (word, word_count) tuples
        corpus = [words_distribution.doc2bow(doc) for doc in tokenized_docs]  # Convert document into the bag-of-words (BoW) format = list of (token_id, token_count) tuples.

        print('Getting topics at ', datetime.now())
        topics = self.get_topics(corpus, words_distribution)
        print('Got topics at ', datetime.now())
        return topics

    def get_topics(self, corpus, vocabulary):

        hdp = HdpModel(corpus=corpus, id2word=vocabulary)
        return hdp.show_topics(formatted=True) #.print_topics(num_topics=20, num_words=10)  # If -1 all topics will be in result (ordered by significance). num_words is optional.

    def chunks(l, n):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(l), n):
            yield l[i:i + n]

    def get_tweets(self, index, doc_field):

        my_connector = Es_connector(index=index)
        all_tweets = []
        res = my_connector.init_paginatedSearch({"_source": doc_field, "query": {"match_all": {}}})
        sid = res["sid"]
        scroll_size = res["scroll_size"]

        # Analyse and process page by page
        processed_tweets = 0
        while scroll_size > 0:

            tweets = res["results"]
            all_tweets.extend([self.tknzr.tokenize(tweet["_source"][doc_field]) for tweet in tweets])
            processed_tweets += scroll_size

            res = my_connector.loop_paginatedSearch(sid, scroll_size)
            scroll_size = res["scroll_size"]
            print(processed_tweets)


        return all_tweets