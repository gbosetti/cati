import nltk
from sklearn.preprocessing import normalize
import numpy as np
from gensim.models import KeyedVectors
from mabed.es_connector import Es_connector

model_path = "./word2vec_twitter_model.bin"
model = KeyedVectors.load_word2vec_format(model_path, binary=True,unicode_errors='ignore')

# the index to be read and vectors added
index = "twitterfdl2015mentions"
# get text from tweets
print("Getting tweets")
# my_connector = Es_connector(index=index, doc_type="tweet")
# query = {
#     "match_all": {}
# }
# text = my_connector.bigTweetTextSearch({"query":query})
text = "coeur coeur sur toi bricou"
# for each tweet sum all the vectors and get the unitary vector
# maybe remove links ?
# convert a tweet into a vector using the trained model
print(text)
tokens = nltk.word_tokenize(text)
tweet_vec = np.zeros(model['coeur'].shape)
for word in tokens:
    print(word)
    try:
        vector = model[word]
        tweet_vec = np.add(tweet_vec, vector)
        print(len(vector))
    except KeyError as ke:
        print(word,"is not in vocabulary")

tweet = normalize(tweet_vec[:,np.newaxis], axis=0)
print(tweet)
