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


def to_boolean(str_param):
    if isinstance(str_param, bool):
        return str_param
    elif str_param.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    else:
        return False

args = parser.parse_args()

index = args.index  # E.g. "experiment_lyon_2015_gt"
property_name = "text_images"
langs = Functions().get_lang_count(index)["aggregations"]["distinct_lang"]["buckets"]
langs = [lang["key"] for lang in langs]



def generate_text_images_prop(docs, langs=["en", "fr", "es"]):
    ngramsAnalizer = NgramBasedClasifier()
    for tweet in docs:
        image_clusters = tweet["_source"].get("imagesCluster", [])
        image_clusters_str=''
        for cluster_id in image_clusters:
            image_clusters_str += ' ' + str(cluster_id)

        doc_text = tweet["_source"]["text"]
        clean_text = ngramsAnalizer.remove_stop_words(doc_text, langs=langs)  # .split()

        full_text = clean_text + image_clusters_str
        #print(property_name, "(", tweet["_id"], ") = ", full_text)
        # ngramsAnalizer.updatePropertyValue(tweet=tweet, property_name=property_name, property_value=full_text, index=index)
        Es_connector(index=index).es.update(
            index=index,
            doc_type="tweet",
            id=tweet["_id"],
            body={"doc": {
                property_name: full_text
            }}
        )



try:
    my_connector = Es_connector(index=index)
    res = my_connector.init_paginatedSearch({
        "query": {
            "match_all": {}
        }
    })

    # res = my_connector.init_paginatedSearch({
    #     "query": {
    #         "match": {"_id": "SvfjDGoBPjCajA-0a9x-"}
    #     }
    # })
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
