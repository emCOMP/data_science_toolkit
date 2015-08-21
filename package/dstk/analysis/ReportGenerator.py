from html import HTML
from dstk.database import utils


class ReportGenerator(object):

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

        # first level codes (pick 1, mutually exclusive)
        self.first_codes = args.first_level_codes
        # second level codes (choose any)
        self.second_codes = args.second_level_codes

        # Setup the HTML page.
        self.page = None  # Root HTML tag
        self.head = None  # Head Tag
        self.report = None  # Body Tag
        self.__page_setup__()

    def __page_setup__(self):
        self.page = HTML('html')
        self.head = self.page.head()
        self.head.title(self.rumor_name + ' Report')
        self.head.link(rel='stylesheet',
                       type='text/css',
                       href='styles/report.css')
        self.report = self.page.body()

    def agreement(self, metric='kappa'):
        # db containing codes for a given rumor
        self.code_comparison = utils.mongo_connect(db_name='code_comparison',
                                                   collection_name=self.rumor)
        if metric == 'kappa':
            result = self.__kappa__()
            print result

    # Right now only supports first-level codes.
    def __kappa__(self):
        matrix = []

        tweets = self.code_comparison.find({}, {'codes': 1})
        for tweet in tweets:
            row = [0] * len(self.first_codes)
            # The codes assigned to this tweet.
            tweet_codes = tweet['codes']

            for i, poss_code in enumerate(self.first_codes):
                for code_set in tweet_codes:
                    row[i] += code_set.get(poss_code, 0)

            matrix.append(row)

        k = kappa(matrix)
        return k

    # Returns a dictionary mapping coder_ids to coder names:
    #    {coder_id: coder_name}
    def __get_coder_names__(self):
        coders = utils.mongo_connect(db_name='coders',
                                     collection_name='coders')
        entries = coders.find({})
        id_to_name = {e['coder_id']: e['name'] for e in entries}

        return id_to_name

    def add_to_report(self, title, item):
        '''
        Adds an item to the report's html page.

        Args:
            title (str): the name of the item being added
            item (str): the item to add (as string containing
                        appropriate HTML tags).
        '''
        header = h2(title)
        self.report.div(class_='reportItem', header + item)
