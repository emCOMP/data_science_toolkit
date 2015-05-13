from collections import Counter
import utils,re,config

class TweetProcessor(object):

    def __init__(self,event_name,rumor=None):
        # name of the event's db
        self.event = event_name
        # name of the rumor to sample/compress/expand
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
        if rumor:
            self.rumor_collection = self._create_rumor_collection()

    # check for a rumor specific collection
    # make collection if doesn't exist
    # return db
    def _create_rumor_collection(self):
        rumor_collection = utils.mongo_connect(db_name=self.event,
                                               collection_name=self.rumor)
        if rumor_collection.find().count() ==  0:
            print '[INFO] rumor collection does not exist, creating collection'
            insert_list = []
            tweet_list = self._find_tweets()
            for tweet in tweet_list:
                insert_list.append(tweet)
                if len(insert_list) == 1000:
                    rumor_collection.insert(insert_list)
                    insert_list = []
            rumor_collection.insert(insert_list)
            rumor_collection.ensure_index('id')
        else:
            print '[INFO] rumor collection exists'
        return rumor_collection

    # helper method for finding rumor specific tweets from config.py
    def _find_tweets(self):
        query = config.rumor_terms[self.rumor]
        tweet_list = self.db.find(query)
        print '[INFO] finished query'
        return tweet_list

    # scrub retweets from tweet text
    # also scrub url if scrub_url is true
    def _scrub_tweet(self,text,scrub_url=True):
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
