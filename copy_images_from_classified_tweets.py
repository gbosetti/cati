import json
import os
import ast
from flask import jsonify

dataset_file = "C:\\Users\\gbosetti\\Desktop\\DATASETS\\lyon2015_gttweets.json"
input_images_folder = "C:\\Users\\gbosetti\\Desktop\\DATASETS\\"
output_images_folder = "C:\\Users\\gbosetti\\Desktop\\DATASETS\\2015"

with open(dataset_file, encoding="utf8") as f:
    # text_data = f.read().replace('\n', '')
    # dataform = str(text_data).strip("'<>() ").replace('\'', '\"')
    raw_data = '"""' + f.read() + '"""'
    # raw_data = """[{'_index': 'experiment_lyon_2015_gt', '_type': 'tweet', '_id': 'J_fkDGoBPjCajA-0Afjt', '_score': 3.1454492, '_source': {'in_reply_to_status_id_str': '674564028337901568', 'in_reply_to_status_id': {'$numberLong': '674564028337901568'}, 'link': ['https://twitter.com/BeRbAtOv69/status/674564148844503040'], 'created_at': 'Wed Dec 09 12:20:00 +0000 2015', 'in_reply_to_user_id_str': '2696669898', 'source': '<a href="http://twitter.com" rel="nofollow">Twitter Web Client</a>', 'retweet_count': 0, 'retweeted': False, 'geo': None, 'path': '/home/stage/IDENUM/2015_dataset/ImageDataset.TwitterFDL2015.json', 'filter_level': 'low', 'in_reply_to_screen_name': 'CamsLeLyonnais', 'is_quote_status': False, 'id_str': '674564148844503040', 'host': 'liris-r03-sta001', '@version': '1', 'favorite_count': 0, 'id': {'$oid': '56681c70bc16ea0554d56c9d'}, 'text': '@CamsLeLyonnais @batindi simple mais beau', 'place': {'country': 'France', 'country_code': 'FR', 'full_name': 'Lyon, RhÃ´ne-Alpes', 'bounding_box': {'coordinates': [[[4.771831, 45.707363], [4.771831, 45.808281], [4.898367, 45.808281], [4.898367, 45.707363]]], 'type': 'Polygon'}, 'place_type': 'city', 'name': 'Lyon', 'attributes': {}, 'id': '179b8df9e368044d', 'url': 'https://api.twitter.com/1.1/geo/id/179b8df9e368044d.json'}, 'lang': 'fr', 'favorited': False, 'coordinates': None, 'truncated': False, 'timestamp_ms': '1449663600537', '@timestamp': '2015-12-09T12:20:00.537Z', 'entities': {'urls': [], 'hashtags': [], 'user_mentions': [{'indices': [0, 15], 'screen_name': 'CamsLeLyonnais', 'id_str': '2696669898', 'name': "Cam's", 'id': {'$numberLong': '2696669898'}}, {'indices': [16, 24], 'screen_name': 'batindi', 'id_str': '2190928680', 'name': 'Christian Lafort', 'id': {'$numberLong': '2190928680'}}], 'symbols': []}, '2grams': ['@camslelyonnais-@batindi', '@batindi-simple', 'simple-beau'], 'contributors': None, 'user': {'utc_offset': 3600, 'friends_count': 294, 'profile_image_url_https': 'https://pbs.twimg.com/profile_images/664124503795060736/udZcLHkL_normal.jpg', 'listed_count': 25, 'profile_background_image_url': 'http://pbs.twimg.com/profile_background_images/498172113123958785/Pqaa0Sz0.jpeg', 'default_profile_image': False, 'favourites_count': 3273, 'description': "J'viens de Lyon pas d'Saint Trond / Lyon Fans / @Gone_Academie #Courtoisizta", 'is_translator': False, 'created_at': 'Tue Aug 30 23:31:32 +0000 2011', 'profile_background_image_url_https': 'https://pbs.twimg.com/profile_background_images/498172113123958785/Pqaa0Sz0.jpeg', 'protected': False, 'screen_name': 'BeRbAtOv69', 'profile_link_color': '3B94D9', 'id_str': '365158660', 'profile_background_color': '131516', 'geo_enabled': True, 'lang': 'fr', 'profile_sidebar_border_color': 'FFFFFF', 'profile_text_color': '333333', 'verified': False, 'profile_image_url': 'http://pbs.twimg.com/profile_images/664124503795060736/udZcLHkL_normal.jpg', 'time_zone': 'Paris', 'contributors_enabled': False, 'url': None, 'profile_banner_url': 'https://pbs.twimg.com/profile_banners/365158660/1449502377', 'profile_background_tile': True, 'follow_request_sent': None, 'statuses_count': 59940, 'following': None, 'followers_count': 1003, 'default_profile': False, 'profile_use_background_image': True, 'name': 'Tito', 'location': 'Lyon ', 'profile_sidebar_fill_color': 'EFEFEF', 'notifications': None}}}] """
    # parsed_data = ast.parse(raw_data)
    # jsonified_data = jsonify(raw_data)
    data_dict = ast.literal_eval(raw_data)

    # data = eval(raw_data) # This should return a json but returns a string
    json_data = json.loads(data_dict)

    #print(data[0])
    #print(data[0]["_index"])

    dataform = bytes(raw_data, "utf-8").decode("unicode_escape").replace('\n', '')  #.replace('\"', '\n').replace('"', '\n').replace('\'', '\"').replace('\n', '\"').replace('None', '\"None\"')
    # data_dict = ast.literal_eval(dataform)
    # str = str(f.read().replace('\n', '')) NOTHING
    # data1 = ast.parse(dataform)
    json_data = eval(dataform)
    #'{"data": ' + dataform + '}')
    json_data = json.loads(data)

os.mkdir(output_images_folder)