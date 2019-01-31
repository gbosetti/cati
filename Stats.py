import json
from collections import defaultdict


class Stats:

    def __init__(self):
        self.data = {
            "tweets": {
                "total": 0,
                "total_removed": 0,
                "excluded_by_lang": 0,
                "target_langs": [],
                "excluded_langs": {
                    "total": 0,
                    "list": []
                }
            },
            "tokens": {
                "total": 0,
                "removed": 0,
                "stemmed_words": 0,
                "popular": []
            },
            "characters": {
                "total_uppercases": 0
            },
            "mentions": {
                "total": 0,
                "removed": 0
            },
            "hashtags": {
                "total": 0,
                "removed": 0,
                "splitted": 0,
                "splitted_extra_words": 0
            }
        }

    # TOKENS ·······································

    def count_total_tokens(self, tokens):
        self.data["tokens"]["total"] = len(tokens)
        return self.data["tokens"]["total"]

    # TWEETS ·······································

    def count_total_tweets(self, tweets):
        self.data["tweets"]["total"] = len(tweets)
        return self.data["tweets"]["total"]

    def count_removed_tweets(self, initial_amount=0, tweets=0):
        self.data["tweets"]["total_removed"] = initial_amount - len(tweets)
        return self.data["tweets"]["total_removed"]

    def count_removed_tweets_by_lang(self, initial_amount=0, tweets=0):
        self.data["tweets"]["removed_by_lang"] = initial_amount - len(tweets)
        return self.data["tweets"]["removed_by_lang"]

    def total_tweets(self):
        return self.data["tweets"]["total"]

    def update_excluded_langs(self, target_langs, tweets):

        excluded_tweets = list(filter(lambda tweet: not (tweet['lang'] in target_langs), tweets))
        self.data["tweets"]["excluded_by_lang"] = len(excluded_tweets)

        excluded_langs = list(set(map(lambda tweet: tweet["lang"], excluded_tweets)))
        self.data["tweets"]["excluded_langs"]["total"] = len(excluded_langs)

        # Count excluded tweets by lang
        lang_bag = defaultdict(int)
        for tweet in excluded_tweets:
            lang_bag[tweet["lang"]] += 1
        self.data["tweets"]["excluded_langs"]["list"] = dict(lang_bag)

    def update_included_langs(self, target_langs, target_tweets):

        self.data["tweets"]["excluded_by_lang"] = len(target_tweets)

        for lang in target_langs:
            self.data["tweets"]["target_langs"] = len(list(filter(lambda tweet: tweet["lang"] == lang, target_tweets)))

    def get_stats(self):
        return self.data
