import json
import re
import argparse
from mabed.es_connector import Es_connector

__author__ = "Firas Odeh"
__email__ = "odehfiras@gmail.com"

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Import images clusters into Elasticsearch index')
    p.add_argument('-f', metavar='file', type=str, help='Cluseters json file')
    p.add_argument('-i', metavar='index', type=str, help='Elasticsearch Index')
    args = p.parse_args()
    print('File: %s\nIndex: %s\n' % (args.f, args.i))

    with open(args.f) as f:
        data = json.load(f)

    print('Number of clusters: %d' % len(data['duplicates']))

    my_connector = Es_connector(index=args.i)
    # my_connector = Es_connector(index=args.i, host='http://206.189.211.142', user='', password='')
    imgs = 0
    count = 0
    c_count = 0
    for cluster in data['duplicates']:
        for img in cluster:
            imgs+=1
            matchObj = re.match(r'(\d*)_(.*).(.*)', img, re.M | re.I)
            res = my_connector.search({
                "query": {
                        "term": {"id_str": matchObj.group(1)}
                    }})
            if res['hits']['total']>0:
                id= res['hits']['hits'][0]['_id']
                if 'imagesCluster' in res['hits']['hits'][0]['_source']:
                    arr = res['hits']['hits'][0]['_source']['imagesCluster']
                    if isinstance(arr, list):
                        print(res['hits']['hits'][0]['_source']['imagesCluster'])
                        arr.extend([c_count])
                        arr = list(set(arr))
                        update = my_connector.update_field(id, 'imagesCluster', arr)
                    else:
                        update = my_connector.update_field(id, 'imagesCluster', [arr])
                        print(res['hits']['hits'][0]['_source']['imagesCluster'])
                else:
                    update = my_connector.update_field(id, 'imagesCluster', [c_count])
                count += res['hits']['total']
        c_count += 1
        print('-----------------------')
    print('images %d' % imgs)
    print('count %d' % count)