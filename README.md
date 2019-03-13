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

If something fails and PyCharm is not detecting the dependencies, then install them by using the UI ( File > Settings > Project > Project Interpreter > + )

Note that in Ubuntu and other Linux distribution python and pip are bound to python2, so one should explicitly call
python3 and pip3 for these to work

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

Before running the application, it is important to properly configure the available list of indexes you want to use from the application. To do so, you can edit the config.json file at the root of the project's folder.

Start the elasticsearchserver:

    python3 server.py

And visit localhost:5000. The first time the system is running, a new “mabed_sessions” index will be automatically created. Just in case a read-only error arises, please run the following using Kibana:
    
    PUT mabed_sessions/_settings { "index": { "blocks": { "read_only_allow_delete": "false" } } } 

Once the application isrunning, go to Settings > Create Session. choose a name and an existing index in Elasticsearch, and click Save. The process may take a while.

Once the new session is created, please select it from the Switch Sessions combo and click on the "Swithc session" button. The information presentes in the "Current Session" section should be updated.

Once you are working with the right session, you can generate as many ngrams as you want, to be further used in the "Tweets Search" tab. E.g. choose "2" and press the "(Re) generate" button. If you execute the process with the same parameters more than once, the ngrams are updated, not duplicated.


### Updating the dependencies

If you edit the code and install new dependencies, you can update the list by executing:
    python -m pip freeze --local > requirements.txt


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


