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

    def most_frequent_n_grams(self, tweets, length=2, top_ngrams_to_retrieve=None, remove_stopwords=True,
                              stemming=True):

        for tweet in tweets["results"]:
            tweet["_source"]["clean_text"] = self.remove_stop_words(tweet["_source"]["text"])

        tweet_texts = [tweet["_source"]["clean_text"] for tweet in tweets["results"]]
        full_text = "".join(tweet_texts)

        ngram_counts = Counter(self.get_n_grams(full_text.split(), length))
        return ngram_counts.most_common(top_ngrams_to_retrieve)

    def bigrams_with_higher_ocurrence(self, tweets, min_occurrence=20, remove_stopwords=True, stemming=True):

        full_bigrams = self.most_frequent_n_grams(tweets)
        filtered_bigrams = list(filter(lambda bigram: bigram[1] > 20, full_bigrams))

        tweets_by_bigrams = []

        for bigram in filtered_bigrams:  # If the two components of a bigram are present in a text, then link it
            bigram_rel_tweets = []

            for tweet in tweets["results"]:
                # This is more precise but it takes too much time. E.g. 13 seconds for 500 tweets when the other  strategy tooks 2
                # tweet_text = self.remove_stop_words(tweet["_source"]["text"])
                tweet_text = tweet["_source"]["clean_text"]
                bigram_az = bigram[0][0] + " " + bigram[0][1]
                # bigram_za = bigram[0][1] + " " + bigram[0][0]
                if bigram_az in tweet_text:  # or bigram_za in tweet_text:
                    # This strategy is faster, but retrieves a lot of extra tweets. Cases like FDL > FDL2017 will be contemplated :(
                    # tweet_text = tweet["_source"]["text"]
                    # if bigram[0][0] in tweet_text and bigram[0][1] in tweet_text:
                     bigram_rel_tweets.append(tweet)  # ["_source"]["text"]

            tweets_by_bigrams.append({"bigram": bigram[0], "tweets": bigram_rel_tweets})

        return filtered_bigrams, tweets_by_bigrams

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
