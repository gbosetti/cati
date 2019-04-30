from mabed.es_connector import Es_connector
import argparse
import time

# Instantiating the parser
parser = argparse.ArgumentParser(description="Removing duplicates")

# General & mandatory arguments (with a default value so we can run it also through the PyCharm's UI

parser.add_argument("-i",
                    "--index",
                    dest="index",
                    help="The target index drom which to look for duplicated docs")

args = parser.parse_args()

if args.index is None:
    raise Exception('You must provide an index')

print("You are removing duplicates from the " + args.index + " index.")

my_conn = Es_connector(index=args.index)
buckets_size = 1

while buckets_size > 0:

    res = my_conn.search({
        "size":0,
        "query": {
            "match_all" : {}
        },
        "aggs" : {
            "duplicated_by_str_id":{
                "terms":{
                    "field" : "id_str.keyword",
                    "min_doc_count": 2,
                    "size": 20
                }
            }
        }
    })
    buckets_size = len(res['aggregations']['duplicated_by_str_id']['buckets'])

    for bucket in res['aggregations']['duplicated_by_str_id']['buckets']:

        print("Deleting ", bucket["key"])
        duplicated_res = my_conn.search({
            "query": {
                "match": {"id_str": bucket["key"]}
            }
        })

        total_dup_files = duplicated_res["hits"]["total"]
        for i in range(0,total_dup_files-1):
            doc = duplicated_res["hits"]["hits"][i]
            my_conn.delete(doc["_id"])

    time.sleep(2)  # Sleep 2 seconds to avoid errors in the next loop


print("Done!")

