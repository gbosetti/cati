from mabed.es_connector import Es_connector
import json
import argparse
import os

file = '2017export.json'
target = 'images_list.lst'


def get_tweets(session, index, state='confirmed'):
    # Get all confirmed tweets
    connector = Es_connector(index=index, doc_type='tweet')

    query = {
        "query": {
            "term": {
                "session_" + session: state
            }
        }
    }

    res = connector.bigSearch(query)
    return res


def get_labeled_tweets(session, index):
    # Get all confirmed tweets
    connector = Es_connector(index=index, doc_type='tweet')

    query = {
        "query": {
            "bool": {
                "should": [
                    {
                        "term": {
                            "session_"+session: "confirmed"
                        }
                    },
                    {
                        "term": {
                            "session_"+session: "negative"
                        }
                    }
                ]
            }
        }
    }

    res = connector.bigSearch(query)
    return res


def tweets2file(tw, f):
    # Write to a file
    res = []
    for tweet in tw:
        res.append(tweet['_source'])
    with open(f, 'w') as output:
        json.dump(res, output, indent=4)


def select_images(tw):
    c = 0
    i = 0
    res = []
    for tweet in tw:
        c = c + 1
        if 'media' in tweet['_source']['entities']:
            for media in tweet['_source']['entities']['media']:
                if media['type'] == 'photo':
                    i = i + 1
                    res.append(tweet['_source']['id_str'])

    print('Exported tweets : ', c)
    print('number of images : ', i)
    return res


def image_names_2_file(images, f, path):
    # check if target is a valid path
    target_file = path + '/' +f
    print("Writing images list to ",target_file)
    with open(target_file, 'w') as f:
        for item in images:
            f.write("%s\n" % item)


def copy_images(images_list, images_path, target_path):
    # this version is still not working, so we still rely on the Shell script
    image_names_2_file(images_list,'images_list',target_path)
    print("Creating images directory")
    os.mkdir('Images')
    print("Copying images")
    os.system("cat images_list|./copyImages.sh "+images_path+" "+target_path+'/Images')
    print("aynsc or not")

    #for item in ids:
    #    print(item)
        # copy files

if __name__ == '__main__':
    p = argparse.ArgumentParser(
        description='Export the confirmed tweets, and the related images')
    p.add_argument('-i', metavar='index', type=str,
                   help='The index to be extracted')
    p.add_argument('-s', metavar='session', type=str,
                   help='The session to be extracted')
    p.add_argument('-p', metavar='path', type=str,
                   help='The path to  the folder containing the images')
    p.add_argument('-d', metavar='dir', type=str,
                   help='The target folder, defaults to current')
    p.add_argument('-c', metavar='confirmed', type=bool, default=False,
                   help='Set this flag to extract only the confirmed tweets')
    args = p.parse_args()
    if args.s is not None:
        session = args.s
    else:
        print("No SESSION defined")
        p.print_help()
        p.exit()
    if args.i is not None:
        index = args.i
    else:
        print("No INDEX defined")
        p.print_help()
        p.exit()
    if args.p is not None:
        images_path = args.p
        if os.path.exists(images_path):
            print("Exists")
        else:
            print('Does not exist')
    else:
        print("No PATH defined")
        p.print_help()
        p.exit()
    if args.d is not None:
        target_path = args.d
    else:
        target_path = os.getcwd()
    # check if the index and the sessions exist
    if args.c:
        print("Getting confirmed tweets")
        tweets = get_tweets(session, index,state='confirmed')
    else:
        print('Getting labeled tweets')
        tweets = get_labeled_tweets(session, index)
    # check if the folder exists
    # check if the folder is empty
    tweets2file(tweets, file)
    images_list = select_images(tweets)
    copy_images(images_list,images_path,target_path)
