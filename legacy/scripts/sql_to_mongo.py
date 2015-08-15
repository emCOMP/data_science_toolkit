import MySQLdb,utils,db_config
from pymongo import MongoClient

#connect to mongo db
mongo = utils.mongo_connect(db_name='mh17')

#connect to sql db
sql = MySQLdb.connect(host=db_config.sql['host'],
                      user=db_config.sql['user'],
                      passwd=db_config.sql['passwd'],
                      db="mh17")
sql_cursor = sql.cursor()
table = 'tweet_mh17'

def process(x):
    tweet = {
        'created_ts':x[1],
        'source':x[3].decode('latin-1').encode('utf-8'),
        'text':x[4].decode('latin-1').encode('utf-8'),
        'id':long(x[5]),
        'user':{
            'screen_name':x[6].decode('latin-1').encode('utf-8'),
            'id':x[8],
            'name':x[11].decode('latin-1').encode('utf-8'),
            'description':x[12].decode('latin-1').encode('utf-8'),
            'followers_count':int(x[13]),
            'friends_count':int(x[14]),
            'location':x[15].decode('latin-1').encode('utf-8'),
            'profile_background_image_url_https':x[22].decode('latin-1').encode('utf-8'),
            'statuses_count':int(x[23])
        },
        'entities':{
            "user_mentions" : [],
            "symbols" : [],
            "trends" : [],
            "hashtags" : [],
            "urls" : []
        },
        'counts':{
            "user_mentions" : 0,
            "hashtags" : 0,
            "urls" : 0
        }
    }
    if x[9] != '':
        tweet['geo'] = {
            'type':'Point',
            'coordinates':[x[9],x[10]]
        }
    else:
        tweet['geo'] = None
    if x[16] != '':
        tweet['place'] = {
            'full_name':x[16].decode('latin-1').encode('utf-8'),
            'url':x[17]
        }
    else:
        tweet['place'] = None
    for y in xrange(19,22):
        if x[y] != '':
            url = {
                'url':x[(y+5)],
                'expanded_url':x[y].decode('latin-1').encode('utf-8')
            }
            tweet['entities']['urls'].append(url)
            tweet['counts']['urls'] += 1
    if x[27] != 27:
        retweeted = {
            'id':long(x[27]),
            'retweet_count':int(x[28]),
            'user':{
                'screen_name':x[29].decode('latin-1').encode('utf-8')
            },
            #'text':x[30].decode('latin-1').encode('utf-8'),
            #'created_ts':x[31]
        }
        tweet['retweeted_status'] = retweeted
    return tweet

def fetch(start,cursor):
    #sql db query
    end = start + 1000
    query = 'select * from %s where id >= %f and id < %f' % (table,start,end)
    cursor.execute(query)

def index_check():
    dbclient = MongoClient('z')
    mongotest = dbclient['ebola']
    x = mongotest.getIndexes()
    print x

def main():
    #sql db query
    query = 'select count(*) from %s' % table
    sql_cursor.execute(query)
    num_tweets = sql_cursor.fetchone()[0]
    processed_tweets = []
    count = 1
    while count < num_tweets - 1:
        fetch(count,sql_cursor)
        for x in sql_cursor.fetchall():
            tweet = process(x)
            processed_tweets.append(tweet)
            count += 1
            if count > 0 and count % 1000 == 0:
                mongo.insert(processed_tweets)
                processed_tweets = []
                print 'processed %d tweets' % count
    mongo.insert(processed_tweets)
    print 'finished processing'

if __name__ == "__main__":
    main()
    #index_check()
