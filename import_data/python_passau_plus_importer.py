import csv
import datetime
from elasticsearch import Elasticsearch

input_path="D:/IDENUM/data-to-import/passau/enriched_filtered_data_plus.csv"
target_index="geo_passau_plus_2"
# target_props=["user_name", "text", "latitude", "longitude", "date"]

input_data=open(input_path, encoding="utf8")
reader=csv.DictReader(input_data)
csv_columns = reader.fieldnames

for line in reader:

    #    try:

    #Creating the doc
    document = {}
    document["user"] = {"name": line["user_name"]}
    document["text"] = line["text"]

    if line["date"]:
        document["timestamp_ms"] = datetime.datetime.timestamp(datetime.datetime.strptime(line["date"], '%Y-%m-%d %H:%M:%S'))

    if line["latitude"] and line["longitude"]:
        document["coordinates"] = {"coordinates": [float(line["latitude"]), float(line["longitude"])]}

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
        #client.save(index=target_index, validate=True, skip_empty=True, **kwargs)

        # res = client.update(
        #     index=target_index,
        #     doc_type="tweet",
        #     id=doc_id,
        #     body={"doc": document }
        # )

    # except Exception as err:
    #     print("Error: ", err)

input_data.close()