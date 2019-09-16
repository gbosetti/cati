from classification.ngram_based_classifier import NgramBasedClasifier
from mabed.es_connector import Es_connector
from mabed.functions import Functions
import argparse

# Instantiating the parser
parser = argparse.ArgumentParser(description="CATI's Active Learning module")

# General & mandatory arguments (with a default value so we can run it also through the PyCharm's UI

parser.add_argument("-i",
                    "--index",
                    dest="index",
                    help="The target index to which to add the new field")

parser.add_argument("-if",
                    "--input_field",
                    dest="input_field",
                    help="The target field to be written and pre-processed",
                    default="text")

parser.add_argument("-of",
                    "--output_field",
                    dest="output_field",
                    help="The field name to generate as the output",
                    default="clean-text")

parser.add_argument("-l",
                    "--languages",
                    dest="languages",
                    help="The list of languages to get the stopwords to remove. E.g. 'fr, es, it, de'")


def to_boolean(str_param):
    if isinstance(str_param, bool):
        return str_param
    elif str_param.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    else:
        return False

args = parser.parse_args()

index = args.index  # E.g. "experiment_lyon_2015_gt"
input_field = args.input_field
output_field = args.output_field

if 'languages' in args and args.languages != None:
    langs = args.languages.split(',')
    print("\nUsing user-defined languages to process stopwords...")
else:
    langs = Functions().get_lang_count(index)["aggregations"]["distinct_lang"]["buckets"]
    langs = [lang["key"] for lang in langs]
    print("\nUsing automatically-extracted languages to process stopwords...")



def generate_text_images_prop(docs, langs=["en", "fr", "es"]):

    ngramsAnalizer = NgramBasedClasifier()
    for tweet in docs:
        image_clusters = tweet["_source"].get("imagesCluster", [])
        image_clusters_str=''
        for cluster_id in image_clusters:
            image_clusters_str += ' ' + str(cluster_id)

        doc_text = tweet["_source"][input_field]
        clean_text = ngramsAnalizer.remove_stop_words(doc_text, langs=langs)  # .split()
        clean_text = ngramsAnalizer.remove_urls(text=clean_text)

        lang = "en"
        if tweet["_source"]["lang"] is not None:
            lang = tweet["_source"]["lang"]

        clean_text = ngramsAnalizer.lemmatize(clean_text, lang) # "en", "fr"

        full_text = clean_text + image_clusters_str
        Es_connector(index=index).es.update(
            index=index,
            doc_type="tweet",
            id=tweet["_id"],
            body={"doc": {
                output_field: full_text
            }}
        )
    print("Languages for stopwords: ", ngramsAnalizer.retrievedLangs)








try:
    my_connector = Es_connector(index=index)
    #query = #"query": {
            #"match_all": {}
        #}
    query = {
        "query": {
            "match": {
                "lang": "en or fr or es"
            }
        }
    }
    res = my_connector.init_paginatedSearch(query=query)

    sid = res["sid"]
    scroll_size = res["scroll_size"]
    init_total = int(res["total"])
    accum_total = 0

    print("\nTotal = ", init_total)
    print("\nScroll = ", scroll_size)
    print("\nLangs = ", langs)

    while scroll_size > 0:

        generate_text_images_prop(res["results"], langs)
        res = my_connector.loop_paginatedSearch(sid, scroll_size)
        scroll_size = res["scroll_size"]
        accum_total += scroll_size
        print(accum_total*100/init_total, "%")


except Exception as e:
    print('Error: ' + str(e))
