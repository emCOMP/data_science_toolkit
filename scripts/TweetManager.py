import utils
from TweetCleaner import TweetCleaner
from TweetExporter import TweetExporter
import argparse


class TweetManager(object):

    def __init__(
            self,
            event,
            rumor,
            export_path,
            export_cols,
            ):
        self.actions = {
            'compress': self.compress,
            'load_training': self.load_training,
            'load_full': self.load_full,
        }

        # name of the event's db
        self.event = event

        # name of the rumor to work with
        self.rumor = rumor

        # db containing all event tweets
        self.db = utils.mongo_connect(db_name=self.event)

        # db for mapping unique tweets to non-uniques
        self.compression = utils.mongo_connect(db_name='rumor_compression',
                                               collection_name=self.rumor)

        # db collection for the individual rumor
        self.rumor_collection = self.__create_rumor_collection__()

        # A cleaner to clean our tweets for comparison purposes.
        cleaner_settings = {
            'scrub_retweet_text': True,
            'scrub_url': True
        }
        self.cleaner = TweetCleaner(
            all_ops=False, user_settings=cleaner_settings)

        self.exporter = TweetExporter(export_path, export_cols)


    def __create_rumor_collection__(self):

        # Create a connection to the database.
        # (This creates a new collection if none exists.)
        rumor_collection = utils.mongo_connect(db_name=self.event,
                                               collection_name=self.rumor)

        # If the collection is empty, we haven't made one before.
        if rumor_collection.find().count() == 0:
            print '!!! Rumor collection does not exist !!!'
            print 'Creating collection...'
            insert_list = []

            # Get all of the tweets matching the rumor query.
            tweet_list = self._find_tweets()

            # Insert the tweets into the collection in batches of 1000.
            for tweet in tweet_list:
                insert_list.append(tweet)
                if len(insert_list) == 1000:
                    rumor_collection.insert(insert_list)
                    insert_list = []

            # Insert the final batch of tweets.
            rumor_collection.insert(insert_list)
            rumor_collection.ensure_index('id')
            rumor_collection.ensure_index('created_ts')
        else:
            print 'Rumor collection found.'

        return rumor_collection


    # Helper method for finding rumor specific tweets from config.py
    def __find_tweets__(self):
        query = config.rumor_terms[self.rumor]
        tweet_list = self.db.find(query)
        print 'Locating tweets...'
        return tweet_list

    # Helper method for creating a list of unique tweets from a rumor
    def __compress__(self, sample=False):
        if sample:
            tweet_list = self.rumor_collection.find({'sample': True})
        else:
            tweet_list = self._find_tweets()
        try:
            count = self.compression.find().sort(
                'db_id', -1).limit(1).next()['db_id'] + 1
        except StopIteration:
            count = 0

        for tweet in tweet_list:
            # Clean the text.
            text = self.cleaner.clean(tweet['text'])

            # If after cleaning we find an exact match in the database...
            if self.compression.find_one({'text': text}) is not None:
                # Add this tweet to the compression list for the match.
                self.compression.update({'text': text},
                                        {'$addToSet': {'id': tweet['id']}})

            # Otherwise...
            else:
                # Add a new entry to the database.
                self.compression.insert({'db_id': count,
                                         'rumor': self.rumor,
                                         'text': text,
                                         'id': [tweet['id']]})

                # NOTE: Old code, not sure what this does / if important.
                if count == 0:
                    self.compression.ensure_index('text')
                count += 1

    # Creates a list of unique tweets
    def compress(self):
        # Check to make sure compression hasn't already been run
        check = self.compression.find_one()
        if check:
            print 'This rumor has already been compressed!'
            print 'Please drop the collection manually if \
                    you need to compress again'
        else:
            print 'Compressing tweets...'
            self.__compress__()

    # # wrapper for creating samples
    # # set edit_distance = true to create a list of different tweets
    # def create_sample(self, start=0, scrub_url=True, edit_distance=False):
    #     title = self.out_file
    #     f = utils.write_to_samples(path=title)

    #     if edit_distance:
    #         print 'enter a sample size'
    #         num = self.training_size
    #         self._create_sample_old(num=num, scrub_url=scrub_url, f=f)
    #     else:
    #         self._create_sample(num=0, f=f, start=start)

    def generate_training(self, sample_size):
        # Get the whole set of tweets.
        tweet_list = self.__find_tweets__()

        # How many tweets we have selected so far.
        count = 0

        # The text of the tweets we've selected so far.
        result = []

        for tweet in tweet_list:

            # Clean the tweet text.
            text = self.cleaner.clean(tweet['text'])

            # Assume the tweet is unique.
            unique = True

            # For each tweet 'y' which we've selected so far...
            for y in result:

                # Check the edit distance between the tweet 'y' and
                # our new tweet 'tweet'.
                cur_edit_dist = nltk.metrics.edit_distance(text, y)

                # If any of the edit distances are below the threshold
                # we say the tweet is not unique.
                if cur_edit_dist < edit_distance:
                    unique = False

            # If we still believe the tweet is unique after the
            # comparisons above...
            if unique:
                # Record our selection
                count += 1
                result.append(text)

                # Write the tweet to the file.
                self.exporter.export_tweet(tweet)

            # If we've achieved the desired 'sample_size', then stop.
            if count >= sample_size:
                break


    def generate_full(self):
        pass


def main(args):
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Manages tweet flow between the database,\
                    spreadsheets, and the coding tool.')
    parser.add_argument(
        'action', help='What to do with the tweets.', type=str)
    parser.add_argument(
        'db_name', help='The name of the database to use.', type=str)
    parser.add_argument(
        'rumor_name', help='The name of the rumor to use.', type=str)
    parser.add_argument(
        '-p', '--export_path', help='File path to use for export.',
        type=str, required=False, default='./samples/sample.csv')
    parser.add_argument(
        '-c', '--export_cols', help='Which columns to export.',
        type=str, required=False, default=["db_id", "tweet_id", "text"])
    args = parser.parse_args()
    main(args)
