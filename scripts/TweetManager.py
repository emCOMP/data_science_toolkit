import argparse
import random
import csv
import os
import nltk
import utils
import config
import json
from TweetCleaner import TweetCleaner
from TweetExporter import TweetExporter


class TweetManager(object):

    def __init__(self, args):
        # name of the event's db
        self.event = args.db_name

        # name of the rumor to work with
        self.rumor = args.rumor_name

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

        self.use_tool = args.coding_tool

        if self.use_tool:
            self.tool_path = args.tool_path
            with open(args.usernames, 'rb') as f:
                self.tool_users = json.loads(f.read())

        self.action = args.action

        # Run action-specific initialization.
        if args.action == 'generate_training':
            self.__init_training__(args)
        elif args.action == 'generate_coding':
            self.__init_coding__(args)
        elif args.action == 'generate_adjudication':
            self.__init_adjudicate__(args)
        elif args.action == 'upload_adjudication':
            self.__init_adjudicate__(args)

    def __init_training__(self, args):
        # Modify the export columns.
        export_cols = args.export_cols
        export_cols.remove('db_id')

        # An exporter to handle tweet export.
        self.exporter = TweetExporter(
            args.export_path,
            export_cols,
            args.aux_cols,
            args.col_order
        )

    def __init_coding__(self, args):
        # Check to see if we have a compression database
        compression_exists = bool(self.compression.find_one())

        # If we don't have a compression database...
        if not compression_exists:
            # Compress before we generate the sheet.
            self.__compress__()

        self.coders_per_tweet = args.coders_per

        # Read the Coder Assigments csv.
        with open(args.coder_assignments, 'rb') as f:
            reader = csv.DictReader(f)
            # Make a dict of {coder_name:load}
            self.coders = {str(row['coder']): int(row['load'])
                           for row in reader}
            # We will keep this list in case we need to assign
            # extra tweets. (Due to the random assignment
            # sometimes the load can get shifted by a couple tweets).
            self.backup_coders = []

        # Check to make sure the assignment numbers add up.
        tweets_to_code = self.compression.count() * self.coders_per_tweet
        tweets_assigned = sum(self.coders.values())
        if tweets_to_code > tweets_assigned:
            diff = tweets_to_code - tweets_assigned
            raise ValueError(
                str(diff) + ' tweets are not assigned. Check your math?'
            )
        else:
            # Make a dict of {coder_name:coder's exporter}
            self.sheets = {}
            for coder_name in self.coders.keys():
                # Create an exporter object for the coder.
                exporter = TweetExporter(
                    args.directory + '/' + coder_name + '.csv',
                    args.export_cols,
                    args.aux_cols,
                    args.col_order
                )
                self.sheets[coder_name] = exporter

    def __init_adjudicate__(self, args):

        # Check to see if we have a compression database
        compression_exists = bool(self.compression.find_one())

        # If we don't have a compression database...
        if not compression_exists:
            # Raise error
            raise ValueError(
                'No compression database exists for rumor: ' + self.rumor +
                '\n Please verify the database and event names.'
            )

        # DB Holds all of the codes for a given set of tweets.
        self.code_comparison = utils.mongo_connect(
            db_name='code_comparison',
            collection_name=self.rumor)
        # DB mapping coder names to coder ids
        self.coders = utils.mongo_connect(
            db_name='coders',
            collection_name='coders')
        # first level codes (pick 1, mutually exclusive)
        self.first_codes = args.first_level_codes
        # second level codes (choose any)
        self.second_codes = args.second_level_codes

        # Ensure the skip_codes is a subset of the first_level codes.
        skip_codes = args.skip_second_code
        if not set(skip_codes).issubset(set(self.first_codes)):
            raise ValueError(
                'skip_second_code is not a subset of first_level_codes'
            )
        else:
            self.skip_second_code = skip_codes

        self.coders_per_tweet = args.coders_per
        self.sheet_dir = args.sheet_dir
        self.infer_coder_names = args.infer_coder_names

        # Read the Adjudicator Assigments csv.
        with open(args.adjudicator_assignments, 'rb') as f:
            reader = csv.DictReader(f)
            # Make a dict of {adjudicator_name:percent}
            self.adjudicators = {str(row['adjudicator']): float(row['load'])
                                 for row in reader}

        # Check to make sure the assignment numbers add up.
        total = sum(self.adjudicators.values())
        if total > 1.:
            raise ValueError(
                'Loads do not add up to 1. (adjudication loads are percentages)\
                Check your math?'
            )

    # Helper method for mapping coder names to coder ids
    # if no name exists, create a new coder
    def __get_db_coder__(self, coder_name, coder_id=None):
        if not coder_name and not coder_id:
            raise TypeError
        elif coder_name:
            coder = self.coders.find_one({'name': coder_name})
            if coder:
                return coder
        elif coder_id:
            coder = self.coders.find_one({'coder_id': coder_id})
            if coder:
                return coder
        try:
            coder_id = self.coders.find().sort('coder_id', -1).limit(1).next()
            coder_id = coder_id['coder_id'] + 1
        except StopIteration:
            coder_id = 0
        print 'Cannot find existing entry for coder: ', str(coder_name)
        print 'Add to database? (Y/n)'
        user_in = raw_input('>>')
        if user_in == 'Y':
            coder = {'name': coder_name,
                     'coder_id': coder_id}
            self.coders.insert(coder)
            return coder
        else:
            print 'Aborting...'
            exit()

    '''
    Returns:
        <bool>: Whether or not to continue running.
    '''

    def __handle_existing_codes__(self):
        print 'WARNING: Codes alreay present in database!'
        print 'Select an action:',
        print 'Overwrite Existing Codes (!w)'
        print 'Upload anyway (u)'
        print 'Abort (a)'
        user_in = raw_input('>>')
        if user_in == '!w':
            print 'You have specified you want to overwrite.'
            print 'DO NOT PROCEED UNLESS YOU ARE SURE!'
            print 'Proceed?(Y/n)'
            confirm = raw_input('>>')
            if confirm == 'Y':
                self.code_comparison.drop()
            else:
                exit()
        elif user_in == 'u':
            print 'You have specified you want to upload anyway.'
            print 'CAUTION:\tTHIS ACTION CANNOT BE UNDONE'
            print 'Proceed?(Y/n)'
            confirm = raw_input('>>')
            if confirm != 'Y':
                exit()
        else:
            exit()

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
            tweet_list = self.__find_tweets__()

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
            tweet_list = self.__find_tweets__()
        try:
            count = self.compression.find().sort(
                'db_id', -1).limit(1).next()['db_id'] + 1
        except StopIteration:
            count = 0

        print 'Compressing...'
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

    '''
    Function:
        Creates a collection in the rumor_compression database
        which maps duplicate tweets to a single representative.
        (The representative is coded, then the codes are propagated
         to the other related tweets.)
    '''

    def compress(self, args):
        # Check to make sure compression hasn't already been run
        check = self.compression.find_one()
        if check:
            print 'This rumor has already been compressed!'
            print 'Please drop the collection manually if \
                    you need to compress again'
        else:
            self.__compress__()

    '''
    Function:
        Generates a random sample of tweets for training.
        Uses edit distance to ensure a diverse sample.

    Parameters:
        args.sample_size <int>: Number of tweets desired for the sample.
        args.edit_distance <int>: The minimum edit_distance for a tweet
                                    to be considered unique.
    '''

    def generate_training(self, args):
        sample_size = args.sample_size
        edit_distance = args.edit_distance

        # Get the whole set of tweets.
        tweet_list = self.__find_tweets__()
        print 'Selecting ' + str(sample_size) + ' unique tweets...'

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

        # If we're uploading to the coding tool...
        if self.use_tool:
            # Upload everything.
            self.__upload_to_coding_tool__()

    '''
    Function:
        Helper for generate_coding:
            Assigns a tweet to the appropriate number of coders
            for coding and writes it to their respective csv files.
    '''

    def __delegate__(self, tweet):
        # If we need to assign extra tweets (in order to ensure)
        # each tweet is covered by the desired number of coders.
        if len(self.coders.keys()) < self.coders_per_tweet:
            # Bring each backup coder in for 1 more tweet.
            for b in self.backup_coders:
                self.coders[b] = 1

            # Clear the backup list
            self.backup_coders = []

        # Get the list of availiable coders.
        avaliable_coders = self.coders.keys()

        for i in range(self.coders_per_tweet):
            # Choose a coder at random.
            cur_coder = random.choice(avaliable_coders)
            # Write the tweet to thier sheet.
            self.sheets[cur_coder].export_tweet(tweet)

            # Remove them from the avaliable coders
            # so we don't assign this tweet to the same person.
            avaliable_coders.remove(cur_coder)

            # Decrement the coder's load by 1.
            self.coders[cur_coder] -= 1

            # If they've reached the number of tweets
            # assigned to them, stop assigning them tweets.
            if self.coders[cur_coder] <= 0:
                del self.coders[cur_coder]

                # Add them to backup in case we go over.
                self.backup_coders.append(cur_coder)

    '''
    Function:
        Uploads one csv sheet to the coding tool
        using the TweetManager's rumor and the
        provided csv_path and coder_name.

    Parameters:
        csv_path <str>: path to the csv file to be uploaded
        coder_name <str>: name of the coder who will recieve the sheet
    '''

    def __upload_one__(self, csv_path, coder_name):
        # Build up the command line call to the uploader.
        command = self.tool_path + ' import_csv'
        command += ' ' + ' '.join([csv_path, self.rumor, coder_name])
        command += ' --codescheme misinfo-first'
        command += ' --codescheme misinfo-second'
        command += ' --codescheme misinfo-aux'

        # Call the command.
        os.system(command)

    '''
    Function:
        Uploads all sheets to the coding tool.
        (Adapts to the 'action' being performed by the TweetManager.)
    '''
    def __upload_to_coding_tool__(self):
        # If we're outputting training...
        if self.action == 'generate_training':
            # Use all known users on coding tool and use the path to the
            # training sheet as everyone's path.
            outputs = {coder_name: self.exporter.get_path()
                       for coder_name in self.tool_users.values()}

        # If we're outputting coding...
        elif self.action == 'generate_coding':
            # Grab the names and paths from the sheets object.
            # (sheets is created in __delegate__)
            outputs = {self.tool_users[coder_name]: exporter.get_path()
                       for coder_name, exporter in self.sheets.iteritems()}

        # Upload each sheet to the tool.
        for coder_name, path in outputs.iteritems():
            self.__upload_one__(path, coder_name)

    '''
    Function:
        Exports an entire rumor to coding sheets.
    '''

    def generate_coding(self, args):
        print 'Gathering tweets...'
        # Get the full list of tweets.
        tweet_list = self.compression.find({})
        print 'Allocating...'
        for tweet in tweet_list:
            # Get the full tweet object from the rumor database.
            # ('tweet' is an object from the compression database so it's
            #   missing some text information)
            full_tweet = self.rumor_collection.find_one({'id': tweet['id'][0]})

            # If the tweet exists...
            if full_tweet is not None:
                tweet['text'] = full_tweet['text']
                self.__delegate__(tweet)

        # If we're uploading to the coding tool...
        if self.use_tool:
            # Upload everything.
            self.__upload_to_coding_tool__()


    def __upload_all__(self):
        print 'Uploading codes from sheets...'

        if self.action == 'generate_adjudication':
            # Check if we've already imported these codes.
            already_imported = bool(self.code_comparison.find_one())
            if already_imported:
                # Handle the conflict.
                self.__handle_existing_codes__()

        # Read all of the files from the provided directory.
        for filename in os.listdir(self.sheet_dir):
            # If the file is a csv...
            if filename.endswith('.csv'):

                # The filepath to this csv.
                path = self.sheet_dir + '/' + filename

                # If we're generating adjudication sheets...
                if self.action == 'generate_adjudication':
                    # Get the coder's name.
                    if self.infer_coder_names:
                        coder_name = filename.strip('.csv')
                    else:
                        print 'enter coder name (file: %s)' % filename
                        coder_name = raw_input('>> ')

                    # Retrive their database entry.
                    coder = self.__get_db_coder__(coder_name=coder_name)
                    # Read the codesheet passing in a coder.
                    self.__handle_sheet__(path, coder)
                else:
                    # Only pass the path.
                    self.__handle_sheet__(path)

    def __auto_adjudicate__(self):
        print 'Auto-adjudicating...'
        # Get all of the tweets with codes uploaded.
        tweets = self.code_comparison.find()
        for tweet in tweets:
            code_counts = {}

            for codes in tweet['codes']:
                # Count the first code votes for the tweet.
                code_counts[codes['first']] = code_counts.get(
                    codes['first'], 0) + 1

                # Count the votes for each second-level code.
                for code in self.second_codes:
                    code_counts[code] = code_counts.get(
                        code, 0) + codes.get(code, 0)

            #                               #
            # -------- First Level -------- #
            #                               #
            # Sort our list of first codes by the number of marks each one got.
            self.first_codes.sort(
                key=lambda x: code_counts.get(x, 0),
                reverse=True
            )
            # The most popular first-level code for this tweet.
            popular_code = code_counts.get(self.first_codes[0], 0)

            # If the most popular choice was chosen by a majority...
            if float(popular_code) / self.coders_per_tweet > .5:
                # Mark that code as the final first-level code.
                first_final = self.first_codes[0]
            else:
                # Otherwise, mark it for adjudication.
                first_final = 'Adjudicate'

            #                                #
            # -------- Second Level -------- #
            #                                #
            # Only adjudicate the second level if
            # the first-level code is one which
            # allows second-level codes
            # (ex. ignore second-level codes for 'unrelated' tweets.)
            #
            # The final second-level codes for this tweet.
            second_final = []
            if first_final not in self.skip_second_code:
                # For each of the second level codes...
                for code in self.second_codes:
                    # If only one person marked a second level code...
                    if code_counts[code] == 1:
                        # Mark tweet for adjudication.
                        second_final = ['Adjudicate']
                        break
                    # If more than half marked this code...
                    elif float(code_counts.get(code, 0)) / self.coders_per_tweet > .5:
                        # Add this code to the final codes for the tweet.
                        second_final.append(code)

            #                               #
            # -------- Write Codes -------- #
            #                               #
            # Update the database with the auto-adjudicated codes.
            self.code_comparison.update(
                {'db_id': tweet['db_id']},
                {'$set':
                 {
                     'first_final': first_final,
                     'second_final': second_final
                 }
                 }
            )

    def __delegate_adjudication__(self, args):

        for i in range(2):
            if i == 0:
                query = {'first_final': 'Adjudicate'}
                export_cols = args.export_cols + ['first_level_codes', 'second_level_codes']
                export_cols.remove('tweet_id')
                suffix = '_level1.csv'
            else:
                query = {'second_final': 'Adjudicate'}
                export_cols = args.export_cols + \
                    ['final_codes', 'second_level_codes']
                export_cols.remove('tweet_id')
                suffix = '_level2.csv'

            tweets = self.code_comparison.find(query)
            num_tweets = self.code_comparison.find(query).count()
            count = float(num_tweets)

            # The loads for each adjudicator for this level.
            loads = {k: int(count * v) + 1
                     for k, v in self.adjudicators.iteritems()}

            # Make a dict of {adjudicator_name: exporter}
            sheets = {}
            for adj_name in self.adjudicators.keys():
                # Create an exporter object for the coder.
                exporter = TweetExporter(
                    args.directory + '/' + adj_name + suffix,
                    export_cols,
                    args.aux_cols,
                    args.col_order
                )
                sheets[adj_name] = exporter

            for tweet in tweets:
                if len(loads) == 0:
                    raise ValueError(
                        'Ran out of adjudicators while delegating.'
                    )
                # Choose a random adjudicator.
                cur_adj = random.choice(loads.keys())
                # Write the tweet to thier sheet.
                sheets[cur_adj].export_tweet(tweet)
                # Decrement thier load.
                loads[cur_adj] -= 1

                # Stop assigning them tweets if
                # they've reached capacity.
                if loads[cur_adj] <= 0:
                    del loads[cur_adj]
                    del sheets[cur_adj]
    '''
    Function:
        Imports codes into the database, performs auto-adjudication
        and then outputs adjudication sheets.
    '''
    def generate_adjudication(self, args):
        self.__upload_all__()
        self.__auto_adjudicate__()
        self.__delegate_adjudication__(args)

    def __upload_adjudication__(self, db_id, codes):
        
        # Create our update object.
        # (Adding a field to mark that the tweet was
        #  adjudicated.)
        update = {'$set':{'adjudicated':True}}
        
        # If there is a first code to update...
        if codes['first_level'] is not None:
            update['$set'].update({'first_final': codes['first_level']})

        # If there are second level codes to update...
        if any(codes['second_level']):
            # Remove the adjudicate code.
            self.code_comparison.update(
                {'db_id': db_id},
                {'$pull':{'second_final':'Adjudicate'}},
                upsert=True
            )

            # Add an operation to our update to add the new
            # second level codes.
            update['$addToSet'] = {
                        'second_final': {'$each': codes['second_level']}
                        }
        # If the tweet was marked as having no second level code.
        elif codes['no_second_code']:
            # Remove the adjudicate code.
            self.code_comparison.update(
                {'db_id': db_id},
                {'$pull':{'second_final':'Adjudicate'}},
                upsert=True
            )

        # Insert the codes into the database.
        self.code_comparison.update(
            {'db_id': db_id},
            update,
            upsert=True
        )


    def __upload_codes__(self, db_id, text, codes, coder):
        # Create the upload_codes object.
        upload_codes = {
                'coder_id': coder['coder_id'],
                'first': codes['first_level'],
                codes['first_level']: 1
            }

        # Format the second level codes:
        second_level = {c: 1 for c in codes['second_level']}

        # Add the second level codes into the dictionary.
        upload_codes.update(second_level)

        # Insert the codes into the database.
        self.code_comparison.update(
            {'db_id': db_id},
            {
                '$setOnInsert': {'text': text},
                '$addToSet': {'codes': upload_codes}
            },
            upsert=True
        )

    '''
    Function:
        Handles reading in one csv sheet.
        (Handles both coding-sheets and adjudication-sheets.)

    Parameters:
        path <str>: A filepath to the codesheet to be read.
        coder <coder_object>: A coder object returned by __get_db_coder__()
    '''
    def __handle_sheet__(self, path, coder=None):
        # Read the code sheet.
        with open(path, 'rb') as f:
            codesheet = csv.DictReader(f)

            # For each tweet on the sheet...
            for row in codesheet:
                # Read the tweet information.
                db_id = row['db_id']
                text = row['text'].decode('latin-1').encode('utf-8')

                # Read the codes.
                codes = {'first_level': None, 'second_level': []}
                for col_name in row.keys():
                    # If the column contains a value...
                    if row[col_name]:
                        if col_name in self.first_codes:
                            codes['first_level'] = col_name
                        elif col_name in self.second_codes:
                            codes['second_level'].append(col_name)
                        elif col_name.lower() == 'no_second_code':
                            codes['no_second_code'] = True
                if db_id:
                    # Handle the reading of the sheet depending on action.
                    if self.action == 'generate_adjudication':
                        self.__upload_codes__(db_id, text, codes, coder)

                    elif self.action == 'upload_adjudication':
                        self.__upload_adjudication__(db_id, codes)

    '''
    Function:
        Uploads adjudicated tweets to the database.
    '''
    def upload_adjudication(self, args):
        self.__upload_all__()




# !!!WIP!!!
def validate_args(action, args):
    # A list of required arguments for each action.
    mappings = {
        'compress': [],
        'generate_training': ['sample_size', 'edit_distance'],
        'generate_coding': ['coders', 'assignment_sheet']
    }
    arg_vals = vars(args)

    # Verify that a valid action was passed.
    if action in mappings:
        for req in mappings[action]:
            # If any of the required args we not passed.
            if req not in arg_vals.keys():
                return False
        return True
    else:
        raise ValueError('Invalid action specified: ' + action)


def main(args):
    tm = TweetManager(args)
    action = tm.__getattribute__(args.action)
    action(args)

    exit()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Manages tweet flow between the database,\
                    spreadsheets, and the coding tool.')

    # General Args.
    general = parser.add_argument_group('General')
    general.add_argument(
        'action', help='What to do with the tweets.',
        choices=[
            'compress',
            'generate_training',
            'generate_coding',
            'generate_adjudication',
            'upload_adjudication'
        ],
        type=str)
    general.add_argument(
        'db_name', help='The name of the database to use.', type=str)
    general.add_argument(
        'rumor_name', help='The name of the rumor to use.', type=str)
    general.add_argument(
        '-ct', '--coding_tool',
        help='Upload output to the coding tool automatically.',
        type=bool, required=False, default=False)

    coding = parser.add_argument_group('Coding Related')
    coding.add_argument(
        '-c', '--coders_per', help='The number of coders per tweet.\
                                (Not required for generate_sample)',
        type=int, required=False, default=3)
    coding.add_argument(
        '-flc', '--first_level_codes', help='Mutually exclusive codes.',
        type=str, required=False,
        nargs='*', default=[
            'Uncodable',
            'Unrelated',
            'Affirm',
            'Deny',
            'Neutral']
    )
    coding.add_argument(
        '-slc', '--second_level_codes',
        help='Secondary codes (non-mutually exclusive)',
        type=str, required=False,
        nargs='*', default=['Uncertainty', 'Ambiguity', 'Implicit'])

    output = parser.add_argument_group('Output Options')
    output.add_argument(
        '-ec', '--export_cols', help='Which columns to export.',
        type=str, required=False,
        nargs='*', default=["db_id", "tweet_id", "text"])
    output.add_argument(
        '-aux', '--aux_cols', help='Auxilliary columns (filled with \
                                    user-specified values.)',
        type=dict, required=False, default={})
    output.add_argument(
        '-co', '--col_order', help='Override the output order of csv columns.',
        type=str, required=False,
        nargs='*', default=None)

    tool = parser.add_argument_group('Coding Tool')
    tool.add_argument(
        '-ctp', '--tool_path',
        help='Path to the coding tool script.',
        type=str, required=False,
        default='/var/www/coding_experiment/manage.py')
    tool.add_argument(
        '-un', '--usernames',
        help='Path to the json file containing username \
                mappings for the coding tool.',
        type=str, required=False,
        default='coding_tool_ids.json')

    # Args for generate_training().
    training = parser.add_argument_group('Generate Training')
    training.add_argument(
        '-p', '--export_path', help='File path to use for export.',
        type=str, required=False, default='../samples/sample.csv')
    training.add_argument(
        '-ss', '--sample_size',
        help='Number of tweets desired for the sample.',
        type=int, required=False, default=80)
    training.add_argument(
        '-ed', '--edit_distance', help='The minimum edit_distance for a tweet\
                                        to be considered unique.',
        type=int, required=False, default=40)

    # Args for generate_coding().
    gen_coding = parser.add_argument_group('Generate Coding')
    gen_coding.add_argument(
        '-dir', '--directory', help='Path to output folder for sheets.',
        type=str, required=False, default='../sheets')
    gen_coding.add_argument(
        '-ca', '--coder_assignments',
        help='A path to a csv containing coder names and the number\
                of tweets each will code.',
        type=str, required=False, default='../sheets/coder_assignments.csv')

    # Args for generate_adjudication().
    adjudicate = parser.add_argument_group('Adjudicate')
    adjudicate.add_argument(
        '-sd', '--sheet_dir', help='Path to input folder for \
                                    completed coding/adjudication sheets.',
        type=str, required=False, default='../codes')
    adjudicate.add_argument(
        '-aa', '--adjudicator_assignments',
        help='A path to a csv containing adjudicator \
            names and the number of tweets each will adjudicate.',
        type=str, required=False,
        default='../sheets/adjudicator_assignments.csv')
    adjudicate.add_argument(
        '-icn', '--infer_coder_names',
        help='If set to true the script will use the filenames of the \
                coding sheets as the names of the coders.',
        type=bool, required=False,
        default=True)
    adjudicate.add_argument(
        '-ssc', '--skip_second_code',
        help='First level codes for which to ignore second level codes.',
        type=str, required=False,
        nargs='*', default=[
            'Uncodable',
            'Unrelated']
    )

    args = parser.parse_args()
    main(args)
