# MABED
## About

MABED is a Python 3 implementation of [MABED](#mabed), distributed under the terms of the MIT licence. If you make use of this software in your research, please cite one the [references](#references) below.

## Requirements

MABED requires scipy, numpy and networkx; these scientific libraries come pre-installed with the [Anaconda Python](https://anaconda.org) distribution. You can also install them manually via [pip](https://pypi.python.org):

	pip install scipy
	pip install numpy
	pip install networkx
	...

You can install all the required libraries (listed in the file `requirements.txt`) by executing the command:

	pip install -r requirements.txt

If PyCharm is not detecting the dependencies, then install them by using the UI ( File > Settings > Project > Project Interpreter > + )


## Usage

Provided a set of tweets, MABED can (i) perform event detection and (ii) generate a visualization of the detected events.

### Import tweets into Elasticsearch

Edit the logstash_tweets_importer.conf file with the path to the json file containing the tweets in your device. Then, run the following command:
logstash -f logstash_tweets_importer.conf


### Import images clusters into Elasticsearch

    python images.py -f twitter2017.json -i twitterfdl2017
    
-f The json file which contains images clusers  
-i Elasticsearch Index

This process adds a new field to the tweets in elasticsearch, called "imagesCluster", which is used by es_corpus.py to retrieve the tweet corpus with an extra feature integrated to the textual value:

    tweet_text = tweet_text + cluster_str

If you execute the images.py script more than one, the values are updated, not duplicated. You can delete the field from Kibana by executing:

    POST twitterfdl2017/_update_by_query?conflicts=proceed
    {
        "script" : "ctx._source.remove('imagesCluster')",
        "query" : {
            "exists": { "field": "imagesCluster" }
        }
    }

### Start the web application

Start the elasticsearchserver. If you are running the application for the first time, please create a “mabed_sessions” index using kibana. For the version 6.5.4 simply execute the following line in the Dev tools console:

    PUT mabed_sessions

Then:

    python3 server.py

Visit localhost:5000.

PS: right now, the indexes listed and used by the application are fixed. Please, add an alias if the name of your index is different. You can do it by running a query like the following one:

    POST /_aliases
    {
        "actions" : [
            { "add" : { "index" : "twitterfdl2017", "alias" : "twitter2017" } }
        ]
    }

When running MABED, the detect_events method is called. Look at the functions.py file

# MABED

## About

MABED (Mention-Anomaly-Based Event Detection) is a statistical method for automatically detecting significant events that most interest Twitter users from the stream of tweets they publish. In contrast with existing methods, it doesn't only focus on the textual content of tweets but also leverages the frequency of social interactions that occur between users (i.e. mentions). MABED also differs from the literature in that it dynamically estimates the period of time during which each event is discussed rather than assuming a predefined fixed duration for all events.

http://mediamining.univ-lyon2.fr/people/guille/mabed.php

## References

- Adrien Guille and Cécile Favre (2015)
  [Event detection, tracking, and visualization in Twitter: a mention-anomaly-based approach](https://github.com/AdrienGuille/pyMABED/blob/master/mabed.pdf).
  Springer Social Network Analysis and Mining,
  vol. 5, iss. 1, art. 18 [DOI: 10.1007/s13278-015-0258-0]


- Adrien Guille and Cécile Favre (2014)
  Mention-Anomaly-Based Event Detection and Tracking in Twitter.
  In Proceedings of the 2014 IEEE/ACM International Conference on
  Advances in Social Network Mining and Analysis (ASONAM 2014),
  pp. 375-382 [DOI: 10.1109/ASONAM.2014.6921613]


