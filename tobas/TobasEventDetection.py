from gensim.test.utils import common_corpus, common_dictionary
from gensim.models import HdpModel
from gensim.corpora.dictionary import Dictionary
from mabed.es_connector import Es_connector
from nltk.tokenize import TweetTokenizer
from datetime import datetime
from mabed.mabed import MABED
from tobas.TobasCorpus import TobasCorpus
import networkx as nx
import numpy as np
import mabed.stats as st

class TobasEventDetection(MABED):

    def __init__(self):
        self.tknzr = TweetTokenizer()

    def detect_events(self, index, doc_field, max_perc_words_by_topic, logger, time_slice_length, k=10, rel_words_per_event=5, theta=0.6, sigma=0.5):

        # vocabulary = self.get_vocabulary(index, doc_field, max_perc_words_by_topic)
        # corpus = TobasCorpus(vocabulary=vocabulary)  # text timestamp_ms (must be a date object)
        vocabulary_tweets = self.get_vocabulary_tweets(index, doc_field, max_perc_words_by_topic)
        self.corpus = TobasCorpus(tweets=vocabulary_tweets)  # text timestamp_ms (must be a date object)
        self.corpus.discretize(time_slice_length, logger=logger)

        mabed = MABED(self.corpus, logger)
        self.rel_words_per_event = rel_words_per_event
        self.p = rel_words_per_event # since some inherited methods need it with this name
        self.theta = theta
        self.sigma = sigma
        basic_events = mabed.phase1()
        final_events = self.phase2(basic_events)

        return final_events

    def get_vocabulary_tweets(self, index, doc_field, max_perc_words_by_topic):

        tweets = self.get_tweets(index=index, doc_field=doc_field)
        tokenized_docs = [tweet["_source"]["text"] for tweet in tweets]
        vocabulary = self.get_vocabulary(tokenized_docs, max_perc_words_by_topic)

        filtered_tweets = []
        for tweet in tweets:

            matching_words = [word for word in tweet['_source']["text"] if word in vocabulary]
            if len(matching_words)>0:
                tweet['_source']["text"] = " ".join(tweet['_source']["text"])
                filtered_tweets.append(tweet)

        return filtered_tweets



    def get_vocabulary(self, tokenized_docs, max_perc_words_by_topic):


        words_distribution = Dictionary(tokenized_docs)  # list of (word, word_count) tuples
        corpus = [words_distribution.doc2bow(doc) for doc in
                  tokenized_docs]  # Convert document into the bag-of-words (BoW) format = list of (token_id, token_count) tuples.

        print('Getting initial vocabulary at ', datetime.now())
        topics = self.get_topics(corpus, words_distribution)
        print('Got vocabulary at ', datetime.now(), "(", len(topics)," topics)", topics)

        # Now filter the most important terms
        vocabulary=set()

        avg_topics_length = [len(topic[1]) for topic in topics]
        avg_topics_length = sum(avg_topics_length)/len(topics)
        max_words_by_topic = int(avg_topics_length * max_perc_words_by_topic)

        for topic in topics:
            topic_words = topic[1]
            i = 0
            topic_words_size = len(topic_words)

            while i <= max_words_by_topic and i<topic_words_size: #topic_words[i][0] palabra, topic_words[i][1] weight
                vocabulary.add(topic_words[i][0])
                i += 1

        # lala = { word:idx for idx, word in enumerate(vocabulary)}
        return vocabulary

    def get_topics(self, corpus, vocabulary):

        hdp = HdpModel(corpus=corpus, id2word=vocabulary)
        # Docs say that if -1 all topics will be in result (ordered by significance). num_words is optional.
        # .print_topics(num_topics=20, num_words=10)
        # Docs are wrong. If you use -1 the list will be empty. So just don't specify the num_topics:
        return hdp.show_topics(formatted=False)

    def chunks(l, n):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(l), n):
            yield l[i:i + n]

    def get_tweets(self, index, doc_field):

        my_connector = Es_connector(index=index)
        all_tweets = []
        query = {
            "query": {"exists": {"field": doc_field}}
        }
        res = my_connector.init_paginatedSearch({"_source": [doc_field, "timestamp_ms"], "query": {"match_all": {}}})
        sid = res["sid"]
        scroll_size = res["scroll_size"]

        # Analyse and process page by page
        processed_tweets = 0
        while scroll_size > 0:

            tweets = res["results"]
            all_tweets.extend([{ '_source': { "text": self.tknzr.tokenize(tweet["_source"][doc_field]), "timestamp_ms": tweet["_source"]["timestamp_ms"]}} for tweet in tweets])
            processed_tweets += scroll_size

            res = my_connector.loop_paginatedSearch(sid, scroll_size)
            scroll_size = res["scroll_size"]

        return all_tweets

    def phase2(self, basic_events):
        print('Phase 2...')

        # create the event graph (directed) and the redundancy graph (undirected)
        self.event_graph = nx.DiGraph(name='Event graph')
        self.redundancy_graph = nx.Graph(name='Redundancy graph')
        refined_events = []

        for basic_event in basic_events:

            main_word = basic_event[2]
            candidate_words = self.corpus.cooccurring_words(basic_event, self.rel_words_per_event)
            main_word_freq = self.corpus.global_freq[self.corpus.vocabulary[main_word], :].toarray()
            main_word_freq = main_word_freq[0, :]
            related_words = []

            # identify candidate words based on co-occurrence
            if candidate_words is not None:
                for candidate_word in candidate_words:
                    candidate_word_freq = self.corpus.global_freq[self.corpus.vocabulary[candidate_word], :].toarray()
                    candidate_word_freq = candidate_word_freq[0, :]

                    # compute correlation and filter according to theta
                    weight = (st.erdem_correlation(main_word_freq, candidate_word_freq) + 1) / 2
                    if weight >= self.theta:
                        related_words.append((candidate_word, weight))

                # if len(related_words) > 1:
                # I also removed a tab. The following lines were inside the "if candidate_words is not None:"
            else: print("no related words")

            refined_event = (basic_event[0], basic_event[1], main_word, related_words, basic_event[3])

            if self.update_graphs(refined_event): # check if this event is distinct from those already stored in the event graph
                refined_events.append(refined_event)
            else :
                print("Different main word but same related words")

        # merge redundant events and save the result
        self.events = self.merge_redundant_events(refined_events)
        return self.events