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
            export_cols,
            aux_cols={},
            order_override=None):
        # The columns to include in exported CSVs.
        self.export_cols = export_cols

        # Auxilliary Columns
        # We split them up into two lists because we need to preserve order.
        self.aux_headers = aux_cols.keys()
        self.aux_vals = [aux_cols[k] for k in self.aux_headers]

        # The order in which to output the columns.
        if order_override is None:
            # Default Order
            self.output_order = self.aux_headers + export_cols

        else:
            # Check to make sure all columns are accounted for.
            if set(self.aux_headers + export_cols) == set(order_override):
                self.output_order = order_override
            else:
                raise ValueError('order_override does not match \
                                    export_cols and/or aux_cols')
        # Store our path.
        self.path = path
        # The csvwriter object to write the file.
        self.writer = self.__init_output__(self.path)

        # A cleaner to clean the tweets for output purposes.
        cleaner_settings = {
            'scrub_non_ascii': True,
            'scrub_newlines': True,
            'scrub_quotes': True
        }
        self.cleaner = TweetCleaner(
            all_ops=False, user_settings=cleaner_settings)

    # Initializes the output file and writes the header.
    def __init_output__(self, path):
        # Quote all of our headers.
        headers = self.output_order
        f = open(path, 'wb')
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(headers)
        return writer

    def export_tweet(self, tweet, extra={}):
        """
        Writes a tweet to the TweetExporter's output file.

        Args:
            extra <dict>: Extra non-built-in columns you want to add.
                        THIS MUST BE THE SAME FOR EVERY CALL TO EXPORT TWEET
                        Format: {header: value_for_this_tweet}
        """
        out_order = self.output_order + extra.keys()
        line = []
        for col in out_order:
            # If the column is a built-in...
            if col in self.export_cols:
                # Get the generator function
                generator = self.__getattribute__(col)

                try:
                    # Call it on the provided tweet.
                    val = generator(tweet)
                except KeyError:
                    # If the tweet doesn't have the appropriate field.
                    # We just return an error value.
                    val = 'FEATURE_NOT_FOUND'

                line.append(val)

            # Otherwise it must be an aux column...
            elif col in self.aux_headers:
                # Retrive the provided aux value.
                header_index = self.aux_headers.index(col)
                line.append(self.aux_vals[header_index])

            elif col in extra:
                line.append(extra[col])

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

    def db_id(self, tweet):
        return str(tweet['db_id'])

    def text(self, tweet):
        return self.cleaner.clean(tweet['text'])

    def tweet_id(self, tweet):
        if type(tweet['id']) == list:
            return str(tweet['id'][0])
        else:
            return str(tweet['id'])

    def first_level_codes(self, tweet):
        if 'codes'in tweet.keys():
            result = []
            for container in tweet['codes']:
                result.append(container['first'])
            return ', '.join(sorted(result))
        else:
            return ''

    def second_level_codes(self, tweet):
        if 'codes'in tweet.keys():
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
            return ', '.join(sorted(result))
        else:
            return ''

    def final_codes(self, tweet):
        result = []
        if 'first_final' in tweet:
            result.append(tweet['first_final'])

        if 'second_final' in tweet:
            second_final = tweet['second_final']
            for code in second_final:
                if code != 'Adjudicate':
                    result.append(code)

        return ', '.join(sorted(result))

    def time(self, tweet):
        pass

#####################################
#     Testing Stuff For Testing     #
#####################################


def test(db, rumor):
    import utils
    mongo = utils.mongo_connect(db, rumor)
    test = mongo.find({}).limit(10)
    e = TweetExporter(
        'test.csv',
        ["db_id", "tweet_id", "text"],
        {'rumor': rumor},
        ["db_id", "rumor", "tweet_id", "text"]
    )
    for t in test:
        e.export_tweet(t)

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
