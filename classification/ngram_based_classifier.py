import string
import nltk
import traceback
from nltk.corpus import stopwords
nltk.download('stopwords')
from collections import Counter
from mabed.es_connector import Es_connector
from nltk.tokenize import TweetTokenizer
import re
import json
from elasticsearch_dsl import UpdateByQuery
from nltk.stem.snowball import FrenchStemmer
from nltk.stem.snowball import EnglishStemmer
from nltk.stem.snowball import ArabicStemmer
from nltk.stem.snowball import SpanishStemmer


class NgramBasedClasifier:

    def __init__(self, config_relative_path=''):
        # self.logs = []
        self.current_thread_percentage = 0
        self.config_relative_path = config_relative_path
        self.tknzr = TweetTokenizer()
        self.retrievedLangs = set() # Matching the languages in the dataset

    def get_n_grams(self, text, length=2):
        n_grams = zip(*[text[i:] for i in range(length)])
        # n_grams = list(nltk.bigrams(text))
        return n_grams

    def remove_stop_words(self, full_text, langs=["en", "fr", "es"]):

        punctuation = list(string.punctuation + "…" + "’" + "'" + '🔴' + '•' + '...' + '.')
        multilang_stopwords = self.get_stopwords_for_langs(langs) + ["Ã", "RT", "im"] + punctuation

        full_text = full_text.lower().translate(str.maketrans('', '', string.punctuation))

        tokenized_text = self.tknzr.tokenize(full_text)  # nltk.word_tokenize(full_text)
        filtered_words = list(filter(lambda word: len(word)>1 and word not in multilang_stopwords, tokenized_text))

        full_text = " ".join(filtered_words)
        full_text_no_emojis = self.remove_emojis(full_text)
        full_text_no_emojis = " ".join(full_text_no_emojis.split())
        return full_text_no_emojis

    def remove_urls(self, text):

        return re.sub(r'http\S+', '', text).strip()

    def lemmatize(self, text, lang):

        # spacy.prefer_gpu()
        # nlp = spacy.load(lang) # en fr "en_core_web_sm"
        if lang == "fr":
            stemmer = FrenchStemmer()
        elif lang == "es":
            stemmer = SpanishStemmer()
        else:
            stemmer = EnglishStemmer()

        print("Stemming in lang: ", lang)

        stemmed = []
        for word in text.split(" "):
            stemmed.append(stemmer.stem(word))

        # doc = nlp(u""+text)
        # lem_terms = []
        # for token in doc:
        #     lem_terms.append(token.lemma_)

        return " ".join(stemmed)

    def search_bigrams_related_tweets(self, **kwargs):

        my_connector = Es_connector(index=kwargs["index"])
        if kwargs.get('full_search', False):  # All tweets
            query = {
                "query": {
                   "bool": {
                       "must": [
                           {"match": {kwargs["ngramsPropName"]: kwargs["ngram"]}},
                           {"match": {kwargs["session"]: kwargs["label"]}}
                       ]
                   }
               }
            }
        else:  # matching keywords
            query = {
                "query": {
                   "bool": {
                       "must": [
                           {"match": {"text": kwargs["word"]}},
                           {"match": {kwargs["ngramsPropName"]: kwargs["ngram"]}},
                           {"match": {kwargs["session"]: kwargs["label"]}}
                       ]
                   }
               }
            }

        print(query)

        return my_connector.init_paginatedSearch(query)

    def update_tweets_state_by_ngram(self, **kwargs):

        tweets_connector = Es_connector(index=kwargs["index"], doc_type="tweet")

        if kwargs.get('full_search', False):  # All tweets
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {kwargs["ngramsPropName"]: kwargs["ngram"]}},
                            {"match": {kwargs["session"]: kwargs["query_label"]}}
                        ]
                    }
                }
            }
        else:  # Tweets matching a user-generated query
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"text": kwargs["word"]}},
                            {"match": {kwargs["ngramsPropName"]: kwargs["ngram"]}},
                            {"match": {kwargs["session"]: kwargs["query_label"]}}
                        ]
                    }
                }
            }

        return tweets_connector.update_query(query, kwargs["session"], kwargs["new_label"])


    def search_event_bigrams_related_tweets(self, **kwargs):

        my_connector = Es_connector(index=kwargs["index"])
        query = {
            "query": {
               "bool": {
                   "should": kwargs["target_terms"],
                   "minimum_should_match": 1,
                   "must": [
                       {"match": {kwargs["ngramsPropName"]: kwargs["ngram"]}},
                       {"match": {kwargs["session"]: kwargs["label"]}}
                   ]
               }
           }
        }

        return my_connector.init_paginatedSearch(query)


    def update_tweets_state_by_event_ngram(self, **kwargs):

        tweets_connector = Es_connector(index=kwargs["index"], doc_type="tweet")

        query = {
            "query": {
                "bool": {
                    "should": kwargs["target_terms"],
                    "minimum_should_match": 1,
                    "must": [
                        {"match": {kwargs["ngramsPropName"]: kwargs["ngram"]}},
                        {"match": {kwargs["session"]: kwargs["query_label"]}}
                    ]
                }
            }
        }
        return tweets_connector.update_query(query, kwargs["session"], kwargs["new_label"])


    def get_ngrams(self, **kwargs):

        if kwargs.get('full_search', False):
            query = {
                "bool": {
                    "must": [
                        {"match": {kwargs["session"]: kwargs["label"]}}
                    ]
                }
            }
        else:
            query = {
                "bool": {
                    "must": [
                        {"match": {"text": kwargs["word"]}},
                        {"match": {kwargs["session"]: kwargs["label"]}}
                    ]
                }
            }

        return self.get_ngrams_by_query(query=query, **kwargs)

    def chunks(self, target_list, target_size):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(target_list), target_size):
            yield target_list[i:i + target_size]

    def get_positive_unlabeled_ngrams(self, **kwargs):

        res = self.get_ngrams_by_query(query={
            "match": {
                kwargs["field"]: "confirmed"
            }
        }, **kwargs)

        try:
            return res["aggregations"]["ngrams_count"]["buckets"]
        except KeyError as e:
            return []

    def get_negative_unlabeled_ngrams(self, **kwargs):

        res = self.get_ngrams_by_query(query={
            "match": {
                kwargs["field"]: "negative"
            }
        }, **kwargs)

        try:
            return res["aggregations"]["ngrams_count"]["buckets"]
        except KeyError as e:
            return []

    def get_ngrams_for_ids(self, **kwargs):

        ids_chunks = self.chunks(kwargs["ids"], 50)

        total_buckets = []
        for chunk in ids_chunks:

            ids = ""
            for id in chunk:
                ids += id + " or "
            ids = ids[:-4]

            query = {
                "match": {
                    "id_str": ids
                }
            }

            res = self.get_ngrams_by_query(query=query, **kwargs)
            buckets = res["aggregations"]["ngrams_count"]["buckets"]

            if len(buckets)>0:
                total_buckets += buckets

        try:
            return total_buckets
        except KeyError as e:
            return []

    def get_ngrams_for_event(self, **kwargs):

        query = {
            "bool": {
                "should": kwargs["target_terms"],
                "minimum_should_match": 1,
                "must": [
                    {"match": {kwargs["session"]: kwargs["label"]}}
                ]
            }
        }

        return self.get_ngrams_by_query(query=query, **kwargs)

    def get_ngrams_by_query(self, query="", **kwargs):

        try:
            my_connector = Es_connector(index=kwargs["index"], config_relative_path=self.config_relative_path)
            full_query = {
                "query": query,
                "size": 0,
                "aggs": {
                    "ngrams_count": {
                        "terms": {
                            "field": kwargs["n_size"] + "grams.keyword",
                            "size": kwargs["results_size"]
                        },
                        "aggs": {
                            "status": {
                                "terms": {
                                    "field": kwargs["session"] + ".keyword"
                                }
                            }
                        }
                    }
                }
            }
            return my_connector.search(full_query)

        except Exception as e:
            print('Error: ' + str(e))
            traceback.print_exc()
            return {}


    def get_search_related_classification_data(self, index="test3", word="", session="", label="confirmed OR proposed OR negative", matching_ngrams=[], full_search=False):

        if full_search:
            query = {
                "bool": {
                    "must": [
                        {"match": {session: label}}
                    ]
                }
            }
        else:
            query = {
                "bool": {
                    "must": [
                        {"match": {"text": word}},
                        {"match": {session: label}}
                    ]
                }
            }

        my_connector = Es_connector(index=index)
        res = my_connector.search({
            "size": 0,
            "query": query,
            "aggs": {
                "query_classification": {
                    "terms": {
                        "field": session + ".keyword"
                    }
                }
            }
        })
        return res['aggregations']['query_classification']['buckets']

    def get_bigrams_related_classification_data(self, matching_ngrams=[]):

        # Counting the matching bigrams results by category
        total_ngrams = matching_ngrams["hits"]["total"]
        confirmed_ngrams = 0
        negative_ngrams = 0
        unlabeled_ngrams = 0
        accum_total_ngrams = 0

        for ngram in matching_ngrams['aggregations']['ngrams_count']['buckets']:
            curr_confirmed = self.get_classif_doc_count("confirmed", ngram["status"]["buckets"])
            confirmed_ngrams += curr_confirmed

            curr_negative = self.get_classif_doc_count("negative", ngram["status"]["buckets"])
            negative_ngrams += curr_negative

            curr_unlabeled = self.get_classif_doc_count("proposed", ngram["status"]["buckets"])
            unlabeled_ngrams += curr_unlabeled

            accum_total_ngrams += curr_confirmed + curr_negative + curr_unlabeled

        if accum_total_ngrams ==0:
            return 0,0,0
        else:
            return (confirmed_ngrams / accum_total_ngrams) * total_ngrams, \
                   (negative_ngrams / accum_total_ngrams) * total_ngrams, \
                   (unlabeled_ngrams / accum_total_ngrams) * total_ngrams  # confirmed_ngrams, negative_ngrams, unlabeled_ngrams

    def get_classification_data(self, **kwargs):

        query_classification = self.get_search_related_classification_data(kwargs["index"], kwargs["word"], kwargs["session"], kwargs["label"], kwargs["matching_ngrams"], kwargs['full_search'])

        confirmed_ngrams, negative_ngrams, unlabeled_ngrams = self.get_bigrams_related_classification_data(kwargs["matching_ngrams"])

        return [
            {
                "label": "Query",
                "confirmed": self.get_classif_doc_count("confirmed", query_classification),
                "negative": self.get_classif_doc_count("negative", query_classification),
                "unlabeled": self.get_classif_doc_count("proposed", query_classification)
            },
            {
                "label": "Ngrams",
                "confirmed": confirmed_ngrams,
                "negative": negative_ngrams,
                "unlabeled": unlabeled_ngrams
            }
        ]

    def get_classif_doc_count(self, tag, classification):
        category = list(filter(lambda item: item["key"] == tag, classification))
        if len(category) > 0:
            return category[0]["doc_count"]
        else:
            return 0

    def gerenate_ngrams_for_tweets(self, tweets, **kwargs ):  # remove_stopwords=True, stemming=True):

        length = int(kwargs.get('length', 2))

        tweets_to_update = []  # So the URL doesn't get too large
        for tweet in tweets:
            try:
                clean_text = self.remove_stop_words(tweet["_source"]["text"]).split()
                ngrams = list(self.get_n_grams(clean_text, length))

                tweets_to_update.append({
                    "_ngrams": self.format_single_tweet_ngrams(ngrams),
                    "_id": tweet["_id"]
                })

                # for prop in tweet["_source"]:
                #     if tweet["_source"][prop] == None:
                #         tweet["_source"][prop] = "None"
                full_tweet_ngrams = self.format_single_tweet_ngrams(ngrams)
                self.updatePropertyValue(tweet=tweet, property_name=kwargs["prop"], property_value=full_tweet_ngrams, index=kwargs["index"])

            except Exception as e:
                print('Error: ' + str(e))

        # cnn = Es_connector(index=kwargs["index"])

        # script_source = "for (int i = 0; i < docs.length; ++i) { if(docs[i]['_id'] == ctx._id){ ctx._source['" + kwargs[
        #     "prop"] + "'] = docs[i]['_ngrams']; break; }}"
        # ubq = UpdateByQuery(using=cnn.es, index=cnn.index).script(source=script_source)

        # for i in range(0, len(tweets_to_update), 5):
        #
        #     tweets_chunk = tweets_to_update[i:i + 5]
        #     str_tweets = str(tweets_chunk).replace("None", "\'None\'").replace("\'", "\"")
        #     tweet_ids = [ { "match": {"_id": tweet["_id"]}} for tweet in tweets_chunk]
        #
        #     query = {"query": {"bool": {"should": tweet_ids, "minimum_should_match": "1"}}}
        #     ubq.update_from_dict(query).params(docs=tweets_chunk)
        #     ubq.execute()

            # Es_connector(index=kwargs["index"]).update_by_query(
            #     {"query": {"bool":{"should": tweet_ids, "minimum_should_match":"1" }}},
            #     "for (int i = 0; i < docs.length; ++i) { if(docs[i]['_id'] == ctx._id){ ctx._source['" +
            #     kwargs["prop"] + "'] = docs[i]['_ngrams']; break; }}",
            #     tweets_chunk
            # )

            # # "params": { "docs": tweets_chunk }
            # q = {
            #   "script": {
            #     "inline": "def tweets = " + str_tweets + "; for (int i = 0; i < params.docs.length; ++i) { if(params.docs[i]['_id'] == ctx._id){ ctx._source['" + kwargs["prop"] + "'] = params.docs[i]['_ngrams']; break; }}",
            #     "lang": "painless"
            #   },
            #   "query": {
            #     "bool":{
            #        "should":tweet_ids,
            #        "minimum_should_match":"1"
            #     }
            #   }
            # }
            # print("...")
            # cnn.es.update_by_query(body=q, doc_type='tweet', index=kwargs["index"]) #, params={ "docs": tweets_chunk })
            # def tweets = " + str_tweets + ";

            # ubq = UpdateByQuery(index=cnn.es.index).using(cnn.es).script(
            #     source="for (int i = 0; i < params.docs.length; ++i) { if(params.docs[i]['_id'] == ctx._id){ ctx._source['" + kwargs["prop"] + "'] = params.docs[i]['_ngrams']; break; }}",
            #     params={ "docs": str_tweets }
            # )
            # response = ubq.execute()

            # ubq = UpdateByQuery(index=cnn.es.index).using(cnn.es).script(
            #     source="def tweets = " + str_tweets + "; for (int i = 0; i < params.docs.length; ++i) { if(params.docs[i]['_id'] == ctx._id){ ctx._source['" +
            #            kwargs["prop"] + "'] = params.docs[i]['_ngrams']; break; }}"
            # )
            # response = ubq.execute()




    def remove_emojis(self, string):
        emoji_pattern = re.compile("["
                                   u"\U0001F600-\U0001F64F"  # emoticons
                                   u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                   u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                   u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                                   u"\U00002702-\U000027B0"
                                   u"\U000024C2-\U0001F251"
                                   "]+", flags=re.UNICODE)
        return emoji_pattern.sub(r'', string)

    def generate_ngrams_for_index(self, **kwargs):

        try:
            # Get the data for performinga paginated search
            self.current_thread_percentage = 0
            print("Starting")
            my_connector = Es_connector(index=kwargs["index"])

            query = kwargs.get('query', {
                "query": {
                    "match_all": {}
                }
            })

            res = my_connector.init_paginatedSearch(query)
            sid = res["sid"]
            scroll_size = res["scroll_size"]
            total = int(res["total"])

            # Analyse and process page by page
            i = 0
            total_scrolls = int(total/scroll_size)
            processed_scrolls = 0

            while scroll_size > 0:
                tweets = res["results"]
                self.gerenate_ngrams_for_tweets(tweets, prop=kwargs["prop"], index=kwargs["index"], length=kwargs["length"])

                i += 1
                res = my_connector.loop_paginatedSearch(sid, scroll_size)
                scroll_size = res["scroll_size"]
                processed_scrolls += 1

                self.current_thread_percentage = round(processed_scrolls * 100 / total_scrolls, 0)

                print("Completed: ", self.current_thread_percentage, "%")

            # Clean it at the end so the clien knows when to end asking for more logs
            self.current_thread_percentage = 100

            return True

        except Exception as e:
            print('Error: ' + str(e))
            return False

    # def generate_ngrams_for_unlabeled_tweets_on_index(self, **kwargs):
    #
    #     query={
    #         "query": {
    #             "bool": {
    #                 "must_not": {
    #                     "exists" : { "field" : kwargs["prop"] }
    #                 }
    #             }
    #         }
    #     }
    #
    #     return self.generate_ngrams_for_index(**dict(kwargs, query=query))

    def format_single_tweet_ngrams(self, ngrams):

        full_tweet_ngrams = []
        for ngram in ngrams:
            single_ngram_text = ""
            for term in ngram:
                single_ngram_text = single_ngram_text + term + "-"

            single_ngram_text = single_ngram_text[:-1]  #remove the last - of the single ngram
            full_tweet_ngrams.append(single_ngram_text)

        return full_tweet_ngrams
        #
        # for k, v in ngrams:
        #
        #     ngram_text = ""
        #     for term in k:
        #         ngram_text = ngram_text + term + "-"
        #     ngram_text = ngram_text.strip()
        #
        # return ngram_text

    def get_current_backend_logs(self):
        return { "percentage": self.current_thread_percentage }

    def updatePropertyValue(self, **kwargs):

        tweet = kwargs["tweet"]
        # cnn = Es_connector(index=kwargs["index"]);
        #
        # q = {
        #     "script": {
        #         "inline": "ctx._source." + kwargs["property_name"] + " = params.value",
        #         "lang": "painless",
        #         "params": {
        #             "value": str(kwargs["property_value"])
        #         }
        #     },
        #     "query": {
        #         "match": {
        #             "_id": tweet["_id"]
        #         }
        #     }
        # }
        #
        # cnn.es.update_by_query(body=q, doc_type='tweet', index=kwargs["index"])

        Es_connector(index=kwargs["index"]).es.update(
            index=kwargs["index"],
            doc_type="tweet",
            id=tweet["_id"],
            body={"doc": {
                kwargs["property_name"]: kwargs["property_value"]
            }},
            retry_on_conflict=5
        )

    def get_stopwords_for_langs(self, langs):

        swords = []

        if "en" in langs:
            swords = swords + stopwords.words('english')
            self.retrievedLangs.add("en")
        if "fr" in langs:
            swords = swords + stopwords.words('french')
            self.retrievedLangs.add("fr")
        if "ar" in langs:
            swords = swords + stopwords.words('arabic')
            self.retrievedLangs.add("ar")
        if "nl" in langs:
            swords = swords + stopwords.words('dutch')
            self.retrievedLangs.add("nl")
        if "id" in langs:
            swords = swords + stopwords.words('indonesian')
            self.retrievedLangs.add("id")
        if "fi" in langs:
            swords = swords + stopwords.words('finnish')
            self.retrievedLangs.add("fi")
        if "de" in langs:
            swords = swords + stopwords.words('german')
            self.retrievedLangs.add("de")
        if "hu" in langs:
            swords = swords + stopwords.words('hungarian')
            self.retrievedLangs.add("hu")
        if "it" in langs:
            swords = swords + stopwords.words('italian')
            self.retrievedLangs.add("it")
        if "nb" in langs:
            swords = swords + stopwords.words('norwegian')
            self.retrievedLangs.add("nb")
        if "pt" in langs:
            swords = swords + stopwords.words('portuguese')
            self.retrievedLangs.add("pt")
        if "ro" in langs:
            swords = swords + stopwords.words('romanian')
            self.retrievedLangs.add("ro")
        if "ru" in langs:
            swords = swords + stopwords.words('russian')
            self.retrievedLangs.add("ru")
        if "es" in langs:
            swords = swords + stopwords.words('spanish')
            self.retrievedLangs.add("es")
        if "sv" in langs:
            swords = swords + stopwords.words('swedish')
            self.retrievedLangs.add("sv")
        if "tr" in langs:
            swords = swords + stopwords.words('turkish')
            self.retrievedLangs.add("tr")



        # TODO: complete with the full list of supported langs (there are some langs supported but miissing  and not documented. E.g. Bulgarian or Ukrainian https://pypi.org/project/stop-words/ )
        # The full list of languages may be found in C:/Users/username/AppData/Roming/nltk_data/corpora/stopwords

        return swords
