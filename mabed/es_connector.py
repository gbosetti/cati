# coding: utf-8
import json
import time
from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
import os
import gensim
import mabed.utils as utils
import string
import re
from elasticsearch_dsl import UpdateByQuery
from pathlib import Path

__author__ = "Firas Odeh"
__email__ = "odehfiras@gmail.com"



class Es_connector:
    def __init__(self, host='', port='', user='', password='', timeout='', index='', doc_type='', protocol='http', config_relative_path=''):

        with open(config_relative_path + 'config.json', 'r') as f:
            config = json.load(f)

        default_source = config['default']['index']
        sessions_source = config['default']['sessions_index']['index']
        session_host = config['default']['sessions_index']['host']
        session_port = config['default']['sessions_index']['port']
        session_user = config['default']['sessions_index']['user']
        session_password = config['default']['sessions_index']['password']
        session_timeout = config['default']['sessions_index']['timeout']
        session_index = config['default']['sessions_index']['index']
        session_doc_type = config['default']['sessions_index']['doc_type']

        default_index = None
        for source in config['elastic_search_sources']:
            if source['index'] == default_source:
                default_host = source['host']
                default_port = source['port']
                default_user = source['user']
                default_password = source['password']
                default_timeout = source['timeout']
                default_index = source['index']
                default_doc_type = source['doc_type']

        available = False
        if default_index != None and index == default_index:
            # Define config
            self.host = default_host
            self.port = default_port
            self.user = default_user
            self.password = default_password
            self.timeout = default_timeout
            self.index = default_index
            self.doc_type = default_doc_type
            available = True
        elif index == sessions_source:
            self.host = session_host
            self.port = session_port
            self.user = session_user
            self.password = session_password
            self.timeout = session_timeout
            self.index = session_index
            self.doc_type = session_doc_type
            available = True

        else:
            for es_source in config['elastic_search_sources']:
                if es_source['index'] == index:
                    # Define config
                    self.host = es_source['host']
                    self.port = es_source['port']
                    self.user = es_source['user']
                    self.password = es_source['password']
                    self.timeout = es_source['timeout']
                    self.index = es_source['index']
                    self.doc_type = es_source['doc_type']
                    available = True
        if not available:
            # We can just throw an error instead
            # Or have elastic search throw it
            print("Index ", index, " not found")
            raise Exception('The "' + index + '" index is not available, please check that it is defined in the config.json file and try again.')

        self.size = 500
        self.body = {"query": {"match_all": {}}}
        self.protocol = protocol
        self.result = []

        # Init Elasticsearch instance
        self.es = Elasticsearch(
            [self.host],
            http_auth=(self.user, self.password),
            port=self.port,
            timeout=self.timeout,
            # TODO: use SSL
            use_ssl=False
        )
        self.ic = IndicesClient(self.es)

    # def search(self, query):
    #     res = self.es.search(
    #         index=self.index,
    #         doc_type=self.doc_type,
    #         body={"query": query},
    #         size=self.size,
    #     )
    #     if res['hits']['total']>0:
    #         print("Got %d Hits:" % res['hits']['total'])
    #     return res

    def search(self, query, size=None):

        target_size = self.size
        if size != None:
            target_size = size

        res = self.es.search(
            index=self.index,
            doc_type=self.doc_type,
            body=query,
            size=target_size,
        )
        return res

    def search_size(self, query, size=500):
        res = self.es.search(
            index=self.index,
            doc_type=self.doc_type,
            body=query,
            size=size,
        )
        return res

    def count(self, query):
        res = self.es.count(
            index=self.index,
            doc_type=self.doc_type,
            body=query
        )
        return res

    def post(self, query):
        res = self.es.index(
            index=self.index,
            doc_type=self.doc_type,
            body=query
        )
        return res

    def update_field(self,id, field, value):
        res = self.es.update(
            index=self.index,
            doc_type=self.doc_type,
            id=id,
            body={"doc": {
                field: value
            }}
        )
        if res['result'] == "updated":
            return res
        else:
            return False

    def update(self,id, query):

        res = self.es.update(
            index=self.index,
            doc_type=self.doc_type,
            id=id,
            body=query
        )
        if res['result'] == "updated":
            return res
        else:
            return False

    def delete(self, id):

        try:
            res = self.es.delete(index=self.index,
                doc_type=self.doc_type,
                id=id)
            if res['result'] == "deleted":
                return res
            else:
                return False
        except Exception as err:
            print("Error: ", err)
            return False

    def get(self, id):

        res = self.es.get(index=self.index,
            doc_type=self.doc_type,
            id=id)
        if res['found'] == True:
            # print(res)
            return res
        else:
            return False


    def bigSearch(self, query):
        res = []
        # Process hits here
        def process_hits(hits, results):
            for item in hits:
                results.append(item)
            return results

        # Check index exists
        if not self.es.indices.exists(index=self.index):
            # print("Index " + self.index + " not exists")
            exit()

        # Init scroll by search
        data = self.es.search(
            index=self.index,
            doc_type=self.doc_type,
            scroll='15m',
            size=self.size,
            body=query,
        )

        # Get the scroll ID
        sid = data['_scroll_id']
        scroll_size = len(data['hits']['hits'])

        # Before scroll, process current batch of hits
        res = process_hits(data['hits']['hits'], res)

        while scroll_size > 0:
            "Scrolling..."
            data = self.es.scroll(scroll_id=sid, scroll='15m')

            # Process current batch of hits
            res = process_hits(data['hits']['hits'], res)

            # Update the scroll ID
            sid = data['_scroll_id']

            # Get the number of results that returned in the last scroll
            scroll_size = len(data['hits']['hits'])

        return res


    def init_paginatedSearch(self, query, size=None):
        res = []
        # Process hits here
        def process_hits(hits, results):
            for item in hits:
                results.append(item)
            return results

        # Check index exists
        if not self.es.indices.exists(index=self.index):
            # print("Index " + self.index + " not exists")
            exit()

        if size != None:
            target_size = size
        else: target_size = self.size

        # Init scroll by search
        data = self.es.search(
            index=self.index,
            doc_type=self.doc_type,
            scroll='15m',
            size=target_size,
            body=query,
        )

        # Get the scroll ID
        sid = data['_scroll_id']
        scroll_size = len(data['hits']['hits'])

        # Before scroll, process current batch of hits
        res = process_hits(data['hits']['hits'], res)
        total = data['hits']['total']
        # scroll_size = total - scroll_size

        return {"results":res, "sid":sid, "scroll_size":scroll_size, "total":total}


    def loop_paginatedSearch(self, sid, scroll_size):
        res = []
        # Process hits here
        def process_hits(hits, results):
            for item in hits:
                results.append(item)
            return results

        if scroll_size > 0:
            data = self.es.scroll(scroll_id=sid, scroll='15m')
            # Process current batch of hits
            res = process_hits(data['hits']['hits'], res)
            # Update the scroll ID
            sid = data['_scroll_id']
            # Get the number of results that returned in the last scroll
            scroll_size = len(data['hits']['hits'])

        return {"results": res, "sid": sid, "scroll_size": scroll_size}


    def getTweets(self):
        # Process hits here
        def process_hits(hits):
            for item in hits:
                self.result.append(item)

        # Check index exists
        if not self.es.indices.exists(index=self.index):
            # print("Index " + self.index + " not exists")
            exit()

        body = self.body
        body = {"_source": ["text", "timestamp_ms", "imagesCluster"],"query": {"match_all": {}}}

        # Init scroll by search
        data = self.es.search(
            index=self.index,
            doc_type=self.doc_type,
            scroll='15m',
            size=self.size,
            body=body
        )

        # Get the scroll ID
        sid = data['_scroll_id']
        scroll_size = len(data['hits']['hits'])

        # Before scroll, process current batch of hits
        process_hits(data['hits']['hits'])

        while scroll_size > 0:
            "Scrolling..."
            data = self.es.scroll(scroll_id=sid, scroll='15m')

            # Process current batch of hits
            process_hits(data['hits']['hits'])

            # Update the scroll ID
            sid = data['_scroll_id']

            # Get the number of results that returned in the last scroll
            scroll_size = len(data['hits']['hits'])

        text = self.result[0]['_source']['text']
        date = self.result[0]['_source']['timestamp_ms']
        return self.result

    def getFilteredTweets(self, session, status):
        # Process hits here
        def process_hits(hits):
            for item in hits:
                self.result.append(item)

        # Check index exists
        if not self.es.indices.exists(index=self.index):
            # print("Index " + self.index + " not exists")
            exit()

        session ='session_'+session
        body = self.body
        body = {"_source": ["text", "timestamp_ms", "imagesCluster"],"query": {
            "terms": {
              session: status
            }
          }}

        # Init scroll by search
        data = self.es.search(
            index=self.index,
            doc_type=self.doc_type,
            scroll='15m',
            size=self.size,
            body=body
        )

        # Get the scroll ID
        sid = data['_scroll_id']
        scroll_size = len(data['hits']['hits'])

        # Before scroll, process current batch of hits
        process_hits(data['hits']['hits'])

        while scroll_size > 0:
            "Scrolling..."
            data = self.es.scroll(scroll_id=sid, scroll='15m')

            # Process current batch of hits
            process_hits(data['hits']['hits'])

            # Update the scroll ID
            sid = data['_scroll_id']

            # Get the number of results that returned in the last scroll
            scroll_size = len(data['hits']['hits'])

        # text = self.result[0]['_source']['text']
        # date = self.result[0]['_source']['timestamp_ms']
        return self.result

    def update_by_query(self, query, script_source):

        try:
            self.fix_read_only_allow_delete()
            ubq = UpdateByQuery(using=self.es, index=self.index).update_from_dict(query).script(source=script_source)
            ubq.execute()

        except Exception as err:
            print("Error: ", err)
            return False

        return True

    def fix_read_only_allow_delete(self):

        self.es.indices.put_settings(index=self.index, body={
            "index": {
                "blocks": {
                    "read_only_allow_delete": "false"
                }
            }
        })

    def update_all(self, field, value, **kwargs):
        # Process hits here
        # def process_hits(hits):
        #     for item in hits:
        #         self.update_field(item['_id'], field, value)

        logger = kwargs.get("logger", None)

        # Check index exists
        if not self.es.indices.exists(index=self.index):
            # print("Index " + self.index + " not exists")
            exit()

        ubq = UpdateByQuery(using=self.es, index=self.index).update_from_dict({"query": {"match_all": {}}}).script(
            source="ctx._source." + field + " = '" + value + "'")
        response = ubq.execute()

        # # Init scroll by search
        # data = self.es.search(
        #     index=self.index,
        #     doc_type=self.doc_type,
        #     scroll='15m',
        #     size=self.size,
        #     body=self.body
        # )
        #
        # # Get the scroll ID
        # sid = data['_scroll_id']
        # scroll_size = len(data['hits']['hits'])
        #
        # # Before scroll, process current batch of hits
        # # print(data['hits']['total'])
        # process_hits(data['hits']['hits'])
        # processed_docs = 0
        #
        # while scroll_size > 0:
        #
        #     data = self.es.scroll(scroll_id=sid, scroll='15m')
        #
        #     # Process current batch of hits
        #     process_hits(data['hits']['hits'])
        #
        #     # Update the scroll ID
        #     sid = data['_scroll_id']
        #
        #     # Get the number of results that returned in the last scroll
        #     scroll_size = len(data['hits']['hits'])
        #
        #     if (logger):
        #         processed_docs += scroll_size
        #         logger.add_log("Scrolling " + str(round(processed_docs * 100 / data['hits']['total'],2)) + "% documents")
        return True

    def update_query(self, query, field, value):
        # Process hits here
        def process_hits(hits):
            for item in hits:
                self.update_field(item['_id'], field, value)

        # Check index exists
        if not self.es.indices.exists(index=self.index):
            # print("Index " + self.index + " not exists")
            exit()

        # Init scroll by search
        data = self.es.search(
            index=self.index,
            doc_type=self.doc_type,
            scroll='15m',
            size=self.size,
            body=query
        )

        # Get the scroll ID
        sid = data['_scroll_id']
        scroll_size = len(data['hits']['hits'])

        # Before scroll, process current batch of hits
        # print(data['hits']['total'])
        process_hits(data['hits']['hits'])

        while scroll_size > 0:
            "Scrolling..."
            data = self.es.scroll(scroll_id=sid, scroll='15m')

            # Process current batch of hits
            process_hits(data['hits']['hits'])

            # Update the scroll ID
            sid = data['_scroll_id']

            # Get the number of results that returned in the last scroll
            scroll_size = len(data['hits']['hits'])
        return True

    def remove_field_all(self, field):
        # Process hits here
        def process_hits(hits):
            for item in hits:
                item['_source'].pop(field, None)
                up = self.update(item['_id'], {"script" : "ctx._source.remove(\""+field+"\")"})
                # print(item['_id'])
                # print(up)

        # Check index exists
        if not self.es.indices.exists(index=self.index):
            # print("Index " + self.index + " not exists")
            return False

        # Init scroll by search
        data = self.es.search(
            index=self.index,
            doc_type=self.doc_type,
            scroll='15m',
            size=self.size,
            body=self.body
        )

        # Get the scroll ID
        sid = data['_scroll_id']
        scroll_size = len(data['hits']['hits'])

        # Before scroll, process current batch of hits
        # print(data['hits']['total'])
        process_hits(data['hits']['hits'])

        while scroll_size > 0:
            "Scrolling..."
            data = self.es.scroll(scroll_id=sid, scroll='15m')

            # Process current batch of hits
            process_hits(data['hits']['hits'])

            # Update the scroll ID
            sid = data['_scroll_id']

            # Get the number of results that returned in the last scroll
            scroll_size = len(data['hits']['hits'])
        return True


    def initMABED(self):
        # Process hits here
        def process_hits(hits):
            for item in hits:
                self.result.append(item)

        # Check index exists
        if not self.es.indices.exists(index=self.index):
            # print("Index " + self.index + " not exists")
            exit()

        body = self.body
        body = {"_source": ["text", "timestamp_ms", "imagesCluster"], "query": {"match_all": {}}}

        # Init scroll by search
        data = self.es.search(
            index=self.index,
            doc_type=self.doc_type,
            scroll='15m',
            size=self.size,
            body=body
        )

        # Get the scroll ID
        sid = data['_scroll_id']
        scroll_size = len(data['hits']['hits'])

        # Before scroll, process current batch of hits
        process_hits(data['hits']['hits'])

        while scroll_size > 0:
            "Scrolling..."
            data = self.es.scroll(scroll_id=sid, scroll='15m')

            # Process current batch of hits
            process_hits(data['hits']['hits'])

            # Update the scroll ID
            sid = data['_scroll_id']

            # Get the number of results that returned in the last scroll
            scroll_size = len(data['hits']['hits'])

        text = self.result[0]['_source']['text']
        date = self.result[0]['_source']['timestamp_ms']
        return self.result


    def tokenize(self, text, stopwords):
        # split the documents into tokens based on whitespaces

        raw_tokens = text.lower().replace("...","").replace("…","").replace("..", "").split()
        # trim punctuation and convert to lower case
        return [token.strip(string.punctuation) for token in raw_tokens if len(token) > 3 and token not in stopwords and 'http' not in token and 'cluster' not in token and re.search('[a-zA-Z]', token)]

    def range_tweets(self, start, end, stopwords_file_path, words, count):
        # Process hits here
        tweets = []
        # load stop-words
        stopwords = utils.load_stopwords(stopwords_file_path)
        # print(stopwords)

        def process_hits(hits, stopwords):
            t = []
            for item in hits:
                # tweet = item['_source']['text'].encode('utf-8', 'ignore').decode('utf-8')
                tweet = item['_source']['text']
                tokenized_tweet = self.tokenize(tweet, stopwords)
                # print(tokenized_tweet)
                t.append(tokenized_tweet)
            return t

        # Check index exists
        if not self.es.indices.exists(index=self.index):
            print("Index " + self.index + " not exists")
            exit()

        body = {
            "query": {
                "bool": {
                    "should": {
                        "match": {
                            "text": {
                                "query": words
                            }
                        }
                    },
                    "filter": {
                        "range": {
                            "@timestamp": {
                                "gt": str(start),
                                "lt": str(end)
                            }
                        }
                    }
                }
            }
        }
        # Init scroll by search

        # filepath = "models/" + str(hash(words)).replace("-", "") + ".model"
        filepath = "models/" + words.replace(" ", "").replace(",", "") + ".model"
        modelfile = Path(filepath)
        if modelfile.is_file():
            model = gensim.models.Word2Vec.load(filepath)
        else:
            data = self.es.search(
                index=self.index,
                doc_type=self.doc_type,
                scroll='2m',
                size=self.size,
                body=body
            )

            # Get the scroll ID
            sid = data['_scroll_id']
            scroll_size = len(data['hits']['hits'])

            # Before scroll, process current batch of hits
            tweets = process_hits(data['hits']['hits'], stopwords)

            while scroll_size > 0:
                "Scrolling..."
                data = self.es.scroll(scroll_id=sid, scroll='2m')

                # Process current batch of hits
                tweets = tweets + process_hits(data['hits']['hits'], stopwords)

                # Update the scroll ID
                sid = data['_scroll_id']

                # Get the number of results that returned in the last scroll
                scroll_size = len(data['hits']['hits'])

            # print(texts[0])
            # tokenized_sentences = [nltk.word_tokenize(sentence) for sentence in tweets]
            # tweets = tweets + ['lyon']


            model = gensim.models.Word2Vec(tweets, min_count=1, workers=1, negative=20)
            model.save(os.path.abspath(filepath))

        words = self.tokenize(words, stopwords)
        pwords=words
        # context = model.most_similar(positive=['fête','lumières'], topn=10)
        context = model.most_similar(positive=pwords, topn=count)
        # context = model.most_similar(positive=['fête','lumières'], topn=count)
        # context = model.most_similar_cosmul(positive=pwords, topn=5)
        # context = model.similar_by_word(word='lyon', topn=5)


        # context = model.similar_by_vector(vector=['lyon','fdl','fdl2017'], topn=5)

        return context

    # =======================================================
    # =======================================================

    def bigTweetTextSearch(self, query):
        res = []
        # Process hits here
        def process_hits(hits, results):
            for item in hits:
                results.append(item['_source']['text'])
            return results

        # Check index exists
        if not self.es.indices.exists(index=self.index):
            # print("Index " + self.index + " not exists")
            exit()

        # Init scroll by search
        data = self.es.search(
            index=self.index,
            doc_type=self.doc_type,
            scroll='15m',
            size=self.size,
            body=query,
        )

        # Get the scroll ID
        sid = data['_scroll_id']
        scroll_size = len(data['hits']['hits'])

        # Before scroll, process current batch of hits
        res = process_hits(data['hits']['hits'], res)

        while scroll_size > 0:
            "Scrolling..."
            data = self.es.scroll(scroll_id=sid, scroll='15m')

            # Process current batch of hits
            res = process_hits(data['hits']['hits'], res)

            # Update the scroll ID
            sid = data['_scroll_id']

            # Get the number of results that returned in the last scroll
            scroll_size = len(data['hits']['hits'])

        return res

    def bigSearchMean(self, query):
        res = []
        count = 0
        scoreSum = 0
        # Process hits here
        def process_hits(hits, scoreSum):
            for item in hits:
                scoreSum = scoreSum + item['_score']
            return scoreSum

        # Check index exists
        if not self.es.indices.exists(index=self.index):
            # print("Index " + self.index + " not exists")
            exit()

        # Init scroll by search
        data = self.es.search(
            index=self.index,
            doc_type=self.doc_type,
            scroll='15m',
            size=self.size,
            body=query,
        )

        # Get the scroll ID
        sid = data['_scroll_id']
        scroll_size = len(data['hits']['hits'])

        # Before scroll, process current batch of hits
        scoreSum = process_hits(data['hits']['hits'], scoreSum)
        count = count + len(data['hits']['hits'])

        while scroll_size > 0:
            "Scrolling..."
            data = self.es.scroll(scroll_id=sid, scroll='15m')

            # Process current batch of hits
            scoreSum = process_hits(data['hits']['hits'], scoreSum)
            count = count + len(data['hits']['hits'])

            # Update the scroll ID
            sid = data['_scroll_id']

            # Get the number of results that returned in the last scroll
            scroll_size = len(data['hits']['hits'])

        mean = scoreSum / count
        return mean

    def bigSearchSSE(self, query, mean):
        sse = 0
        # Process hits here
        def process_hits(hits, sse):
            for item in hits:
                sse = (item['_score'] - mean) ** 2
            return sse

        # Check index exists
        if not self.es.indices.exists(index=self.index):
            # print("Index " + self.index + " not exists")
            exit()

        # Init scroll by search
        data = self.es.search(
            index=self.index,
            doc_type=self.doc_type,
            scroll='15m',
            size=self.size,
            body=query,
        )

        # Get the scroll ID
        sid = data['_scroll_id']
        scroll_size = len(data['hits']['hits'])

        # Before scroll, process current batch of hits
        sse = process_hits(data['hits']['hits'], sse)

        while scroll_size > 0:
            "Scrolling..."
            data = self.es.scroll(scroll_id=sid, scroll='15m')

            # Process current batch of hits
            sse = process_hits(data['hits']['hits'], sse)

            # Update the scroll ID
            sid = data['_scroll_id']

            # Get the number of results that returned in the last scroll
            scroll_size = len(data['hits']['hits'])

        return sse

    def w2v_tweets(self, stopwords_file_path, words, count):
        # Process hits here
        tweets = []
        # load stop-words
        stopwords = utils.load_stopwords(stopwords_file_path)

        # print(stopwords)

        def process_hits(hits, stopwords):
            t = []
            for item in hits:
                # tweet = item['_source']['text'].encode('utf-8', 'ignore').decode('utf-8')
                tweet = item['_source']['text']
                tokenized_tweet = self.tokenize(tweet, stopwords)
                # print(tokenized_tweet)
                t.append(tokenized_tweet)
            return t

        # Check index exists
        if not self.es.indices.exists(index=self.index):
            print("Index " + self.index + " not exists")
            exit()

        body = {
            "query": {
                "bool": {
                    "should": {
                        "match": {
                            "text": {
                                "query": words
                            }
                        }
                    }
                }
            }
        }

        # Init scroll by search

        # filepath = "models/" + str(hash(words)).replace("-", "") + ".model"
        filepath = "models/" + words.replace(" ", "").replace(",", "") + ".model"
        modelfile = Path(filepath)
        if modelfile.is_file():
            model = gensim.models.Word2Vec.load(filepath)
        else:
            data = self.es.search(
                index=self.index,
                doc_type=self.doc_type,
                scroll='2m',
                size=self.size,
                body=body
            )

            # Get the scroll ID
            sid = data['_scroll_id']
            scroll_size = len(data['hits']['hits'])

            # Before scroll, process current batch of hits
            tweets = process_hits(data['hits']['hits'], stopwords)

            while scroll_size > 0:
                "Scrolling..."
                data = self.es.scroll(scroll_id=sid, scroll='2m')

                # Process current batch of hits
                tweets = tweets + process_hits(data['hits']['hits'], stopwords)

                # Update the scroll ID
                sid = data['_scroll_id']

                # Get the number of results that returned in the last scroll
                scroll_size = len(data['hits']['hits'])

            # print(texts[0])
            # tokenized_sentences = [nltk.word_tokenize(sentence) for sentence in tweets]
            # tweets = tweets + ['lyon']


            model = gensim.models.Word2Vec(tweets, min_count=1, workers=10, negative=20)
            model.save(filepath)

        words = self.tokenize(words, stopwords)
        pwords = words
        # context = model.most_similar(positive=['fête','lumières'], topn=10)
        context = model.most_similar(positive=pwords, topn=count)
        # context = model.most_similar(positive=['fête','lumières'], topn=count)
        # context = model.most_similar_cosmul(positive=pwords, topn=5)
        # context = model.similar_by_word(word='lyon', topn=5)


        # context = model.similar_by_vector(vector=['lyon','fdl','fdl2017'], topn=5)

        return context

    def field_exists(self, field):
        res = self.ic.get_field_mapping(
            index=self.index,
            doc_type=self.doc_type,
            fields=[field]
        )
        return len(res[(next(iter(res)))]['mappings'])  > 0

    def field_values(self,field, size=10):
        body = {
            "aggs": {
                "field_values": {
                    "terms": {
                        "field": field,
                        "size": size
                    }
                }
            }
        }
        data = self.es.search(
            index=self.index,
            doc_type=self.doc_type,
            size=0,
            body=body
        )
        return data["aggregations"]["field_values"]["buckets"]
