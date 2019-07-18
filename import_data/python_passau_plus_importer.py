import csv
import datetime
from elasticsearch import Elasticsearch

input_path="D:/IDENUM/data-to-import/passau/enriched_filtered_data_plus.csv"
target_index="geo_passau_plus"
# target_props=["user_name", "text", "latitude", "longitude", "date"]

input_data=open(input_path, encoding="utf8")
reader=csv.DictReader(input_data)
csv_columns = reader.fieldnames

for line in reader:

    #Creating the doc
    document = {}
    document["user"] = {"name": line["user_name"]}
    document["text"] = line["text"]

    if line["date"]:
        date_as_date = datetime.datetime.strptime(line["date"], '%Y-%m-%d %H:%M:%S')
        document["timestamp_ms"] = datetime.datetime.timestamp(date_as_date)
        document["created_at"] = date_as_date.strftime("%a %b %d %H:%M:%S +0000 %Y")

    if line["latitude"] and line["longitude"]:
        document["coordinates"] = {
            "coordinates": [float(line["latitude"]), float(line["longitude"])],
            "type": "Point"
        }

    # Persistence
    client = Elasticsearch(
        ["localhost"],
        http_auth=("elastic", "elastic"),
        port=9200,
        timeout=1000,
        use_ssl=False
    )
    doc_id = line["id"]
    client.create(index=target_index, doc_type="tweet", body=document, id=doc_id)

input_data.close()