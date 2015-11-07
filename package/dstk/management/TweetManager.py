import random
import csv
import os
import json
import nltk
import re
from dstk.database import utils
from dstk.database import config
from dstk.processing.TweetCleaner import TweetCleaner
from dstk.processing.TweetExporter import TweetExporter


class TweetManager(object):
    """
    Manages the movement of tweets through the qualitative
    coding pipeline.
    """
    def __init__(self, args):
        # name of the event's db
        self.event = args.db_name

        # name of the rumor to work with
        self.rumor = args.rumor_name

        # the action the manager will be performing.
        self.action = args.action

        # connects to the appropriate database for the action
        self.__connect_dbs__(self.action)

        # The directory to upload files from.
        self.upload_dir = args.upload_dir
        self.use_tool = args.coding_tool
        self.status_log = self.__get_status_document__()

        if self.use_tool:
            self.tool_path = args.tool_path
            with open(args.usernames, 'rb') as f:
                self.tool_users = json.loads(f.read())

        # first level codes (pick 1, mutually exclusive)
        self.first_codes = args.first_level_codes
        # second level codes (choose any)
        self.second_codes = args.second_level_codes

        # These are the second-level codes for which
        # we want to adjudicate.
        self.second_level_adj_codes = ['Uncertainty']

        # First level codes for which we want to skip assigning second
        # level codes (unrelated/uncodable shouldn't have 2nd level codes)
        skip_codes = args.skip_second_code
        # Ensure the skip_codes is a subset of the first_level codes.
        if not set(skip_codes).issubset(set(self.first_codes)):
            raise ValueError(
                'skip_second_code is not a subset of first_level_codes'
            )
        else:
            self.skip_second_code = skip_codes

        self.coders_per_tweet = args.coders_per
        self.infer_coder_names = args.infer_coder_names

        # A cleaner to clean our tweets for comparison purposes.
        cleaner_settings = {
            'scrub_retweet_text': True,
            'scrub_mentions': True,
            'scrub_url': True
        }
        self.cleaner = TweetCleaner(
            all_ops=False, user_settings=cleaner_settings)

        # Run action-specific initialization.
        if args.action == 'generate_training':
            self.__init_training__(args)
        elif args.action == 'generate_coding' or args.action == 'generate_recodes':
            self.__init_coding__(args)
        elif args.action == 'generate_adjudication':
            self.__init_adjudicate__(args)
        elif args.action == 'upload_adjudication':
            self.__init_adjudicate__(args)

    def __connect_dbs__(self, action):
        """
        Connects to the appropriate databases needed
        to complete the 'action'.

        Args:
            action (str): the name of the action which
                          the TweetManager is going to do.
                          (taken from args)
        """
        # db containing all event tweets
        self.db = utils.mongo_connect(db_name=self.event)

        # db for mapping unique tweets to non-uniques
        self.compression = utils.mongo_connect(db_name='rumor_compression',
                                               collection_name=self.rumor)

        # db containing metadata about the rumor
        self.rumor_metadata = utils.mongo_connect(db_name='rumor_metadata',
                                                  collection_name=self.rumor)

        # db collection for the individual rumor
        self.rumor_collection = self.__create_rumor_collection__()

        code_related_actions = ['upload_coding', 'upload_adjudication',
                                'generate_coding', 'generate_adjudication',
                                'propagate_codes', 'generate_recodes']
        if action in code_related_actions:
            # db Holds all of the codes for a given set of tweets.
            self.code_comparison = utils.mongo_connect(
                                        db_name='code_comparison',
                                        collection_name=self.rumor)
            # db mapping coder names to coder ids
            self.coders_db = utils.mongo_connect(
                                db_name='coders',
                                collection_name='coders')

    def __init_training__(self, args):
        # Make sure the rumor is compressed.
        self.__verify_compression__()
        # An exporter to handle tweet export.
        self.exporter = TweetExporter(
            args.export_path,
            args.export_cols,
            args.aux_cols,
            args.col_order
        )

    def __init_coding__(self, args):
        self.__verify_compression__()
        self.coders_per_tweet = args.coders_per

        # Initialize, look into scope issues?
        tweets_to_code = 0

        if args.action == 'generate_recodes':
            q = {'$and':[{'first_final':{'$ne':code}} for code in self.skip_second_code]}
            tweets_to_code = self.compression.find(q).count() * self.coders_per_tweet
        if args.action == 'generate_coding':
            tweets_to_code = self.compression.count() * self.coders_per_tweet

        # Read the Coder Assigments csv.
        with open(args.coder_assignments, 'rb') as f:
            reader = csv.DictReader(f)
            # Make a dict of {coder_name:load}
            self.coders = {
                str(row['coder']): 1 + int(float(row['load']) * tweets_to_code)
                for row in reader}
            # We will keep this list in case we need to assign
            # extra tweets. (Due to the random assignment
            # sometimes the load can get shifted by a couple tweets).
            self.backup_coders = []

        # Check to make sure the assignment numbers add up.
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
        # What level of codes we're adjudicating
        if not args.adjudication_level:
            raise ValueError('No adjudication level provided!')
        else:
            self.adjudication_level = args.adjudication_level

            # This will be used to update the rumor_metadata
            if self.adjudication_level == 'first':
                self.adj_meta_prefix = 'adjudication1'

            elif self.adjudication_level == 'both':
                self.adj_meta_prefix = 'adjudication_both'

            elif self.adjudication_level == 'second':
                self.adj_meta_prefix = 'adjudication2'

        # Check to see if we have a compression database
        compression_exists = bool(self.compression.find_one())

        # If we don't have a compression database...
        if not compression_exists:
            # Raise error
            raise ValueError(
                'No compression database exists for rumor: ' + self.rumor +
                '\n Please verify the database and event names.'
            )

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

    def __verify_compression__(self):
        """
        Checks to see if the rumor database has been compressed.
        (If it has not, compresses it.)
        """
        # Check to see if we have a compression database
        compression_exists = bool(self.compression.find_one())

        # If we don't have a compression database...
        if not compression_exists:
            # Compress before we generate the sheet.
            self.__compress__()

    # Returns the status document for this rumor from the rumor_metadata
    # database. (Initializes it if there isn't one.)
    def __get_status_document__(self):
        """
        Retrives the metadata document containing the status
        of the rumor. (Creates one if it does not exist.)

        Returns:
            (dict): The metadata document for this rumor from
                    the rumor_metadata database.
        """
        # Check to see if there is an existing status document.
        check = list(self.rumor_metadata.find({'metadata': 'status'}))

        if check:
            return check[0]

        # Initialize the record if we don't have one.
        else:
            print 'Creating metadata document...'
            self.rumor_metadata.insert(
                {'metadata': 'status',
                 'collection_complete': True,
                 'collection_coverage_analyzed': False,
                 'coding_assigned': False,
                 'coding_uploaded': False,
                 'auto_adjudicated': False,
                 'adjudication1_assigned': False,
                 'adjudication1_uploaded': False,
                 'adjudication_both_assigned': False,
                 'adjudication_both_uploaded': False,
                 'adjudication2_assigned': False,
                 'adjudication2_uploaded': False,
                 'final_codes_propagated': False
                 }
            )

            return list(self.rumor_metadata.find({'metadata': 'status'}))[0]

    def __update_rumor_status__(self, status, value=True):
        # Ensure the document exists.
        if self.__get_status_document__():
            # Update with the desired value.
            self.rumor_metadata.update(
                {'metadata': 'status'},
                {'$set': {status: value}},
                upsert=True
            )
        else:
            raise KeyError(
                'No status document found for the rumor: ' + self.rumor)

    # Helper method for mapping coder names to coder ids
    # if no name exists, create a new coder
    def __get_db_coder__(self, coder_name, coder_id=None):
        if not coder_name and not coder_id:
            raise TypeError
        elif coder_name:
            coder = self.coders_db.find_one({'name': coder_name})
            if coder:
                return coder
        elif coder_id:
            coder = self.coders_db.find_one({'coder_id': coder_id})
            if coder:
                return coder
        try:
            coder_id = self.coders_db.find().sort('coder_id', -1).limit(1).next()
            coder_id = coder_id['coder_id'] + 1
        except StopIteration:
            coder_id = 0
        print 'Cannot find existing entry for coder: ', str(coder_name)
        print 'Add to database? (Y/n)'
        user_in = raw_input('>>')
        if user_in == 'Y':
            coder = {'name': coder_name,
                     'coder_id': coder_id}
            self.coders_db.insert(coder)
            return coder
        else:
            print 'Aborting...'
            exit()

    def __handle_existing_codes__(self):
        """
        Handles the case where codes already exist in the
        code_comparison database.

        Returns:
            (bool) Whether or not to continue running.
        """
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
            tweet_list.close()

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
        tweet_list = self.db.find(query, timeout=False)
        return tweet_list

    # Helper method for creating a list of unique tweets from a rumor
    def __compress__(self, sample=False):
        cleaner_settings = {
            'scrub_retweet_text': True,
            'scrub_url': True,
            'scrub_mentions': True,
            'scub_newlines': True,
            'scrub_nonstandard_punct': True
        }
        cleaner = TweetCleaner(
            all_ops=False, user_settings=cleaner_settings)

        if sample:
            tweet_list = self.rumor_collection.find({'sample': True}, timeout=False)
        else:
            tweet_list = self.__find_tweets__()
        try:
            count = self.compression.find().sort(
                'db_id', -1).limit(1).next()['db_id'] + 1
        except StopIteration:
            count = 0

        print 'Compressing...'
        # Get the total number of tweets to compress
        total = self.rumor_collection.count()

        for i, tweet in enumerate(tweet_list):
            print 'Compressing Tweet ', str(i + 1), ' of ', str(total) 
            # Clean the text.
            text = cleaner.clean(tweet['text'])

            # If the tweet is a retweet...
            if 'retweeted_status' in tweet:
                # Get the id of the original
                rt_id = tweet['retweeted_status']['id']

                # If we don't have the original
                if self.compression.find_one({'id': rt_id}) is None:
                    # If we don't have another retweet stored already...
                    if self.compression.find_one({'retweeted_status.id': rt_id}) is None:
                        # Add a new entry to the database.
                        self.compression.insert({'db_id': count,
                         'rumor': self.rumor,
                         'text': text,
                         'id': [tweet['id']]})

                    else:
                        self.compression.update({'retweeted_status.id': rt_id},
                            {'$addToSet': {'id': tweet['id']}})
                else:
                    self.compression.update({'id': rt_id},
                        {'$addToSet': {'id': tweet['id']}})
            else:
                # WIP Code for truncation detection.
                # truncated = re.search(r'\.\.\.$', text)
                # if truncated:
                #     # Remove the truncated word and the elipis.
                #     non_truncated_words = text.split()[:-1]
                #     non_truncated_text = re.escape(' '.join(non_truncated_words))
                #     # Create regex to match the non-truncated part of the text
                #     # (starting from the beginning of the tweet.)
                #     reg = re.compile(r'^' + non_truncated_text, re.IGNORECASE)
                #     # If we do find a match...
                #     if self.compression.find_one({'text': {'$regex': reg}}) is not None:
                #         self.compression.update({'text': text},
                #             {'$addToSet': {'id': tweet['id']}})
                #     else:
                #         # Add a new entry to the database.
                #         self.compression.insert({'db_id': count,
                #                                  'rumor': self.rumor,
                #                                  'text': text,
                #                                  'id': [tweet['id']]})

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
        tweet_list.close()

    def compress(self, args):
        """
        Creates a collection in the rumor_compression database
        which maps duplicate tweets to a single representative.
        (The representative is coded, then the codes are propagated
        to the other related tweets.)
        """
        # Check to make sure compression hasn't already been run
        check = self.compression.find_one()
        if check:
            print 'This rumor has already been compressed!'
            print 'Please drop the collection manually if\
                    you need to compress again'
        else:
            self.__compress__()

    def generate_training(self, args):
        """
        Generates a random sample of tweets for training.
        Uses edit distance to ensure a diverse sample.

        Args:
            args.sample_size (int): Number of tweets desired for the sample.
            args.edit_distance (int): The minimum edit_distance for a tweet
                                        to be considered unique.
        """
        sample_size = args.sample_size
        edit_distance = args.edit_distance

        # Get the whole set of tweets.
        tweet_list = self.compression.find({})
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
                result.append(tweet['text'])
                full_tweet = self.rumor_collection.find_one({'id': tweet['id'][0]})
                # Write the tweet to the file.
                self.exporter.export_tweet(full_tweet)

            # If we've achieved the desired 'sample_size', then stop.
            if count >= sample_size:
                break

        # If we're uploading to the coding tool...
        if self.use_tool:
            # Upload everything.
            self.__upload_to_coding_tool__()

    def __delegate__(self, tweet):
        """
        Helper for generate_coding:
        Assigns a tweet to the appropriate number of coders
        for coding and writes it to their respective csv files.
        """
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

    def __upload_one__(self, csv_path, coder_name):
        """
            Uploads one csv sheet to the coding tool
            using the TweetManager's rumor and the
            provided csv_path and coder_name.

            Args:
                csv_path (str): path to the csv file to be uploaded
                coder_name (str): name of the coder who will recieve the sheet
        """
        # Build up the command line call to the uploader.
        command = self.tool_path + ' import_csv'
        command += ' ' + ' '.join([csv_path, self.rumor, coder_name])
        command += ' --codescheme misinfo-first'
        command += ' --codescheme misinfo-second'
        command += ' --codescheme misinfo-aux'

        # Call the command.
        os.system(command)

    def __upload_to_coding_tool__(self):
        """
        Uploads all sheets to the coding tool.
        (Adapts to the 'action' being performed by the TweetManager.)
        """
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

    def generate_coding(self, args):
        """
        Exports an entire rumor to coding sheets,
        assigning each tweet to 'coders_per' coders
        (coders_per is speficied in args). 
        How many tweets are assigned to each coder is
        determined by the coder_assignments.csv 
        speficied in args.
        """

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
        self.__update_rumor_status__('coding_assigned')

    def __upload_all__(self):
        """
        Uploads all of the CSVs in the directory 'upload_dir'
        (speficied in args) to the appropriate database.
        """
        print 'Uploading codes from sheets...'
        # Read all of the files from the provided directory.
        for filename in os.listdir(self.upload_dir):
            # If the file is a csv...
            if filename.endswith('.csv'):

                # The filepath to this csv.
                path = self.upload_dir + '/' + filename

                # If we're generating adjudication sheets...
                if self.action == 'upload_coding':
                    # Get the coder's name.
                    if self.infer_coder_names:
                        coder_name = filename.replace('.csv', '')
                    else:
                        print 'enter coder name (file: %s)' % filename
                        coder_name = raw_input('>> ')

                    # Retrive their database entry.
                    coder = self.__get_db_coder__(coder_name=coder_name)
                    # Read the codesheet passing in a coder.
                    self.__handle_sheet__(path, coder)

                elif self.action == 'upload_adjudication':
                    # Only pass the path.
                    self.__handle_sheet__(path)

    def __auto_adjudicate__(self):
        """
        Adjudicates as many tweets as possible using rule
        based methods, and marks tweets which need human
        adjudication by adding the code 'Adjudicate' to
        the appropriate field in the code_comparison database.
        """
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
                    # How many people marked this code?
                    votes = float(code_counts.get(code, 0))
                    # Percentage of agreement.
                    cur_code_agreement = votes / self.coders_per_tweet
                    # If we're adjudicating this code...
                    if code in self.second_level_adj_codes:
                        # Check if it needs to be adjudicated.
                        # Did a minority mark it?
                        if 0 < cur_code_agreement < .5:
                            second_final = ['Adjudicate']
                    # If more than half marked this code...
                    if cur_code_agreement > .5:
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
        # Record that the rumor has been auto-adjudicated.
        self.__update_rumor_status__('auto_adjudicated')

    def __delegate_adjudication__(self, args):
        """
        Takes tweets from code comparison which meet the
        criteria for the adjudication_level specified
        in args, and outputs them to CSV(s) according
        to the adjudicator_assignments.csv in args.
        """

        # Setup the database query and the columns
        # which will be written to the csv according
        # to the level of adjudication we are assigning.
        if self.adjudication_level == 'first':
            query = {'$and': [
                {'first_final': 'Adjudicate'},
                {'second_final': {'$ne': 'Adjudicate'}}
            ]}
            export_cols = args.export_cols + \
                ['first_level_code_comparison', 'second_level_code_comparison']
            export_cols.remove('tweet_id')
            suffix = '_level1.csv'
        elif self.adjudication_level == 'both':
            query = {'$and': [
                {'first_final': 'Adjudicate'},
                {'second_final': 'Adjudicate'}
            ]}
            export_cols = args.export_cols + \
                ['first_level_code_comparison', 'second_level_code_comparison']
            export_cols.remove('tweet_id')
            suffix = '_both.csv'
        elif self.adjudication_level == 'second':
            query = {'$and': [
                {'first_final': {'$ne': 'Adjudicate'}},
                {'second_final': 'Adjudicate'}
            ]}
            export_cols = args.export_cols + \
                ['final_code_comparison', 'second_level_code_comparison']
            export_cols.remove('tweet_id')
            suffix = '_level2.csv'
        else:
            raise ValueError(
                'Unexpected adjudication_level value: ' +
                str(self.adjudication_level))

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

    def upload_coding(self, args):
        """
        Imports codes into the database
        """
        # Check if we've already imported these codes.
        already_imported = bool(self.code_comparison.find_one())
        if already_imported:
            # Handle the conflict.
            self.__handle_existing_codes__()

        # Upload the codes.
        self.__upload_all__()
        self.__update_rumor_status__('coding_uploaded')
        self.__update_rumor_status__('auto_adjudicated', value=False)

    def generate_adjudication(self, args):
        """
        Performs auto-adjudication (if needed)
        and then outputs adjudication sheets for the
        'adjudication level' specified in the args.
        """
        # Auto adjudicate the rumor if it hasn't been already.
        if not self.status_log['auto_adjudicated']:
            self.__auto_adjudicate__()

        # Loop through the possible adjudication levels...
        adj_levels = ['adjudication1', 'adjudication_both', 'adjudication2']
        for level in adj_levels:
            # If we arrive at the one supplied to args,
            # generate the adjudication.
            if self.adj_meta_prefix == level:
                self.__delegate_adjudication__(args)
                self.__update_rumor_status__(
                    self.adj_meta_prefix + '_assigned')
                break

            # If we encounter an earlier level which has not been
            # uploaded notify the user and abort.
            elif not self.status_log[level + '_uploaded']:
                print '!!!'
                print level, ' has not been uploaded yet.'
                print 'Please upload it before assigning more.'
                exit()

    def __upload_adjudication__(self, db_id, codes):
        # Create our update object.
        # (Adding a field to mark that the tweet was
        #  adjudicated.)
        update = {'$set': {'adjudicated': True}}

        # If there is a first code to update...
        if codes['first_level'] is not None:
            update['$set'].update({'first_final': codes['first_level']})

        # Remove the adjudicate code.
        self.code_comparison.update(
            {'db_id': db_id},
            {'$pull': {'second_final': 'Adjudicate'}},
            upsert=True
        )

        # If there are second level codes to update...
        if any(codes['second_level']):
            # Add an operation to our update to add the new
            # second level codes.
            update['$addToSet'] = {
                'second_final': {'$each': codes['second_level']}
            }
        # If the tweet was marked as having no second level code.
        # elif 'no_second_code' in codes:
        #     # Remove the adjudicate code.
        #     self.code_comparison.update(
        #         {'db_id': db_id},
        #         {'$pull': {'second_final': 'Adjudicate'}},
        #         upsert=True
        #     )

        # Insert the codes into the database.
        self.code_comparison.update(
            {'db_id': db_id},
            update,
            upsert=True
        )

    def __upload_codes__(self, db_id, text, codes, coder):
        """
        Uploads the codes for a single tweet to the code_comparison
        database.

        Args:
            db_id (str): The db_id of the tweet
                        (taken from rumor_compression database)
            text (str): The tweet text
            codes (dict str:str): The codes for the tweet in the format:
                            {'first_level': first_code,
                            'second_level': [second_codes]}
            coder (dict): The coder database object for the coder
                            who assigned these codes.
                            (taken from coders database)

        """
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

    def __handle_sheet__(self, path, coder=None, db_id_str=True):
        """
        Handles reading in one csv sheet.
        (Handles both coding-sheets and adjudication-sheets.)

        Args:
            path (str): A filepath to the codesheet to be read.
            coder (coder_object): A coder object returned by __get_db_coder__()
        """
        # Read the code sheet.
        with open(path, 'rb') as f:
            codesheet = csv.DictReader(f)

            # For each tweet on the sheet...
            for row in codesheet:
                # Read the tweet information.
                db_id = row['db_id']

                # If needed, cast the db_id to a string.
                if db_id_str:
                    db_id = str(db_id)

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
                    if self.action == 'upload_coding':
                        # If after going through all of the columns there still
                        # isn't a first level code...
                        if codes['first_level'] is None:
                            # Prompt the user to code the tweet
                            # on the spot.
                            print '\nSheet:', path
                            print 'Is missing a code for db_id: ', db_id
                            codes = self.__handle_missing_code__(text)

                        self.__upload_codes__(db_id, text, codes, coder)

                    elif self.action == 'upload_adjudication':
                        self.__upload_adjudication__(db_id, codes)

    def propagate_codes(self, args):
        """
        Propagates codes from the code_comparsion database
        which contains only unique tweets, to the event database
        which contains duplicates. (Each duplicate tweet is
        assigned the same code as the corresponding unique tweet).
        """
        print 'Propagating...'
        # Find all of the non adjudicated codes.
        coded_uniques = self.code_comparison.find(
            {'$and': [
                {'first_final': {'$ne': 'Adjudicate'}},
                {'second_final': {'$ne': 'Adjudicate'}}
            ]}
        )
        for u in coded_uniques:
            # Get the final codes for the tweet.
            first_code = u['first_final']
            second_codes = u['second_final']

            codes = {'codes': [
                            {
                                'second_code': second_codes,
                                'first_code': first_code,
                                'rumor': self.rumor
                            }
                        ]
                     }
            if int(u['db_id']) == 40:
                print 'FOUND! (DB_ID)'

            compression_mapping = self.compression.find(
                {'db_id': int(u['db_id'])},
            )
            # Pull the tweet out of the iterator.
            compression_mapping = list(compression_mapping)[0]
            if "323949024744964097" in compression_mapping['id']:
                print 'FOUND! (STR)'
            # Get the list of tweets which are mapped to this tweet.
            duplicate_ids = map(int ,compression_mapping['id'])

            if 323949024744964097 in duplicate_ids:
                print 'FOUND! (INT)'
            # Propagate the codes.
            query = {'id': {'$in': duplicate_ids}}
            self.rumor_collection.update(
                query,
                {'$set': codes},
                upsert=False,
                multi=True
            )
        # Update the metadata
        self.__update_rumor_status__('final_codes_propagated')

    def upload_adjudication(self, args):
        """
        FUNCTION:
            Uploads adjudicated tweets to the database.
        """
        uploaded_str = self.adj_meta_prefix + '_uploaded'
        if self.status_log[uploaded_str]:
            raise RuntimeError(
                'This level of adjudication has already been uploaded')
        else:
            self.__upload_all__()
            self.__update_rumor_status__(uploaded_str)

    def __prompt_for_code__(self, level):
        """
        (Helper for __handle_missing_code__)
        Prompts the user to choose a code from a
        list of either first or second level codes,
        and returns the chosen code.

        Args:
            level (int): The level of codes (1 or 2)
                         to present to the user.
        """
        if level == 1:
            options = self.first_codes
        elif level == 2:
            options = self.second_codes
        else:
            raise ValueError('Invalid level parameter: '+str(level))

        print 'Please assign a code (!q to abort):'
        for i, code in enumerate(options):
            print code, '\t('+str(i)+')'

        usr_in = -1
        while  0 > usr_in or usr_in > len(options):
            usr_in = raw_input('>>')
            if usr_in == '!q':
                exit()
            else:
                try:
                    usr_in = int(usr_in)
                except:
                    usr_in = -1

        return options[usr_in]

    def __handle_missing_code__(self, text):
        """
        In the case that a tweet is missing a code,
        this method presents the tweet to the user
        and prompts them to assign a code to it.

        Args:
            text (str): The text of the tweet which is
                        missing a code.

        Returns:
            (dict): A codes object of the form:
                        {'first_level': first_code,
                        'second_level': [second_codes]}
        """
        print '\n', text, '\n'
        first_code = self.__prompt_for_code__(1)
        second_codes = []
        usr_in = ''
        while usr_in != 'n':
            if usr_in == 'y':
                second_codes.append(self.__prompt_for_code__(text, 2))

            print 'Add second_level code?(y/n)'
            usr_in = raw_input('>>')

        return {'first_level': first_code, 'second_level': second_codes}

    def generate_recodes(self, args):
        print 'Gathering tweets...'
        # Get the full list of tweets which were marked related.
        tweet_list = self.code_comparison.find(
            {'$and':[{'first_final':{'$ne':code}} for code in self.skip_second_code]})

        print 'Allocating...'
        for tweet in tweet_list:
            # Get the tweet id from the compression database.
            c_tweet = self.compression.find_one({'db_id': int(tweet['db_id'])})
            # Get the full tweet object from the rumor database.
            # ('tweet' is an object from the compression database so it's
            #   missing some text information)
            full_tweet = self.rumor_collection.find_one(
                            {'id': c_tweet['id'][0]})

            # If the tweet exists...
            if full_tweet is not None:
                tweet['text'] = full_tweet['text']
                self.__delegate__(tweet)


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
