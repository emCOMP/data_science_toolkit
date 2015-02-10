from collections import Counter
import utils,random,re,nltk,os,csv,config

class TweetSampler(object):

    def __init__(self,event,_namerumor):
        # name of the event's db
        self.event_name = event_name
        # name of the rumor to sample / compress /expand
        self.rumor = rumor
        # db containing all event tweets
        self.db = utils.mongo_connect(db_name=self.event)
        # db for raw and finals codes
        self.code_comparison = utils.mongo_connect(db_name='code_comparison',
                                                   collection_name=self.rumor)
        # db for mapping unique tweets to non-uniques
        self.compression = utils.mongo_connect(db_name='rumor_compression',
                                               collection_name=self.rumor)
        # db collection for the individual rumor
        self.rumor_collection = _create_rumor_collection()

    # check for a rumor specific collection
    # make collection if doesn't exist
    # return db
    def _create_rumor_collection(self):
        if not self.rumor in self.db.collection_names():
            rumor_collection = utils.mongo_connect(db_name=self.event,
                                                   collection_name=self.rumor)
            insert_list = []
            tweet_list = _find_tweets()
            for tweet in tweet_list:
                insert_list.append(tweet)
                if len(insert_list) == 1000:
                    rumor_collection.insert(insert_list)
                    insert_list = []
            rumor_collection.insert(insert_list)
        return rumor_collection

    # helper method for finding rumor specific tweets from config.py
    def _find_tweets(self):
        query = config.rumor_terms[self.rumor]
        tweet_list = self.db.find(query)
        print 'finished query'
        return tweet_list

    # scrub retweets from tweet text
    # also scrub url if scrub_url is true
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

    # helper method to create a random sample using edit distance
    # default edit distance of 20
    def _create_sample_old(self,num,f,scrub_url=True,edit_distance=20):

        tweet_list = [x for x in _find_tweets()]
        print 'created list'

        count = 0
        result = []
        for tweet in tweet_list:
            text = _scrub_tweet(text=tweet['text'],scrub_url=True)
            unique = True
            for y in result:
                if nltk.metrics.edit_distance(text,y) < edit_distance:
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

    # helper method to create a sample of unique tweets from a rumor
    def _create_sample(self,num,f,start=0):

        result = []
        if num == 0:
            query = {}
        else:
            query = {'$and':[{'db_id':{'$gte':start}},{'db_id':{'$lt':start+num}}]}
        tweet_list = self.compression.find(query)

        for tweet in tweet_list:
            for x in dbs:
                full_tweet = self.db.find_one({'id':tweet['id'][0]})
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

    # wrapper for creating samples
    # set edit_distance = true to create a list of different tweets
    def create_sample(self,start=0,scrub_url=True,edit_distance=False):
        print 'enter a valid file name:'
        fname_in = raw_input('>> ')
        title = "%s.csv" % (fname_in)
        f = utils.write_to_samples(path=title)
        f.write('"db_id","rumor","id","text"\n')

        if edit_distance:
            _create_sample_old(num=num,scrub_url=scrub_url,f=f)
        else:
            _create_sample(num=num,f=f,start=start)

    # helper method for creating a list of unique tweets from a rumor
    def _compress_tweets(self):
        tweet_list = _find_tweets()
        try:
            count = self.compression.find().sort('db_id',-1).limit(1).next()['db_id'] + 1
        except StopIteration:
            count = 0
        for tweet in tweet_list:
            text = _scrub_tweet(text=tweet['text'],scrub_url=True)

            if self.compression.find_one({'text':text}) is not None:
                self.compression.update({'text':text},
                                        {'$addToSet':{'id':tweet['id']}})
            else:
                self.compression.insert({'db_id':count,
                                         'rumor':rumor,
                                         'text':text,
                                         'id':[tweet['id']]})
                if count == 0:
                    self.compression.ensure_index('text')
                count += 1

    # create a list of unique tweets
    # check to make sure compression hasn't already been run
    def compress_tweets(self):
        test = cache.find_one()
        if test:
            print 'uniques db already exists!'
            print 'exiting...'
        else:
            _compress_tweets()

    # apply codes from unique coded tweets to a rumor specific collection
    def expand_tweets(self):
        compressed_list = self.code_comparison.find()
        for tweet in compressed_list:
            db_id = int(tweet['db_id'])
            first_code = tweet.get('first_final','')
            second_code = tweet.get('second_final',[])
            tweet_list = self.compression.find_one({'db_id':db_id})
            for tweets in set(tweet_list['id']):
                self.rumor_collection.update({'id':tweets},
                                             {'$push':{'codes':{'rumor':rumor,
                                                                'first_code':first_code,
                                                                'second_code':second_code}}})

def main():
    event = 'sydneysiege'
    rumor = 'hadley'
    t = TweetSampler(event_name=event,rumor=rumor)

def old_main():

    # list of dbs for creating samples from multiple databases
    #dbs = [utils.mongo_connect(db_name='sydneysiege')]
    # single database for creating a sample
    db = utils.mongo_connect(db_name='sydneysiege')
    db_name = 'sydneysiege'
    # the cache database name for compression
    cache_name = 'sydneysiege_cache'
    code_comparison_name = 'code_comparison'

    # list of the rumors names.  check config.py for rumor names
    rumor_list=['hadley']

    # uncomment this code to compress tweets and create a full sample
    #for db in dbs:
    #rumor_collection(db_name=db_name,rumor_list=rumor_list)
    #compress_tweets(db_name=db_name,rumor_list=rumor_list,cache_name=cache_name)
    #create_sample(rumor_list=rumor_list,db=cache_name,dbs=dbs)

    rumor_collection(db_name=db_name,rumor_list=rumor_list)

    expand_tweets(db_name=db_name,cache_name=cache_name,code_comparison_name=code_comparison_name,rumor_list=rumor_list)

    # uncomment this code to create a random sample.
    #create_sample(rumor_list=rumor_list,db=db,num=60,scrub_url=True,old=True)

if __name__ == "__main__":
    main()
