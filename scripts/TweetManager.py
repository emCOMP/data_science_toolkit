import utils
import TweetCleaner
import argparse

class TweetManager(object):

    def __init__(self, event, rumor):
        self.actions = {
                    'compress':self.compress,
                    'load_training':self.load_training,
                    'load_full':self.load_full,
        }

        # name of the event's db
        self.event = event
        # name of the rumor to sample/compress/expand
        self.rumor = rumor
        # db containing all event tweets
        self.db = utils.mongo_connect(db_name=self.event)

        # db for mapping unique tweets to non-uniques
        self.compression = utils.mongo_connect(db_name='rumor_compression',
                                               collection_name=self.rumor)

        # db collection for the individual rumor
        self.rumor_collection = self.__create_rumor_collection__()

        self.cleaner = TweetCleaner()

    def __create_rumor_collection__(self):
        rumor_collection = utils.mongo_connect(db_name=self.event,
                                               collection_name=self.rumor)
        if rumor_collection.find().count() ==  0:
            print '!!! Rumor collection does not exist !!!'
            print 'Creating collection...'
            insert_list = []
            tweet_list = self._find_tweets()
            for tweet in tweet_list:
                insert_list.append(tweet)
                if len(insert_list) == 1000:
                    rumor_collection.insert(insert_list)
                    insert_list = []
            rumor_collection.insert(insert_list)
            rumor_collection.ensure_index('id')
            rumor_collection.ensure_index('created_ts')
        else:
            print 'Rumor collection found.'
        return rumor_collection

        # helper method for finding rumor specific tweets from config.py
    def __find_tweets__(self):
        query = config.rumor_terms[self.rumor]
        tweet_list = self.db.find(query)
        print 'Locating tweets...'
        return tweet_list

    def compress(self):
        pass

    def load_training(self):
        pass

    def load_full(self):
        pass



def main(args):
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Manages tweet flow between the database,spreadsheets, and the coding tool.')
    parser.add_argument(
        'action', help='What to do with the tweets.', type=str)
    parser.add_argument(
        'db_name', help='The name of the database to use.', type=str)
    parser.add_argument(
        'rumor_name', help='The name of the rumor to use.', type=str)
    parser.add_argument(
        '-ec', '--event_color', help='color to use for event capture volume',
        type=str, required=False, default='black')
    args = parser.parse_args()
    main(args)
