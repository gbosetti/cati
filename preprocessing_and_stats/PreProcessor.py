from preprocessing_and_stats.Stats import Stats
import re
import string
from collections import Counter
import nltk
from nltk import bigrams
from nltk.stem import PorterStemmer
nltk.download('stopwords')
# from nltk.stem.snowball import FrenchStemmer
# from nltk.stem.snowball import SnowballStemmer
from nltk.tokenize import TweetTokenizer
from mabed.es_connector import Es_connector
from classification.ngram_based_classifier import NgramBasedClasifier

class PreProcessor:

    def __init__(self):
        self.stats = Stats()

    punctuation = list(string.punctuation + "…" + "..." + "’" + "️" + "'" + '🔴' + '•')
    emoticons_str = r"""
            (?:
                [:=;] # Eyes
                [oO\-]? # Nose (optional)
                [D\)\]\(\]/\\OpP] # Mouth
            )"""
    # regex_str = [
    #     emoticons_str,
    #     r'<[^>]+>',  # HTML tags
    #     r'(?:@[\w_]+)',  # @-mentions
    #     r"(?:\#+[\w_]+[\w\'_\-]*[\w_]+)",  # hash-tags
    #     r'http[s]?://(?:[a-z]|[0-9]|[$-_@.&amp;+]|[!*\(\),]|(?:%[0-9a-f][0-9a-f]))+',  # URLs
    #     r'(?:(?:\d+,?)+(?:\.?\d+)?)',  # numbers
    #     r"(?:[a-z][a-z'\-_]+[a-z])",  # words with - and '
    #     r'(?:[\w_]+)',  # other words
    #     r'(?:\S)'  # anything else
    # ]
    # tokens_re = re.compile(r'(' + '|'.join(regex_str) + ')', re.VERBOSE | re.IGNORECASE)
    emoticon_re = re.compile(r'^' + emoticons_str + '$', re.VERBOSE | re.IGNORECASE)

    def process_stopwords(self, tokens):
        if self.remove_stopwords:
            return [term for term in tokens if term not in self.stop_words]
        else:
            return tokens

    def tokenize(self, tweet_content):

        tknzr = TweetTokenizer()
        tokens = tknzr.tokenize(tweet_content)
        # tokens = self.tokens_re.findall(tweet_content)
        if self.generate_stats:
            self.stats.count_total_tokens(tokens)
        return tokens

    def process_lowercase(self, tweet):

        if self.to_lowercase:
            return [token.lower() for token in tweet]
        else:
            return tweet

    def process_mentions(self, tokens):

        if self.include_mentions:
            return tokens
        else:
            return list(filter(lambda token: not (token.startswith('@')), tokens))

    def process_hashtags(self, tokens):

        if self.include_hashtags:
            return tokens
        else:
            return list(filter(lambda token: not (token.startswith('#')), tokens))

    def process_stemming(self, tokens):

        if self.stem_tokens:
            stemmer = PorterStemmer()
            stemmed_tokens = []
            for token in tokens:
                stemmed_tokens.append(stemmer.stem(token))

            return stemmed_tokens

        else:
            return tokens

    def process_emoticons(self, tokens):

        if self.include_emoticons:
            return tokens
        else:
            return list(filter(lambda token: not (self.emoticon_re.search(token)), tokens))

    def process_hashtag_splitting(self, tokens):

        if self.split_hashtags:

            reg_exp = re.compile(r'#[a-z, 0-9]{2,}(?![a-z])|[A-Z][a-z]+')
            splitted_tokens = []
            for token in tokens:

                if token.startswith("#"):

                    words = reg_exp.findall(token)
                    # print(token, " -> ", words,  words.__len__())
                    for word in words: # Checked: if no word is detected, the code in the loop is not executed
                        # if word.startswith("#"):
                            #splitted_tokens.append(word[1:])
                        # else:
                        splitted_tokens.append(word)
                    splitted_tokens.append(token)
                else:
                    splitted_tokens.append(token)

            return splitted_tokens

        else:
            return tokens

    def pre_process_tweet_corpus(self, tweet):

        tokens = self.tokenize(tweet) # Splitting text into words
        tokens = self.process_emoticons(tokens)
        tokens = self.process_hashtag_splitting(tokens) # Splitting hashtags
        tokens = self.process_lowercase(tokens)
        tokens = self.process_stopwords(tokens)
        tokens = self.process_mentions(tokens) # Including or excluding mentions
        tokens = self.process_hashtags(tokens) # Including or excluding mentions
        tokens = self.process_stemming(tokens)

        return tokens

    def filtering_target_langs(self, tweets):
        if self.target_langs:

            # In case the API changes or you change the current structure of some tweet
            # target_tweets = [tweet for tweet in tweets if 'lang' in tweet]
            # print(len(target_tweets), " have the 'lang' tag")
            # no_target_tweets = [tweet for tweet in tweets if not('lang' in tweet)]
            # print(no_target_tweets)
            target_tweets = list(filter(lambda tweet: tweet['lang'] in self.target_langs, tweets)) # , target_tweets))

            if self.generate_stats:
                self.stats.update_included_langs(self.target_langs, target_tweets)
                self.stats.update_excluded_langs(self.target_langs, tweets)

            return target_tweets
        else:
            return tweets

    def most_common_tokens(self, tweets, remove_stopwords=True, to_lowercase=True, maxTermsByTweet=None,
                           includeMentions=True,
                           include_hashtags=True, stem_tokens=True, split_hashtags=True, remove_urls=True):

        # tweets = self.pre_process(tweets, remove_stopwords, to_lowercase, None, includeMentions,
        #            include_hashtags, stem_tokens, split_hashtags, remove_urls)
        count_all = Counter()

        for tweet in tweets:
            count_all.update(tweet)

        # Return the first n most frequent words
        return count_all.most_common(maxTermsByTweet)

    def frequentBigramCount(self, tweetList, frequentTermCount=10):
        count_all = Counter()
        for tweet in tweetList:
            terms_stop = [term for term in tweet['text'] if term not in self.stop_words]
            terms_bigram = bigrams(terms_stop)
            # Update the counter
            count_all.update(terms_bigram)
        # Print the first 5 most frequent words
        # print(count_all.most_common(frequentTermCount))
        return count_all.most_common(frequentTermCount)

    def get_stats(self):
        return self.stats.get_stats()

    def pre_process(self, tweets, **kwargs):

        self.__init__();

        self.stop_words = self.punctuation + ['rt', 'via']
        for lbs in kwargs["lang_based_stopworders"]:
            self.stop_words = self.stop_words + lbs.stop_words()

        # Keep them as properties in case we implement it as a chain of responsibilities
        # DO NOT refactor by moving this to the init, otherwise a new instance must be created each time
        # the data is pre-processed
        self.remove_stopwords = kwargs.get('remove_stopwords', True)
        self.to_lowercase =kwargs.get('to_lowercase', True)
        self.max_terms_by_tweet = kwargs.get('max_terms_by_tweet', None)
        self.include_mentions = kwargs.get('include_mentions', True)
        self.include_hashtags = kwargs.get('include_hashtags', True)
        self.stem_tokens = kwargs.get('stem_tokens', True)
        self.split_hashtags = kwargs.get('split_hashtags', False)
        self.remove_urls = kwargs.get('remove_urls', False)
        self.target_langs = kwargs.get('target_langs', ["fr", "en"])
        self.generate_stats = kwargs.get('generate_stats', False)
        self.include_emoticons = kwargs.get('include_emoticons', False)

        processed_tweets = []

        # Stats: counting the number of total read tweets
        if self.generate_stats:
            orig_total_tweets = self.stats.count_total_tweets(tweets)

        # Updating stats
        print("Filtering tweets by language")
        tweets = self.filtering_target_langs(tweets)

        print("Processing the individual corpus. It could take a while...")
        for tweet in tweets:

            # Creating the new tweet structure (discarding other fields)
            new_tweet = {}
            new_tweet["id"] = tweet['id']
            new_tweet["lang"] = tweet['lang']
            new_tweet["tokens"] = self.pre_process_tweet_corpus(tweet['text'])
            # new_tweet["created_at"] = tweet['created_at']
            new_tweet["timestamp_ms"] = tweet['timestamp_ms']
            new_tweet["user_id"] = tweet['user']['id_str'] # id

            # Adding them to the processed collection
            processed_tweets.append(new_tweet)

        # Update stats
        if self.generate_stats:
            self.stats.count_removed_tweets(self.stats.total_tweets(), tweets=processed_tweets)

        # Return the first n most frequent words
        return processed_tweets


    def putDocumentProperty(self, **kwargs):

        try:
            query = {
                "properties": {
                    kwargs["prop"]: {
                        "type": kwargs["prop_type"]
                    }
                }
            }
            Es_connector().es.indices.put_mapping(
                index=kwargs["index"],
                doc_type="tweet",
                body=query
            )
            print("Successfully putting ", kwargs["prop"], " property into the index")
        except Exception as e:
            print('Error on putDocumentProperty: ' + str(e))

