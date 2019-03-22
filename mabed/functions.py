# coding: utf-8

import timeit
import json
import time

from flask import jsonify
from mabed.es_corpus import Corpus
from mabed.mabed import MABED
from mabed.es_connector import Es_connector

# es connector exceptions
from elasticsearch import RequestError
import elasticsearch.helpers

from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from nltk.tokenize import word_tokenize
from elasticsearch import Elasticsearch
__author__ = "Firas Odeh"
__email__ = "odehfiras@gmail.com"


# Interface Functions
class Functions:
    #TODO check if this needs to e configured on master
    def __init__(self):
        self.sessions_index = 'mabed_sessions'
        self.sessions_doc_type = 'session'
        # print("Functions init")

    def get_total_tweets(self, index):

        try:
            my_connector = Es_connector(index=index, doc_type="tweet")  # self.sessions_doc_type)
            res = my_connector.search({
                "query": {
                    "match_all": {}
                }
            })

            return res['hits']['total']
        except RequestError:
            return '...'

    def get_total_hashtags(self, index):

        my_connector = Es_connector(index=index, doc_type="tweet")  # self.sessions_doc_type)
        try:
            res = my_connector.search({
                "query": {
                    "exists": {"field": "entities.hashtags"}
                }
            })
            return res['hits']['total']
        except RequestError:
            return '...'


    def get_mapping_spec(self, index, doc):

        return Es_connector(index=index, doc_type=doc).es.indices.get_mapping(index=index, doc_type=doc)

    def get_total_mentions(self,index):
        my_connector = Es_connector(index=index, doc_type= "tweet")
        print("Index for get mentions ", index)
        try:
            res = my_connector.search({
                    "size": 0,
                    "query": {
                        "exists": {"field": "entities.user_mentions"}
                    }
            })
            return res['hits']['total']
        except RequestError:
            return 'None  Found'

    def get_total_urls(self, index):

        my_connector = Es_connector(index=index, doc_type="tweet")  # self.sessions_doc_type)
        try:
            res = my_connector.search({
                "query": {
                    "exists": {"field": "entities.urls"}
                }
            })

            return res['hits']['total']
        except RequestError:
            return '...'

    # get the 10 most used languages
    def get_lang_count(self, index):

        my_connector = Es_connector(index=index, doc_type="tweet")
        try:
            res = my_connector.search(
                {
                    "size": 0,
                    "aggs": {
                        "distinct_lang": {
                            "terms": {
                                "field": "lang.keyword",
                                "size": 10
                            }
                        },
                        "count": {
                            "cardinality": {
                                "field": "lang.keyword"
                            }
                        }
                    }
                })

            return res
        except RequestError:
            return {'aggregations': {'count': {'value': '...'},
                                     'distinct_lang': {
                                         'buckets': [{'key': '...', 'doc_count': '...'} for i in range(10)]}}}

    def get_total_images(self, index):
        my_connector = Es_connector(index=index, doc_type="tweet")
        try:
            res = my_connector.search(
                {
                    "size": 0,
                    "aggs": {
                        "distinct_img": {
                            "terms": {
                                "field": "extended_entities.media.id_str.keyword",
                                "size": 1
                            }
                        },
                        "count": {
                            "cardinality": {
                                "field": "extended_entities.media.id_str.keyword"
                            }
                        }
                    }
                }
            )
            return res['aggregations']['count']['value']
        except RequestError:
              # this may happen if media.id_str is not bound to a keyword multi field
              # PUT / twitterfdl2017 / _mapping / tweet

              # {
              # "properties": {
              # "extended_entities.media.id_str": {
              # "type": "text",
              # "fields": {
              # "keyword": {
              # "type": "keyword"
              # }
              # }
              # }
              # }
              # }
            return '...'

    def get_classification_stats(self, index, session_name):
        session = "session_" + session_name
        keyword = session+".keyword"
        my_connector = Es_connector(index=index)
        try:
            res = my_connector.search(
                {"_source": ["id_str", "text", "imagesCluster", session, "lang"],
                 "size": 0,
                 "aggs": {
                     "classification_status": {
                         "terms": {
                             "field":  keyword,
                             "size": 10
                         }
                     },
                     "count": {
                         "cardinality": {
                             "field": keyword
                         }
                     }
                 }}
            )
            return res['aggregations']['classification_status']['buckets']
        except RequestError:
            return {
                 [
                    {'key': 'proposed', 'doc_count': '0'},
                    {'key': 'positive', 'doc_count': '0'},
                    {'key': 'negative', 'doc_count': '0'}
                ]}

    # ==================================================================
    # Event Detection
    # ==================================================================

    def detect_events(self, index="test3", k=10, maf=10, mrf=0.4, tsl=30, p=10, theta=0.6, sigma=0.6, cluster=2, **kwargs):
        sw = 'stopwords/twitter_all.txt'
        sep = '\t'

        kwargs["logger"].add_log('Parameters:   Index: %s\n   k: %d\n   Stop-words: %s\n   Min. abs. word frequency: %d\n   Max. rel. word frequency: %f' %
            (index, k, sw, maf, mrf))
        kwargs["logger"].add_log('   p: %d\n   theta: %f\n   sigma: %f' % (p, theta, sigma))
        kwargs["logger"].add_log('Loading corpus...')

        start_time = timeit.default_timer()
        my_corpus = Corpus(sw, maf, mrf, sep, index=index)
        elapsed = timeit.default_timer() - start_time
        kwargs["logger"].add_log('Corpus loaded in %f seconds.' % elapsed)

        time_slice_length = tsl
        kwargs["logger"].add_log('Partitioning tweets into %d-minute time-slices...' % time_slice_length)
        start_time = timeit.default_timer()
        my_corpus.discretize(time_slice_length, cluster, logger=kwargs["logger"])
        elapsed = timeit.default_timer() - start_time
        kwargs["logger"].add_log('Partitioning done in %f seconds.' % elapsed)

        kwargs["logger"].add_log('Running MABED...')
        start_time = timeit.default_timer()
        mabed = MABED(my_corpus, kwargs["logger"])
        mabed.run(k=k, p=p, theta=theta, sigma=sigma)
        elapsed = timeit.default_timer() - start_time
        kwargs["logger"].add_log('Event detection performed in %f seconds.' % elapsed)
        return mabed

    def event_descriptions(self, index="test3", k=10, maf=10, mrf=0.4, tsl=30, p=10, theta=0.6, sigma=0.6, cluster=2, **kwargs):
        mabed = self.detect_events(index, k, maf, mrf, tsl, p, theta, sigma, cluster, logger=kwargs["logger"])

        # format data
        event_descriptions = []
        impact_data = []
        formatted_dates = []
        for i in range(0, mabed.corpus.time_slice_count):
            formatted_dates.append(int(time.mktime(mabed.corpus.to_date(i).timetuple())) * 1000)

        for event in mabed.events:
            mag = event[0]
            main_term = event[2]
            raw_anomaly = event[4]
            formatted_anomaly = []
            time_interval = event[1]
            related_terms = []
            for related_term in event[3]:
                # related_terms.append(related_term[0] + ' (' + str("{0:.2f}".format(related_term[1])) + ')')
                related_terms.append({'word': related_term[0], 'value': str("{0:.2f}".format(related_term[1]))})
            event_descriptions.append((mag,
                                       str(mabed.corpus.to_date(time_interval[0])),
                                       str(mabed.corpus.to_date(time_interval[1])),
                                       main_term,
                                       json.dumps(related_terms)))
            for i in range(0, mabed.corpus.time_slice_count):
                value = 0
                if time_interval[0] <= i <= time_interval[1]:
                    value = raw_anomaly[i]
                    if value < 0:
                        value = 0
                formatted_anomaly.append([formatted_dates[i], value])
            impact_data.append({"key": main_term, "values": formatted_anomaly})

        return {"event_descriptions": event_descriptions, "impact_data": impact_data}

    def detect_filtered_events(self, index="test3", k=10, maf=10, mrf=0.4, tsl=30, p=10, theta=0.6, sigma=0.6,
                               session=False, filter=False, cluster=2, **kwargs):
        sw = 'stopwords/twitter_all.txt'
        sep = '\t'
        kwargs["logger"].add_log('Parameters--')
        kwargs["logger"].add_log(
            '   Index: %s\n   k: %d\n   Stop-words: %s\n   Min. abs. word frequency: %d\n   Max. rel. word frequency: %f' %
            (index, k, sw, maf, mrf))
        kwargs["logger"].add_log('   p: %d\n   theta: %f\n   sigma: %f' % (p, theta, sigma))

        kwargs["logger"].add_log('Loading corpus...')
        start_time = timeit.default_timer()
        my_corpus = Corpus(sw, maf, mrf, sep, index=index, session=session, filter=filter)
        if not my_corpus.tweets:
            return False

        elapsed = timeit.default_timer() - start_time
        kwargs["logger"].add_log('Corpus loaded in %f seconds.' % elapsed)

        time_slice_length = tsl
        kwargs["logger"].add_log('Partitioning tweets into %d-minute time-slices...' % time_slice_length)
        start_time = timeit.default_timer()
        my_corpus.discretize(time_slice_length, cluster, logger=kwargs["logger"])
        elapsed = timeit.default_timer() - start_time
        kwargs["logger"].add_log('Partitioning done in %f seconds.' % elapsed)

        kwargs["logger"].add_log('Running MABED...')
        start_time = timeit.default_timer()
        mabed = MABED(my_corpus, kwargs["logger"])
        mabed.run(k=k, p=p, theta=theta, sigma=sigma)
        elapsed = timeit.default_timer() - start_time
        kwargs["logger"].add_log('Event detection performed in %f seconds.' % elapsed)
        return mabed

    def filtered_event_descriptions(self, index="test3", k=10, maf=10, mrf=0.4, tsl=30, p=10, theta=0.6, sigma=0.6,
                                    session=False, filter=False, cluster=2, **kwargs):
        mabed = self.detect_filtered_events(index, k, maf, mrf, tsl, p, theta, sigma, session, filter, cluster, logger=kwargs["logger"])
        if not mabed:
            return False

        # format data
        event_descriptions = []
        impact_data = []
        formatted_dates = []
        for i in range(0, mabed.corpus.time_slice_count):
            formatted_dates.append(int(time.mktime(mabed.corpus.to_date(i).timetuple())) * 1000)

        for event in mabed.events:
            mag = event[0]
            main_term = event[2]
            raw_anomaly = event[4]
            formatted_anomaly = []
            time_interval = event[1]
            related_terms = []
            for related_term in event[3]:
                # related_terms.append(related_term[0] + ' (' + str("{0:.2f}".format(related_term[1])) + ')')
                related_terms.append({'word': related_term[0], 'value': str("{0:.2f}".format(related_term[1]))})
            event_descriptions.append((mag,
                                       str(mabed.corpus.to_date(time_interval[0])),
                                       str(mabed.corpus.to_date(time_interval[1])),
                                       main_term,
                                       json.dumps(related_terms)))
            for i in range(0, mabed.corpus.time_slice_count):
                value = 0
                if time_interval[0] <= i <= time_interval[1]:
                    value = raw_anomaly[i]
                    if value < 0:
                        value = 0
                formatted_anomaly.append([formatted_dates[i], value])
            impact_data.append({"key": main_term, "values": formatted_anomaly})

        return {"event_descriptions": event_descriptions, "impact_data": impact_data}

    # ==================================================================
    # Tweets
    # ==================================================================

    def get_tweets(self, index="test3", word="", session="", label="confirmed OR proposed OR negative"):
        my_connector = Es_connector(index=index)
        res = my_connector.init_paginatedSearch({
            "query": {
                "bool": {
                    "must": [
                        {"match": {"text": word }},
                        {"match": {session: label}}
                    ]
                }
            }
        })

        return res

    def get_tweets_scroll(self, index, sid, scroll_size):
        my_connector = Es_connector(index=index)
        res = my_connector.loop_paginatedSearch(sid, scroll_size)
        return res

    def get_big_tweets(self, index="test3", word=""):
        my_connector = Es_connector(index=index)
        res = my_connector.bigSearch(
            {
                "_source": ["text", "id_str", "extended_entities", "user", "created_at", "link"],
                "query": {
                    "simple_query_string": {
                        "fields": [
                            "text"
                        ],
                        "query": word
                    }
                }
            })
        return res

    def get_tweets_state(self, index="test3", session="", state="proposed"):
        my_connector = Es_connector(index=index)
        res = my_connector.init_paginatedSearch(
            {
                "query": {
                    "term": {
                        "session_" + session: state
                    }
                }
            })
        return res

    def get_tweets_query_state(self, index="test3", word="", state="proposed", session=""):
        my_connector = Es_connector(index=index)
        query = {
            "query": {
                "bool": {
                    "must": {
                        "simple_query_string": {
                            "fields": [
                                "text"
                            ],
                            "query": word
                        }
                    },
                    "filter": {
                        "bool": {
                            "should": [
                                {
                                    "match": {
                                        session: state
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        }
        res = my_connector.init_paginatedSearch(query)
        return res

    def get_big_tweets_scroll(self, index="test3", word=""):
        my_connector = Es_connector(index=index)
        res = my_connector.init_paginatedSearch(
            {
                "_source": ["text", "id_str", "extended_entities", "user", "created_at", "link"],
                "query": {
                    "simple_query_string": {
                        "fields": [
                            "text"
                        ],
                        "query": word
                    }
                }
            })
        return res

    def get_event_tweets(self, index="test3", main_term="", related_terms=""):
        my_connector = Es_connector(index=index)
        terms = []
        words = main_term + ' '
        for t in related_terms:
            terms.append({"match": {
                "text": {
                    "query": t['word'],
                    "boost": t['value']
                }
            }})
            words += t['word'] + " "
        terms.append({"match": {
            "text": {
                "query": main_term,
                "boost": 2
            }
        }})
        # res = my_connector.search({"query": {"term" : { "text" : word }}})
        # query = {
        #     "bool": {
        #         "must": {
        #             "match": {
        #                 "text": {
        #                     "query": main_term,
        #                     "operator": "or"
        #                 }
        #             }
        #         },
        #         "should": terms
        #     }
        # }
        query = {
            "sort": [
                "_score"
            ],
            "query": {
                "bool": {
                    "should": terms
                }
            }
        }
        # print(query)
        # res = my_connector.search(query)
        res = my_connector.init_paginatedSearch(query)
        return res

    def get_event_filter_tweets(self, index="test3", main_term="", related_terms="", state="proposed", session=""):
        my_connector = Es_connector(index=index)
        terms = []
        words = main_term + ' '
        for t in related_terms:
            terms.append({"match": {
                "text": {
                    "query": t['word'],
                    "boost": t['value']
                }
            }})
            words += t['word'] + " "
        terms.append({"match": {
            "text": {
                "query": main_term,
                "boost": 2
            }
        }})
        # query = {
        #     "sort": [
        #         "_score"
        #     ],
        #         "query": {
        #                 "bool": {
        #                     "should": terms
        #                 }
        #             }
        #         }

        query = {
            "sort": [
                "_score"
            ],
            "query": {
                "bool": {
                    "must": [
                        {
                            "bool": {
                                "should": terms
                            }
                        }
                    ],
                    "filter": {
                        "bool": {
                            "should": [
                                {
                                    "match": {
                                        session: state
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        }
        res = my_connector.init_paginatedSearch(query)
        return res

    def get_event_tweets2(self, index="test3", main_term="", related_terms="", cid=0):
        my_connector = Es_connector(index=index)
        terms = []
        words = main_term + ' '
        for t in related_terms:
            terms.append({"match": {
                "text": {
                    "query": t['word'],
                    "boost": t['value']
                }
            }})
            words += t['word'] + " "
        terms.append({"match": {
            "text": {
                "query": main_term,
                "boost": 2
            }
        }})
        # terms.append({"match": {
        #     "imagesCluster": {
        #         "query": cid
        #     }
        # }})
        # query = {
        #         "query": {
        #                 "bool": {
        #                     "must": {
        #                         "exists": {
        #                             "field": "imagesCluster"
        #                         }
        #                     },
        #                     # "must": { "match": { "imagesCluster" : cid }},
        #                     "should": terms
        #                 }
        #             }
        #         }

        query = {
            "sort": [
                "_score"
            ],
            "query": {
                "bool": {
                    "should": terms,
                    "minimum_should_match": 1,
                    "must": [
                        {
                            "match": {
                                "imagesCluster": cid
                            }
                        }
                    ]
                }
            }
        }

        # res = my_connector.bigSearch(query)
        res = my_connector.init_paginatedSearch(query)
        return res

    def get_cluster_tweets(self, index="test3", cid=0):
        my_connector = Es_connector(index=index)
        query = {
            "query": {
                "term": {"imagesCluster": cid}
            }
        }
        res = my_connector.search(query)
        return res

    def get_dataset_date_range(self, index="test3"):

        try:
            my_connector = Es_connector(index=index)
            res = my_connector.search({
                "size": 0,
                "query": {
                    "match_all": {}
                },
                "aggs": {
                    "min_timestamp": {"min": {"field": "@timestamp"}},
                    "max_timestamp": {"max": {"field": "@timestamp"}}
                }
            })
            return res["aggregations"]

        except RequestError:
            print("Error: try creating the keyword field")  #TODO
            return {}

    def get_event_image(self, index="test3", main_term="", related_terms="",s_name=""):
        my_connector = Es_connector(index=index)
        terms = []
        session = 'session_'+s_name
        words = main_term + ' '
        for t in related_terms:
            terms.append({"match": {
                "text": {
                    "query": t['word'],
                    "boost": t['value']
                }
            }})
            words += t['word'] + " "
        terms.append({"match": {
            "text": {
                "query": main_term,
                "boost": 2
            }
        }})
        # res = my_connector.search({"query": {"term" : { "text" : word }}})
        # query = {
        #     "bool": {
        #         "must": {
        #             "match": {
        #                 "text": {
        #                     "query": main_term,
        #                     "operator": "or"
        #                 }
        #             }
        #         },
        #         "should": terms
        #     }
        # }
        # TODO add session field to this function
        query = {
            "size": 1,
            "_source": [
                "id_str",
                "imagesCluster",
                session,
                "extended_entities"
            ],
            "query": {
                "bool": {
                    "must":
                        {
                            "exists": {
                                "field": "extended_entities"
                            }
                        },
                    "should": terms
                }
            }
        }
        # print(query)
        res = my_connector.search(query)
        return res

    def get_valid_tweets(self, index="test3"):
        my_connector = Es_connector(index=index)
        res = my_connector.search({
            "query": {
                "simple_query_string": {
                    "fields": [
                        "text"
                    ],
                    "query": word
                }
            }
        })
        # res = my_connector.bigSearch(
        #     {
        #         "_source": ["text", "id_str", "extended_entities", "user", "created_at", "link"],
        #         "query": {
        #             "simple_query_string": {
        #               "fields": [
        #                 "text"
        #               ],
        #               "query": word
        #             }
        #           }
        #     })
        return res['hits']['hits']

    # ==================================================================
    # Clusters
    # ==================================================================

    def get_clusters(self, index="test3", word="", session="", label="confirmed OR proposed OR negative"):
        my_connector = Es_connector(index=index)
        res = my_connector.search({
            "size": 1,
            "query": {
                "bool": {
                    "must": [
                        {"match": {"text": word }},
                        {"match": {session: label}}
                    ]
                }
            },
            "aggs": {
                "group_by_cluster": {
                    "terms": {
                        "field": "imagesCluster",
                        "size": 9999
                    }
                }
            }
        })
        clusters = res['aggregations']['group_by_cluster']['buckets']
        data = self.get_current_session_data(index)

        for cluster in clusters:
            if data and data["duplicates"]:
                images = data['duplicates'][cluster['key']]
                cluster['image'] = images[0]
                cluster['size'] = len(images)
            else:
                cluster['image'] = "Missing 'duplicated' file"
                cluster['size'] = "Missing 'duplicated' file"

        return clusters


    def get_image_folder(self, index):

        with open('config.json') as f:
            config = json.load(f)

        try:
            for es_sources in config['elastic_search_sources']:
                if es_sources['index'] == index:
                    return es_sources['images_folder']
            return

        except IOError as err:
            print("The image-duplicated file was not found.", err)
            return

    def get_current_session_data(self, index):

        with open('config.json') as f:
            config = json.load(f)

        try:
            for es_sources in config['elastic_search_sources']:
                if es_sources['index'] == index:
                    with open(es_sources['image_duplicates']) as file:
                        return json.load(file)
            return

        except IOError as err:
            print("The image-duplicated file was not found.", err)
            return

    def get_event_clusters(self, index="test3", main_term="", related_terms=""):
        my_connector = Es_connector(index=index)
        terms = []
        words = main_term + ' '
        for t in related_terms:
            terms.append({"match": {
                "text": {
                    "query": t['word'],
                    "boost": t['value']
                }
            }})
            words += t['word'] + " "
        terms.append({"match": {
            "text": {
                "query": main_term,
                "boost": 2
            }
        }})

        query = {
            "size": 0,
            "query": {
                "bool": {
                    "should": terms
                }
            },
            "aggregations": {
                "group_by_cluster": {
                    "terms": {
                        "field": "imagesCluster",
                        "size": 999999
                    }
                }
            }
        }
        res = my_connector.search(query)
        clusters = res['aggregations']['group_by_cluster']['buckets']

        data = self.get_current_session_data(index)

        for cluster in clusters:
            if data and data["duplicates"]:
                q2 = {
                    "query": {
                        "term": {"imagesCluster": cluster['key']}
                    }
                }
                cres = my_connector.count(q2)
                images = data['duplicates'][cluster['key']]
                cluster['image'] = images[0]
                cluster['size'] = cres['count']
            else:
                cluster['image'] = "Missing 'duplicated' file"
                cluster['size'] = "Missing 'duplicated' file"

        return clusters

    # ==================================================================
    # Sessions
    # ==================================================================

    # Get all sessions
    def get_sessions(self):
        my_connector = Es_connector(index=self.sessions_index, doc_type=self.sessions_doc_type)
        query = {
            "query": {
                "match_all": {}
            }
        }

        res = my_connector.search(query)
        return res

    # Get session by session ID
    def get_session(self, id):
        my_connector = Es_connector(index=self.sessions_index, doc_type=self.sessions_doc_type)
        res = my_connector.get(id)
        return res

    # Get session by session name
    def get_session_by_Name(self, name):
        my_connector = Es_connector(index=self.sessions_index, doc_type=self.sessions_doc_type)
        query = {
            "query": {
                "constant_score": {
                    "filter": {
                        "term": {
                            "s_name": name
                        }
                    }
                }
            }
        }
        print("index: ", self.sessions_index, " doc: ", self.sessions_doc_type, " name: ", name)
        res = my_connector.search(query)
        return res

    # Add new session
    def create_mabed_sessions_index(self, es):

        settings = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "blocks": {
                    "read_only_allow_delete": "false"
                }
            },
            "mappings": {
                "session": {
                    "properties": {
                        "events": {
                            "type": "text",
                            "fields": {
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            }
                        },
                        "impact_data": {
                            "type": "text",
                            "fields": {
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            }
                        },
                        "s_index": {
                            "type": "text",
                            "fields": {
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            }
                        },
                        "s_name": {
                            "type": "text",
                            "fields": {
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            }
                        },
                        "s_type": {
                            "type": "text",
                            "fields": {
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            }
                        }
                    }
                }
            }
        }
        es.indices.create(index=self.sessions_index, ignore=400, body=settings)

    def fix_read_only_allow_delete(self, index, connector):

        print("index: ", index)
        connector.es.indices.put_settings(index=index, body={
            "index": {
                "blocks": {
                    "read_only_allow_delete": "false"
                }
            }
        })

    # Add new session
    def add_session(self, name, index, **kwargs):

        try:
            my_connector = Es_connector(index=self.sessions_index, doc_type=self.sessions_doc_type)

            es = Elasticsearch([{'host': my_connector.host, 'port': my_connector.port}])

            if not es.indices.exists(index=self.sessions_index):
                self.create_mabed_sessions_index(es)
                kwargs["logger"].add_log("The existence of the " + self.sessions_index + " index was checked")

            my_connector = Es_connector(index=self.sessions_index, doc_type=self.sessions_doc_type)
            session = self.get_session_by_Name(name)

            if session['hits']['total'] == 0:
                self.fix_read_only_allow_delete(self.sessions_index, my_connector)  # Just in case we import it and the property isn't there
                # Creating the new entry in the mabed_sessions
                res = my_connector.post({
                    "s_name": name,
                    "s_index": index,
                    "s_type": "tweet"
                })
                # Adding the session's field in the existing dataset
                tweets_connector = Es_connector(index=index, doc_type="tweet")
                self.fix_read_only_allow_delete(index, tweets_connector)

                kwargs["logger"].add_log("Starting with the labeling of the session's tweet to 'proposed'")
                tweets_connector.update_all('session_' + name, 'proposed', logger=kwargs["logger"])
                kwargs["logger"].add_log("The tweets labels were successfully updated to the 'proposed' state")
                return res
            else:
                kwargs["logger"].add_log("There are no documents in the selected index.")
                return False

        except RequestError as e:  # This is the correct syntax
            print(e)
            return False


    # Update specific field value in an Index
    def update_all(self, index, doc_type, field, value, **kwargs):
        my_connector = Es_connector(index=index, doc_type=doc_type)
        res = my_connector.update_all(field, value, logger=kwargs["logger"])
        return res

    # Update session events results
    def update_session_results(self, id, events, impact_data):
        my_connector = Es_connector(index=self.sessions_index, doc_type=self.sessions_doc_type)
        res = my_connector.update(id, {
            "doc": {
                "events": events,
                "impact_data": impact_data
            }
        })
        return res

    # Get session events results
    def get_session_results(self, id):
        my_connector = Es_connector(index=self.sessions_index, doc_type=self.sessions_doc_type)
        res = my_connector.get(id)
        return res

    # Delete session by name
    def delete_session(self, id):
        session_connector = Es_connector(index=self.sessions_index, doc_type=self.sessions_doc_type)
        session = session_connector.get(id)
        if session:
            print("delete Session")
            # print(session)
            # 1. Delete session data from the tweets
            tweets_connector = Es_connector(index=session['_source']['s_index'], doc_type=session['_source']['s_type'])
            session_name = 'session_' + session['_source']['s_name']
            print(session_name)
            tweets_connector.remove_field_all(session_name)
            # 2. Delete the session
            session_connector.delete(id)
            return True
        else:
            return False

    # ==================================================================
    # Tweets session status
    # ==================================================================

    # Set tweets status
    def set_all_status(self, index, session, status):
        tweets_connector = Es_connector(index=index, doc_type="tweet")
        res = tweets_connector.update_all(session, status)
        return res

    def set_status(self, index, session, data):
        tweets_connector = Es_connector(index=index, doc_type="tweet")
        # All tweets
        event = json.loads(data['event'])
        # print("------------------------")
        # print(data)
        # print("------------------------")
        # print(event)
        # print(event['main_term'])
        terms = []
        words = event['main_term'] + ' '
        for t in event['related_terms']:
            terms.append({"match": {
                "text": {
                    "query": t['word'],
                    "boost": t['value']
                }
            }})
            words += t['word'] + " "
        terms.append({"match": {
            "text": {
                "query": event['main_term'],
                "boost": 2
            }
        }})
        # query = {
        #     "query": {
        #         "bool": {
        #             "should": terms
        #         }
        #     }
        # }

        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "bool": {
                                "should": terms
                            }
                        }
                    ],
                    "filter": {
                        "bool": {
                            "should": [
                                {
                                    "match": {
                                        session: "proposed"
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        }

        # print(query)
        res = tweets_connector.update_query(query, session, data['status'])
        # Event related

        return res

    def mark_unlabeled_tweets(self, index, session, state, word):
        tweets_connector = Es_connector(index=index, doc_type="tweet")
        query = {
            "query": {
                "bool": {
                    "must": {
                        "simple_query_string": {
                            "fields": [
                                "text"
                            ],
                            "query": word
                        }
                    },
                    "filter": {
                        "bool": {
                            "should": [
                                {
                                    "match": {
                                        session: "proposed"
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        }
        res = tweets_connector.update_query(query, session, state)
        return res

    def mark_all_matching_tweets(self, index, session, state, word):
        tweets_connector = Es_connector(index=index, doc_type="tweet")
        query = {
            "query": {
                "bool": {
                    "must": {
                        "simple_query_string": {
                            "fields": [
                                "text"
                            ],
                            "query": word
                        }
                    }
                }
            }
        }
        return tweets_connector.update_query(query, session, state)

    def set_cluster_state(self, index, session, cid, state):
        tweets_connector = Es_connector(index=index, doc_type="tweet")
        # All tweets
        query = {
            "query": {
                "term": {"imagesCluster": cid}
            }
        }
        res = tweets_connector.update_query(query, session, state)
        return res

    def set_tweet_state(self, index, session, tid, val):
        tweets_connector = Es_connector(index=index, doc_type="tweet")

        query = {
            "doc": {
                session: val
            }
        }
        res = tweets_connector.update(tid, query)
        return res

    def export_event(self, index, session):
        my_connector = Es_connector(index=index)
        res = my_connector.bigSearch(
            {
                "_source": {
                    "excludes": ["session_*"]
                },
                "query": {
                    "term": {
                        "session_" + session: "confirmed"
                    }
                }
            })
        return res

    # ==================================================================
    # Beta
    # ==================================================================

    def get_event_tweets_count(self, index="test3", main_term="", related_terms=""):
        my_connector = Es_connector(index=index)
        terms = []
        words = main_term + ' '
        for t in related_terms:
            terms.append({"match": {
                "text": {
                    "query": t['word'],
                    "boost": t['value']
                }
            }})
            words += t['word'] + " "
        terms.append({"match": {
            "text": {
                "query": main_term,
                "boost": 2
            }
        }})
        query = {
            "query": {
                "bool": {
                    "should": terms
                }
            }
        }
        res = my_connector.count(query)
        return res['count']

    def get_event_state_tweets_count(self, index="test3", session="", words="", state="confirmed"):
        my_connector = Es_connector(index=index)
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "text": {
                                    "query": words
                                }
                            }
                        }
                    ],
                    "filter": {
                        "bool": {
                            "should": [
                                {
                                    "match": {
                                        "session_" + session: state
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        }
        res = my_connector.count(query)
        return res['count']

    def get_words_tweets_count(self, index="test3", session="", words=""):
        my_connector = Es_connector(index=index)
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "text": {
                                    "query": words
                                }
                            }
                        }
                    ]
                }
            }
        }
        res = my_connector.count(query)
        return res['count']

    def get_all_count(self, index="test3"):
        my_connector = Es_connector(index=index)
        query = {
            "query": {
                "match_all": {}
            }
        }
        res = my_connector.count(query)
        return res['count']

    def get_words_count(self, index="test3", words=""):
        my_connector = Es_connector(index=index)
        query = {
            "query": {
                "simple_query_string": {
                    "fields": [
                        "text"
                    ],
                    "query": words
                }
            }
        }
        res = my_connector.count(query)
        return res['count']

    def get_start_date(self, index):
        my_connector = Es_connector(index=index)
        res = my_connector.search_size({
            "_source": [
                "@timestamp",
                "timestamp_ms"
            ],
            "query": {
                "match_all": {}
            },
            "sort": [
                {
                    "@timestamp": {
                        "order": "asc"
                    }
                }
            ]
        }, 1)
        return res['hits']['hits'][0]['_source']

    def get_end_date(self, index):
        my_connector = Es_connector(index=index)
        res = my_connector.search_size({
            "_source": [
                "@timestamp",
                "timestamp_ms"
            ],
            "query": {
                "match_all": {}
            },
            "sort": [
                {
                    "@timestamp": {
                        "order": "desc"
                    }
                }
            ]
        }, 1)
        return res['hits']['hits'][0]['_source']

    def get_range_count(self, index, start, end):
        my_connector = Es_connector(index=index)
        query = {
            "query": {
                "range": {
                    "timestamp_ms": {
                        "gt": str(start),
                        "lt": str(end)
                    }
                }
            }
        }
        print(query)
        res = my_connector.count(query)
        return res['count']

    def process_range_tweets(self, index, start, end, words, count):
        sw = 'stopwords/twitter_all.txt'
        my_connector = Es_connector(index=index)
        res = my_connector.range_tweets(start, end, sw, words, count)
        return res

    def process_w2v_tweets(self, index, words, count):
        sw = 'stopwords/twitter_all.txt'
        my_connector = Es_connector(index=index)
        res = my_connector.w2v_tweets(sw, words, count)
        return res

    def get_event_central_tweets(self, index="test3", main_term="", related_terms=""):
        my_connector = Es_connector(index=index)
        terms = []
        words = main_term + ' '
        for t in related_terms:
            terms.append({"match": {
                "text": {
                    "query": t['word'],
                    "boost": t['value']
                }
            }})
            words += t['word'] + " "
        terms.append({"match": {
            "text": {
                "query": main_term,
                "boost": 2
            }
        }})
        query = {
            "sort": [
                "_score"
            ],
            "query": {
                "bool": {
                    "should": terms
                }
            }
        }
        res = my_connector.search_size(query, 1)
        return res

    def get_event_tweets_bigsearch(self, index="test3", main_term="", related_terms=""):
        my_connector = Es_connector(index=index)
        terms = []
        words = main_term + ' '
        for t in related_terms:
            terms.append({"match": {
                "text": {
                    "query": t['word'],
                    "boost": t['value']
                }
            }})
            words += t['word'] + " "
        terms.append({"match": {
            "text": {
                "query": main_term,
                "boost": 2
            }
        }})
        query = {
            "sort": [
                "_score"
            ],
            "query": {
                "bool": {
                    "should": terms
                }
            }
        }

        res = my_connector.bigTweetTextSearch(query)
        return res

    def getMean(self, index="test3", main_term="", related_terms=""):
        my_connector = Es_connector(index=index)
        terms = []
        words = main_term + ' '
        for t in related_terms:
            terms.append({"match": {
                "text": {
                    "query": t['word'],
                    "boost": t['value']
                }
            }})
            words += t['word'] + " "
        terms.append({"match": {
            "text": {
                "query": main_term,
                "boost": 2
            }
        }})
        query = {
            "sort": [
                "_score"
            ],
            "_source": [
                "_score"
            ],
            "query": {
                "bool": {
                    "should": terms
                }
            }
        }

        query = {
            "size": 0,
            "query": {
                "bool": {
                    "should": terms
                }
            },
            "aggs": {
                "sum_scores": {
                    "sum": {
                        "script": "_score"
                    }
                }
            }
        }
        res = my_connector.search(query)
        total = res['hits']['total']
        sum = res['aggregations']['sum_scores']['value']
        mean = sum / total
        # res = my_connector.bigSearchMean(query)
        return mean

    def getSSE(self, index="test3", main_term="", related_terms="", mean=0):
        my_connector = Es_connector(index=index)
        terms = []
        words = main_term + ' '
        for t in related_terms:
            terms.append({"match": {
                "text": {
                    "query": t['word'],
                    "boost": t['value']
                }
            }})
            words += t['word'] + " "
        terms.append({"match": {
            "text": {
                "query": main_term,
                "boost": 2
            }
        }})
        query = {
            "sort": [
                "_score"
            ],
            "query": {
                "bool": {
                    "should": terms
                }
            }
        }

        res = my_connector.bigSearchSSE(query, mean)
        return res

    def d2v(self, tweet, data):
        # data = ["I love machine learning. Its awesome.",
        #         "I love coding in python",
        #         "I love building chatbots python",
        #         "they chat amagingly well",
        #         "So we have saved the model and its ready for implementation. Lets play with it"]
        print("=============================================================")
        print("=============================================================")
        print(tweet)
        print("-------------")
        print("-------------")

        tagged_data = [TaggedDocument(words=word_tokenize(_d.lower()), tags=[str(i)]) for i, _d in enumerate(data)]

        max_epochs = 100
        vec_size = 20
        alpha = 0.025

        model = Doc2Vec(vector_size=vec_size,
                        alpha=alpha,
                        min_alpha=0.00025,
                        min_count=1,
                        dm=1)

        model.build_vocab(tagged_data)

        for epoch in range(max_epochs):
            # print('iteration {0}'.format(epoch))
            model.train(tagged_data,
                        total_examples=model.corpus_count,
                        epochs=model.iter)
            # decrease the learning rate
            model.alpha -= 0.0002
            # fix the learning rate, no decay
            model.min_alpha = model.alpha

        # test_data = word_tokenize("So we have saved the model and its ready for implementation. Lets play with it".lower())
        test_data = word_tokenize(tweet.lower())
        v1 = model.infer_vector(test_data)
        # print("V1_infer", v1)

        # to find most similar doc using tags
        similar_doc = model.docvecs.most_similar([v1])
        print("similar_docs:")
        print("-------------")
        # print(similar_doc)
        for doc in similar_doc:
            print(data[int(doc[0])])
            # print(doc[1])

        print("=============================================================")
        print("=============================================================")

        # to find vector of doc in training data using tags or in other words, printing the vector of document at index 1 in training data
        # print(model.docvecs['1'])
