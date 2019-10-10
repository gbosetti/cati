from classification.ngram_based_classifier import NgramBasedClasifier
from mabed.es_connector import Es_connector
from mabed.functions import Functions

index = "geo_passau_plus_en"
input_field = "text"
langs = ["en", "fr"]
ngramsAnalizer = NgramBasedClasifier()


item = "0.005*i'm + 0.004*i + 0.003*refuge + 0.003*... + 0.003*syria + 0.002*border + 0.002*w + 0.002*#syria + 0.002*kurtuluş + 0.002*the + 0.002*türkiy + 0.002*.. + 0.001*syrian + 0.001*cross + 0.001*peopl + 0.001*love + 0.001*̇ + 0.001*one + 0.001*turkey + 0.001*istanbul"
terms = item.split(" + ")
terms

doc_text = "I'm trying... to solve this a w asd :) !!"
clean_text = ngramsAnalizer.remove_stop_words(doc_text, langs=langs)  # .split()
clean_text = ngramsAnalizer.remove_urls(text=clean_text)
clean_text = ngramsAnalizer.lemmatize(clean_text, "en") # "en", "fr"