import json
import re
import argparse
from mabed.es_connector import Es_connector

__author__ = "Firas Odeh"
__email__ = "odehfiras@gmail.com"

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Import images clusters into Elasticsearch index')
    p.add_argument('-i', metavar='index', type=str, help='The Elasticsearch index you want to associate the image clusters')
    args = p.parse_args()

    with open('config.json', 'r') as f:
        config = json.load(f)

    for source in config['elastic_search_sources']:
        if source['index'] == args.i:
            filename = source['image_duplicates']

    print('File: %s\nIndex: %s\n' % (filename, args.i))

    with open(filename) as f:
        data = json.load(f)

    print('Number of clusters: %d' % len(data['duplicates']))
    print('Index', args.i)

    my_connector = Es_connector(index=args.i)
    imgs = 0
    count = 0
    c_count = 0
    for cluster in data['duplicates']:
        for img in cluster:
            imgs+=1
            print("     Image ", imgs)
            target_tweet_id  = re.search(r'(?<=/)(\d*)_(.*)\.(.*)', img, re.M | re.I)
            res = my_connector.search({
                "query": {
                        "term": {"id_str": target_tweet_id.group(1)}
                    }})
            if res['hits']['total']>0:
                id = res['hits']['hits'][0]['_id']
                if 'imagesCluster' in res['hits']['hits'][0]['_source']:
                    arr = res['hits']['hits'][0]['_source']['imagesCluster']
                    if isinstance(arr, list):
                        arr.extend([c_count])
                        arr = list(set(arr))
                        update = my_connector.update_field(id, 'imagesCluster', arr)
                    else:
                        update = my_connector.update_field(id, 'imagesCluster', [arr])
                else:
                    update = my_connector.update_field(id, 'imagesCluster', [c_count])

                count += res['hits']['total']
        c_count += 1
        print('CLuster ', c_count, ' -----------------------')
    print('images %d' % imgs)
    print('count %d' % count)