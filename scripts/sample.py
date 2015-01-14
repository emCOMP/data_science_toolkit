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
    while len(result) <= num:
        for tweet in random.sample(tweet_list,num):
            text = _scrub_tweet(text=tweet['text'],scrub_url=True)
            unique = True
            for y in result:
                if nltk.metrics.edit_distance(text,y) < 20:
                    unique = False
            if unique is True:
                result.append(text)
                out = '"%s","%s","%s",\n' % (rumor,
                                             tweet['id'],
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

def compress_tweets(db,rumor_list,cache_name):
    for rumor in rumor_list:
        cache = utils.mongo_connect(db_name=cache_name,collection_name=rumor)
        _compress_tweets(db=db,cache=cache,rumor=rumor)

def _exapand_tweets(db,cache,rumor):
    compressed_list = cache.find()
    for tweet_list in compressed_list:
        for tweet in tweet_list['id']:
            db.update({'id':tweet},{'$set':{'code'}})

def main():

    # list of dbs for creating samples from multiple databases
    dbs = [utils.mongo_connect(db_name='sydneysiege')]
    # single database for creating a sample
    db = utils.mongo_connect(db_name='sydneysiege')
    # the cache database name for compression
    cache_name = 'sydneysiege_cache'

    # list of the rumors names.  check config.py for rumor names
    rumor_list=['gunmen',]

    # uncomment this code to compress tweets and create a full sample
    #for db in dbs:
    #    compress_tweets(db=db,rumor_list=rumor_list,cache_name=cache_name)
    #create_sample(rumor_list=rumor_list,db=cache_name,dbs=dbs)

    # uncomment this code to create a random sample.
    create_sample(rumor_list=rumor_list,db=db,num=300,scrub_url=True,old=True)

if __name__ == "__main__":
    main()
