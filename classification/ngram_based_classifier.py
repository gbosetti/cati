import string
import nltk
from nltk.corpus import stopwords
nltk.download('stopwords')
from collections import Counter
from mabed.es_connector import Es_connector


class NgramBasedClasifier:

    def __init__(self):
        self.logs = []

    def get_n_grams(self, text, length=2):
        n_grams = zip(*[text[i:] for i in range(length)])
        # n_grams = list(nltk.bigrams(text))
        return n_grams

    def remove_stop_words(self, full_text, langs=["en", "fr", "es"]):

        punctuation = list(string.punctuation + "…" + "..." + "’" + "️" + "'" + '🔴' + '•')
        multilang_stopwords = self.get_stopwords_for_langs(langs) + ["Ã", "RT"] + punctuation
        tokenized_text = nltk.word_tokenize(full_text)
        filtered_words = list(filter(lambda word: word not in multilang_stopwords, tokenized_text))
        full_text = " ".join(filtered_words)
        return full_text

    def bigrams_with_higher_ocurrence(self, tweets, **kwargs ):  # remove_stopwords=True, stemming=True):

        length = kwargs.get('length', 2)
        top_ngrams_to_retrieve = kwargs.get('top_ngrams_to_retrieve', 2)
        min_occurrences = kwargs.get('min_occurrences', 20)

        try:
            full_bigrams = {}
            res = tweets["hits"]["hits"]
            for tweet in res:
                clean_text = self.remove_stop_words(tweet["_source"]["text"]).split()
                bigrams = Counter(self.get_n_grams(clean_text, length)).most_common(None) #We don't filter at this point but at the end

                # print("N-grams", bigrams)

                for k, v in bigrams:

                    ngram_text=""
                    for term in k:
                        ngram_text = ngram_text + term + " "
                    ngram_text = ngram_text.strip()
                    # print("N-gram: ", ngram_text, " - ", k)

                    try:
                        full_bigrams[ngram_text].append(tweet["_id"])  # .add for {}
                    except KeyError:  # If the collection doesn't have the entry yet
                        full_bigrams[ngram_text] = [tweet["_id"]]  # Use an array otherwise it will be expensive to convert to json

            return {k: full_bigrams[k] for k in full_bigrams if len(full_bigrams[k]) > min_occurrences}  # Removing bigrams with a low ocurrence (associated num of tweets)

        except Exception as e:
            print('Error: ' + str(e))


    def gerenate_ngrams_for_tweets(self, tweets, **kwargs ):  # remove_stopwords=True, stemming=True):

        length = int(kwargs.get('length', 2))
        top_ngrams_to_retrieve = kwargs.get('top_ngrams_to_retrieve', 2)
        min_occurrences = kwargs.get('min_occurrences', 20)

        for tweet in tweets:
            try:
                clean_text = self.remove_stop_words(tweet["_source"]["text"]).split()
                ngrams = list(self.get_n_grams(clean_text, length))
                # print("     N-grams:", bigrams)
                ngrams_as_text = self.get_ngrams_as_plain_text(ngrams)
                self.updatePropertyValue(tweet=tweet, property_name=kwargs["prop"], property_value=ngrams_as_text, index=kwargs["index"])

            except Exception as e:
                print('Error: ' + str(e))


    def get_ngrams_as_plain_text(self, ngrams):

        full_ngrams_text = ""
        for ngram in ngrams:
            single_ngram_text = ""
            for term in ngram:
                single_ngram_text = single_ngram_text + term + "-"

            single_ngram_text = single_ngram_text[:-1]
            full_ngrams_text = full_ngrams_text + single_ngram_text + " "

        full_ngrams_text.strip()

        return full_ngrams_text
        #
        # for k, v in ngrams:
        #
        #     ngram_text = ""
        #     for term in k:
        #         ngram_text = ngram_text + term + "-"
        #     ngram_text = ngram_text.strip()
        #
        # return ngram_text


    def generate_ngrams_for_index(self, **kwargs):

        try:
            # Get the data for performinga paginated search
            my_connector = Es_connector(index=kwargs["index"])
            res = my_connector.init_paginatedSearch({
                "query": {
                    "match_all": {}
                }
            })
            sid = res["sid"]
            scroll_size = res["scroll_size"]
            total=int(res["total"])
            print("Total: ", total)

            # Analyse and process page by page
            i=0
            processed = 0
            while scroll_size > 0:
                i+=1
                res2 = my_connector.loop_paginatedSearch(sid, scroll_size)
                scroll_size = res2["scroll_size"]
                processed += scroll_size
                tweets = res2["results"]
                self.gerenate_ngrams_for_tweets(tweets, prop=kwargs["prop"], index=kwargs["index"])

                # For backend & client-side logging
                curr_log = "Updating bigrams of " + str(str(processed) + " tweets of " + str(total) + " (" + str(round(processed*100/total, 2)) + "% done)")
                self.logs.append(curr_log)
                self.logs = self.logs[:10]
                print(curr_log)

            # Clean it at the end so the clien knows when to end asking for more logs
            self.logs = []

            return True

        except Exception as e:
            print('Error: ' + str(e))
            return False

    def get_current_backend_logs(self):
        return self.logs

    def updatePropertyValue(self, **kwargs):

        # query = {
        #     "script": {
        #         "lang": "painless",
        #         "source": "ctx._source." + kwargs["property_name"] + " = params.ngrams",
        #         "params": {
        #             "ngrams": kwargs["property_value"]
        #         }
        #     },
        #     "query": {
        #         "match": {
        #             "_id": kwargs["tweet_id"]
        #         }
        #     }
        # }
        # Es_connector().es.update_by_query(body=query, doc_type='tweet', index=kwargs["index"])

        # tweet["_id"]   ["_source"]["id"]["$oid"]
        tweet = kwargs["tweet"]
        Es_connector().es.update(
            index=kwargs["index"],
            doc_type="tweet",
            id=tweet["_id"],
            body={"doc": {
                kwargs["property_name"]: kwargs["property_value"]
            }}
        )

    def get_stopwords_for_langs(self, langs):

        swords = []
        if "en" in langs:
            swords = swords + stopwords.words('english')
        if "fr" in langs:
            swords = swords + stopwords.words('french')
        if "ar" in langs:
            swords = swords + stopwords.words('arabic')
        if "nl" in langs:
            swords = swords + stopwords.words('dutch')
        if "id" in langs:
            swords = swords + stopwords.words('indonesian')
        if "fi" in langs:
            swords = swords + stopwords.words('Finnish')
        if "de" in langs:
            swords = swords + stopwords.words('German')
        if "hu" in langs:
            swords = swords + stopwords.words('Hungarian')
        if "it" in langs:
            swords = swords + stopwords.words('Italian')
        if "nb" in langs:
            swords = swords + stopwords.words('Norwegian')
        if "pt" in langs:
            swords = swords + stopwords.words('Portuguese')
        if "ro" in langs:
            swords = swords + stopwords.words('Romanian')
        if "ru" in langs:
            swords = swords + stopwords.words('Russian')
        if "es" in langs:
            swords = swords + stopwords.words('spanish')
        if "sv" in langs:
            swords = swords + stopwords.words('Swedish')
        if "tr" in langs:
            swords = swords + stopwords.words('Turkish')

        # TODO: complete with the full list of supported langs (there are some langs supported but miissing  and not documented. E.g. Bulgarian or Ukrainian https://pypi.org/project/stop-words/ )
        # The full list of languages may be found in C:/Users/username/AppData/Roming/nltk_data/corpora/stopwords

        return swords
