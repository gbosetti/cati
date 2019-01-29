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


## Usage

Provided a set of tweets, MABED can (i) perform event detection and (ii) generate a visualization of the detected events.

### Import images clusters into Elasticsearch

    python3 images.py -f twitter2015.json -i twitter2015
    
-f The json file which contains images clusers  
-i Elasticsearch Index

### Start the web application
    python3 server.py

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


