import os
from collections import Counter
from pymongo import MongoClient

def write_to_data(path=''):
    fpath = os.path.join(os.path.dirname(__file__),os.pardir,'data/') + path
    f = open(fpath, 'w')
    return f

def mongo_connect(db_name,collection_name=None):
    dbclient = MongoClient('z')
    mongo = dbclient[db_name]
    if collection_name is None:
        db = mongo.tweets
        return db
    else:
        db = mongo[collection_name]
        return db

def counter_data(count,gran=False):
    codes = {}

    if gran:
        codes['misinfo'] = count['misinfo']
        codes['speculation'] = count['speculation']
        codes['hedge'] = count['hedge']
        codes['correction'] = count['correction']
        codes['question'] = count['question']
        codes['other'] = count['unrelated'] + count['other/unclear/neutral'] + count['unclear'] + count[''] + count['discussion - justifying'] + count['discussion - question'] + count['other'] + count['discussion']

    else:
        codes['misinfo'] = count['misinfo'] + count['speculation'] + count['hedge']
        codes['correction'] = count['correction'] + count['question']
        codes['other'] = count['unrelated'] + count['other/unclear/neutral'] + count['unclear'] + count[''] + count['discussion - justifying'] + count['discussion - question'] + count['other'] + count['discussion']

    return codes
