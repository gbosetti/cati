import string
import nltk
from nltk.corpus import stopwords
nltk.download('stopwords')
from collections import Counter


class NgramBasedClasifier:

    def get_n_grams(self, text, length=2):
        # return zip(*[text[i:] for i in range(length)])
        return list(nltk.bigrams(text))

    def remove_stop_words(self, full_text, langs=["en", "fr", "es"]):

        punctuation = list(string.punctuation + "…" + "..." + "’" + "️" + "'" + '🔴' + '•')
        multilang_stopwords = self.get_stopwords_for_langs(langs) + ["Ã", "RT"] + punctuation
        tokenized_text = nltk.word_tokenize(full_text)
        filtered_words = list(filter(lambda word: word not in multilang_stopwords, tokenized_text))
        full_text = " ".join(filtered_words)
        return full_text

    def bigrams_with_higher_ocurrence(self, tweets, min_occurrences=20, remove_stopwords=True, stemming=True, length=2, top_ngrams_to_retrieve=None):

        try:
            full_bigrams = {}
            res = tweets["hits"]["hits"]
            for tweet in res:
                clean_text = self.remove_stop_words(tweet["_source"]["text"]).split()
                bigrams = Counter(self.get_n_grams(clean_text, length)).most_common(top_ngrams_to_retrieve)

                for k, v in bigrams:
                    try:
                        full_bigrams[k[0] + " " + k[1]].append(tweet["_id"])  # .add for {}
                    except KeyError:
                        full_bigrams[k[0] + " " + k[1]] = [
                            tweet["_id"]]  # Use an array otherwise it will be expensive to convert to json

            return {k: full_bigrams[k] for k in full_bigrams if len(full_bigrams[k]) > min_occurrences}  # partial_bigrams

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
