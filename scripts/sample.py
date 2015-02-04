from collections import Counter
import utils,random,re,nltk,os,csv,config

def _find_tweets(db,rumor):
    query = config.rumor_terms[rumor]
    tweet_list = db.find(query)
    print 'finished query'
    return tweet_list

def _scrub_tweet(text,scrub_url=True):
    temp = None
    s = ur'\u201c' + '@.*?:'
    while text is not temp:
        temp = text
        text = re.sub('RT .*?:','',text).strip()
        text = re.sub('"@.*?:','',text).strip()
        text = re.sub(s,'',text).strip()
        text = re.sub('via @.*?:','',text).strip()
        text = re.sub('via @.*?\b','',text).strip()
        text = re.sub('@.*?\b','',text).strip()
        if scrub_url is True:
            text = re.sub('http.*?\s|http.*?$','',text).strip()
    #print text
    return text

def _create_sample_old(rumor,num,db,f,scrub_url=True):

    tweet_list = [x for x in _find_tweets(db,rumor)]
    print 'created list'

    count = 0
    result = []
    for tweet in tweet_list:
        text = _scrub_tweet(text=tweet['text'],scrub_url=True)
        unique = True
        for y in result:
            if nltk.metrics.edit_distance(text,y) < 20:
                unique = False
        if unique is True:
            result.append(text)
            out = '"%s","%s","%s",\n' % (tweet['id'],
                                         rumor,
                                         tweet['text'].replace('"',''))
            f.write(out.encode('utf-8'))
            count += 1
        if count >= num:
            break

    return result

def _create_sample(rumor,db,dbs,num,f,start=0):

    db = db #utils.mongo_connect(db_name='ebola_cache',collection_name=rumor)
    dbs = dbs
    #dbs = [utils.mongo_connect(db_name='ebola'),
    #       utils.mongo_connect(db_name='ebola2'),
    #       utils.mongo_connect(db_name='ebola3')]
    result = []
    if num == 0:
        query = {}
    else:
        query = {'$and':[{'db_id':{'$gte':start}},{'db_id':{'$lt':start+num}}]}
    tweet_list = db.find(query)

    for tweet in tweet_list:
        for x in dbs:
            full_tweet = x.find_one({'id':tweet['id'][0]})
            if full_tweet is not None:
                text = full_tweet['text']
                result.append(text)
                out = '"%s","%s","%s","%s",\n' % (tweet['db_id'],
                                                  rumor,
                                                  tweet['id'][0],
                                                  text.replace('"',''))
                f.write(out.encode('utf-8'))
                break

    return result

def create_sample(rumor_list,db=None,dbs=None,num=0,start=0,scrub_url=True,old=False):
    print 'enter a valid file name:'
    fname_in = raw_input('>> ')
    title = "%s.csv" % (fname_in)
    f = utils.write_to_samples(path=title)
    f.write('"db_id","rumor","id","text"\n')

    for rumor in rumor_list:
        if old is True:
            _create_sample_old(rumor=rumor,num=num,db=db,scrub_url=scrub_url,f=f)
        else:
            cache = utils.mongo_connect(db_name=db,collection_name=rumor)
            _create_sample(rumor=rumor,db=cache,dbs=dbs,num=num,f=f,start=start)

def _compress_tweets(db,cache,rumor):
    tweet_list = _find_tweets(db,rumor)
    try:
        count = cache.find().sort('db_id',-1).limit(1).next()['db_id'] + 1
    except StopIteration:
        count = 0
    for tweet in tweet_list:
        text = _scrub_tweet(text=tweet['text'],scrub_url=True)

        if cache.find_one({'text':text}) is not None:
            cache.update({'text':text},
                         {'$push':{'id':tweet['id']}})
        else:
            cache.insert({'db_id':count,
                          'rumor':rumor,
                          'text':text,
                          'id':[tweet['id']]})
            if count == 0:
                cache.ensure_index('text')
            count += 1

def compress_tweets(db_name,rumor_list,cache_name):
    for rumor in rumor_list:
        cache = utils.mongo_connect(db_name=cache_name,collection_name=rumor)
        db = utils.mongo_connect(db_name=db_name)
        test = cache.find_one()
        if test:
            print 'uniques db already exists!'
            print 'exiting...'
        else:
            _compress_tweets(db=db,cache=cache,rumor=rumor)

def expand_tweets(db_name,cache_name,code_comparison_name,rumor_list):
    for rumor in rumor_list:
        cache = utils.mongo_connect(db_name=cache_name,collection_name=rumor)
        db = utils.mongo_connect(db_name=db_name,collection_name=rumor)
        code_comparison = utils.mongo_connect(db_name=code_comparison_name,collection_name=rumor)
        _expand_tweets(db=db,cache=cache,code_comparison=code_comparison,rumor=rumor)

def _expand_tweets(db,cache,code_comparison,rumor):
    compressed_list = code_comparison.find()
    for tweet in compressed_list:
        db_id = int(tweet['db_id'])
        final_code = tweet.get('final','')
        tweet_list = cache.find_one({'db_id':db_id})
        for tweets in tweet_list['id']:
            db.update({'id':tweets},
                      {'$push':{'codes':{'rumor':rumor,
                                         'code':final_code,}}})

def rumor_collection(db_name,rumor_list):
    for rumor in rumor_list:
        db = utils.mongo_connect(db_name=db_name)
        rumor_collection = utils.mongo_connect(db_name=db_name,collection_name=rumor)
        insert_list = []
        tweet_list = _find_tweets(db=db,rumor=rumor)
        for tweet in tweet_list:
            insert_list.append(tweet)
            if len(insert_list) == 1000:
                rumor_collection.insert(insert_list)
                insert_list = []
        rumor_collection.insert(insert_list)

def main():

    # list of dbs for creating samples from multiple databases
    #dbs = [utils.mongo_connect(db_name='sydneysiege')]
    # single database for creating a sample
    db = utils.mongo_connect(db_name='sydneysiege')
    db_name = 'sydneysiege'
    # the cache database name for compression
    cache_name = 'sydneysiege_cache'
    code_comparison_name = 'code_comparison'

    # list of the rumors names.  check config.py for rumor names
    rumor_list=['flag','airspace']

    # uncomment this code to compress tweets and create a full sample
    #for db in dbs:
    #rumor_collection(db_name=db_name,rumor_list=rumor_list)
    #compress_tweets(db_name=db_name,rumor_list=rumor_list,cache_name=cache_name)
    #create_sample(rumor_list=rumor_list,db=cache_name,dbs=dbs)

    #rumor_collection(db_name=db_name,rumor_list=rumor_list)

    #expand_tweets(db_name=db_name,cache_name=cache_name,code_comparison_name=code_comparison_name,rumor_list=rumor_list)

    # uncomment this code to create a random sample.
    create_sample(rumor_list=rumor_list,db=db,num=60,scrub_url=True,old=True)

if __name__ == "__main__":
    main()
