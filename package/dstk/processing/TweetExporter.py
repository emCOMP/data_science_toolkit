import csv
import datetime
from TweetCleaner import TweetCleaner


class TweetExporter(object):

    """
    Handles the writing of tweets to csv rows on a tweet-by-tweet
    basis.

    Usage:
        1. Create a TweetExporter instance, initializing it with your
            desired path and export settings.
        2. For each tweet you want to export: call the instance's
            export_tweet() method, passing the tweet object as
            the argument.

    Args:
        path (str): The destination file-path to write output.
        export_cols ([str]): The columns to include in output.
        aux_cols ({str: str}): Keys are extra column names, values are
                                    the value to write in that column.

                                    Ex. {'rumor': 'sunil'} will include
                                    an extra column called 'rumor'
                                    with a value of 'sunil'.
        order_override ([str]): An ordered list of the export columns
                                which will specif the order in which
                                the columns are written to the file.
    """

    def __init__(
            self,
            path,
            export_features,
            aux_features=[],
            order_override=None):

        self.export_features = export_features
        # Get the column headers for each of our export features.
        # (The columns to include in exported CSVs.)
        self.export_cols = []
        for f in self.export_features:
            feat_func = self.__getattribute__(f)
            self.export_cols.extend(feat_func(header_only=True))

        # Auxilliary Columns
        # We split them up into two lists because we need to preserve order.
        self.aux_features = aux_features

        # The order in which to output the columns.
        if order_override is None:
            # Default Order
            self.output_order = self.aux_features + self.export_cols

        else:
            # Check to make sure all columns are accounted for.
            if set(self.aux_features + self.export_cols) == set(order_override):
                self.output_order = order_override
            else:
                raise ValueError('order_override does not match \
                                    export_cols and/or aux_cols')
        # Store our path.
        self.path = path
        # The csvwriter object to write the file.
        self.writer = self.__init_output__()

        # A cleaner to clean the tweets for output purposes.
        cleaner_settings = {
            'scrub_non_ascii': True,
            'scrub_newlines': True,
            'scrub_quotes': True
        }
        self.cleaner = TweetCleaner(
            all_ops=False, user_settings=cleaner_settings)

    # Initializes the output file and writes the header.
    def __init_output__(self):
        f = open(self.path, 'wb')
        writer = csv.DictWriter(f, self.output_order, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        return writer

    def export_tweet(self, tweet, aux_features={}):
        """
        Writes a tweet to the TweetExporter's output file.

        Args:
            extra <dict>: Extra non-built-in columns you want to add.
                        THIS MUST BE THE SAME FOR EVERY CALL TO EXPORT TWEET
                        Format: {header: value_for_this_tweet}
        """

        # This is the object we will pass to the DictWriter.
        line = {k: '' for k in self.output_order}

        # Grab all of our feature values.
        for feat in self.export_features:
            try:
                # Get the generator function
                generator = self.__getattribute__(feat)
                # Call it on the provided tweet.
                val = generator(tweet)
                line.update(val)
            except KeyError:
                pass

        # Add the aux features passed in to our line.
        line.update(
            {k: v for k, v in aux_features.iteritems() if k in self.aux_features})

        # Write to the file.
        self.writer.writerow(line)

    def get_path(self):
        """
        Returns:
            (str): The file-path this exporter is writing to.
        """
        return self.path


##########################################
#     Define Column Behaviours Here      #
##########################################

#   Note: 'tweet' is a single tweet object
#           in all of the methods below.
    def mongo_id(self, tweet=None, header_only=False):
        header = 'mongo_id'

        if header_only:
            return [header]
        else:
            return {header: str(tweet['_id'])}

    def db_id(self, tweet=None, header_only=False):
        header = 'db_id'

        if header_only:
            return [header]
        else:
            return {header: str(tweet['db_id'])}

    def text(self, tweet=None, header_only=False):
        header = 'text'

        if header_only:
            return [header]
        else:
            return {header: self.cleaner.clean(tweet['text'])}

    def tweet_id(self, tweet=None, header_only=False):
        header = 'tweet_id'

        if header_only:
            return [header]
        elif type(tweet['id']) == list:
            return {header: str(tweet['id'][0])}
        else:
            return {header: str(tweet['id'])}

    def first_level_code_comparison(self, tweet=None, header_only=False):
        header = 'first_level_code_comparison'

        if header_only:
            return [header]
        elif 'codes'in tweet.keys():
            result = []
            for container in tweet['codes']:
                result.append(container['first'])
            return {header: ', '.join(sorted(result))}
        else:
            return {header: ''}

    def first_level_codes(self, tweet=None, header_only=False):
        header = 'first_level_codes'

        if header_only:
            return [header]
        else:
            try:
                return {header: tweet['codes'][0]['first_code']}
            except:
                return {header: 'Not found.'}

    def second_level_code_comparison(self, tweet=None, header_only=False):
        header = 'second_level_code_comparison'

        if header_only:
            return [header]
        elif 'codes'in tweet.keys():
            ignore = ['coder_id',
                      'first',
                      'Affirm',
                      'Deny',
                      'Neutral',
                      'Unrelated',
                      'Uncodable'
                      ]
            result = []
            for container in tweet['codes']:
                for code in container:
                    if code not in ignore:
                        result.append(code)
            return {header: ', '.join(sorted(result))}
        else:
            return {header: ''}

    def second_level_codes(self, tweet=None, header_only=False):
        header = 'second_level_codes'

        if header_only:
            return [header]
        else:
            try:
                codes = tweet['codes'][0]['second_code']
                codes = [c for c in codes if c != 'Adjudicate']
                return {header: ', '.join(sorted(codes))}
            except:
                return {header: 'Not found.'}

    def second_level_separate(self, tweet=None, header_only=False):
        headers = ['Implicit', 'Uncertainty', 'Ambiguity']
        result = {c: 0 for c in headers}

        if header_only:
            return headers
        else:
            try:
                codes = tweet['codes'][0]['second_code']
                for c in codes:
                    if c in result:
                        result[c] = 1

            except:
                pass

            return result

    def final_code_comparison(self, tweet=None, header_only=False):
        header = 'final_code_comparison'

        if header_only:
            return [header]
        else:
            result = []
            if 'first_final' in tweet:
                result.append(tweet['first_final'])

            if 'second_final' in tweet:
                second_final = tweet['second_final']
                for code in second_final:
                    if code != 'Adjudicate':
                        result.append(code)

            return {header: ', '.join(sorted(result))}

    def datetime(self, tweet=None, header_only=False):
        header = 'datetime'
        if header_only:
            return [header]
        else:
            return {header: tweet['created_ts'].isoformat()}

    def retweet(self, tweet=None, header_only=False):
        header = 'retweet'

        if header_only:
            return [header]
        else:
            text = tweet['text'].lower()
            return {header: ("rt @" in text or "via @" in text)}

    def uncertainty_codes(self, tweet=None, header_only=False):
        headers = ["R/U",
                   "Named",
                   "Emotional_Comment",
                   "Question:_Theorizing",
                   "Uncertain_Space",
                   "Doubt_or_Challenge",
                   "Theorizing",
                   "Personal",
                   "Open_Question",
                   "Impersonal",
                   "Question:_Doubt",
                   "Trigger_Word",
                   "Question_Source",
                   "Statement_of_Incredulity",
                   "Simple_Pass",
                   "Wish/_Dread",
                   "Implied",
                   "Unnamed",
                   "Linked",
                   "Formal"]

        if header_only:
            return headers
        else:
            return tweet['uncertainty_codes']

#####################################
#     Testing Stuff For Testing     #
#####################################


def test(db, rumor):
    from pymongo import MongoClient
    mongo = MongoClient('z')[db][rumor]
    test = mongo.find({}).limit(10)
    e = TweetExporter(
        'test.csv',
        ["tweet_id", "text", "second_level_separate"],
        aux_features=['rumor', 'dummy']
    )
    for t in test:
        e.export_tweet(t, {'rumor': rumor})

    exit()

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Manages the writing of tweets to ')
    parser.add_argument(
        'db_name', help='The name of the database to use.', type=str)
    parser.add_argument(
        'rumor_name', help='The name of the rumor to use.', type=str)
    args = parser.parse_args()
    test(args.db_name, args.rumor_name)
