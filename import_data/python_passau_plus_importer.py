import csv
import datetime
from elasticsearch import Elasticsearch
import argparse


parser = argparse.ArgumentParser(description="CATI's Active Learning module")
parser.add_argument("-ip", "--input_path", dest="input_path", help="The path to the csv. E.g. D:/data/data.csv")
parser.add_argument("-ti", "--target_index", dest="target_index", help="The name of the (already existing) index. E.g. geo_data")
args = parser.parse_args()


input_data=open(args.input_path, encoding="utf8")
reader=csv.DictReader(input_data)
csv_columns = reader.fieldnames
client = Elasticsearch(
    ["localhost"],
    http_auth=("elastic", "elastic"),
    port=9200,
    timeout=1000,
    use_ssl=False
)

for line in reader:

    try:
        if line["text_translated_en"]:

            doc_id = line["id"]

            #Creating the doc
            document = {}
            document["user"] = {"name": line["user_name"]}
            document["text"] = line["text_translated_en"]
            document["id_str"] = doc_id

            if line["date"]:
                date_as_date = datetime.datetime.strptime(line["date"], '%Y-%m-%d %H:%M:%S')
                document["timestamp_ms"] = str(int(datetime.datetime.timestamp(date_as_date)))
                document["created_at"] = date_as_date.strftime("%a %b %d %H:%M:%S +0000 %Y")

            if line["latitude"] and line["longitude"]:
                document["coordinates"] = {
                    "coordinates": [float(line["latitude"]), float(line["longitude"])],
                    "type": "Point"
                }

            # Persistence
            client.create(index=args.target_index, doc_type="tweet", body=document, id=doc_id)
            print("Creating document #" + str(doc_id))

    except Exception as err:
        print("Error: ", err)

input_data.close()