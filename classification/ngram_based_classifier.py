import string
import nltk
from nltk.corpus import stopwords
nltk.download('stopwords')
from collections import Counter


class NgramBasedClasifier:

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

    def bigrams_with_higher_ocurrence(self, tweets, **kwargs ):  #min_occurrences=20, remove_stopwords=True, stemming=True, length=2, top_ngrams_to_retrieve=None):

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
