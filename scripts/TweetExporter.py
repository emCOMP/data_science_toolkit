import csv
from TweetCleaner import TweetCleaner


class TweetExporter(object):

    '''
    Parameters:
        path<str>: The destination file-path to write output.
        export_cols<[str]>: The columns to include in output.

        aux_cols<{str: str}>: Keys are extra column names, values are
                                the value to write in that column.

                                Ex. {'rumor': 'sunil'} will include
                                    an extra column called 'rumor'
                                    with a value of 'sunil'.

        order_override<[str]>: An ordered list of the export columns
                                which will specif the order in which
                                the columns are written to the file.
    '''

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

        # The csvwriter object to write the file.
        self.writer = self.__init_output__(path)

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

    '''
    Function:
        Writes a tweet to the TweetExporter's output file.

    '''

    def export_tweet(self, tweet):

        line = []
        for col in self.output_order:
            # If the column is a built-in...
            if col in self.export_cols:
                # Get the generator function
                generator = self.__getattribute__(col)
                # Call it on the provided tweet.
                line.append(generator(tweet))

            # Otherwise it must be an aux column...
            elif col in self.aux_headers:
                # Retrive the provided aux value.
                header_index = self.aux_headers.index(col)
                line.append(self.aux_vals[header_index])

        # Write to the file.
        self.writer.writerow(line)


##########################################
#     Define Column Behaviours Here      #
##########################################

#   Note: 'tweet' is a single tweet object
#           in all of the methods below.

    def db_id(self, tweet):
        return str(tweet['_id'])

    def text(self, tweet):
        return self.cleaner.clean(tweet['text'])

    def tweet_id(self, tweet):
        if type(tweet['id']) == list:
            return str(tweet['id'][0])
        else:
            return str(tweet['id'])


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
