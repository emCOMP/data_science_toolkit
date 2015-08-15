import argparse
from dstk.database import utils
from agreement.kappa import kappa

class Page(object):
    def __init__(self, layout):
        self.layout = layout
        self.figures = {}
        # {figure_title: {data_type:'', data_value:''}}

    def __getitem__(self, key):
        return self.figures[key]

    def __setitem__(self, key, value):
        self.figures[key] = value


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

        tweets = self.code_comparison.find({},{'codes':1})
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
        id_to_name = {e['coder_id']:e['name'] for e in entries}

        return id_to_name

    def add_to_report(self, title, item):
        pass

def main(args):
    rg = ReportGenerator(args)
    report_items = args.report_items
    for i in report_items:
        calculation = rg.__getattribute__(i)
        result = calculation()
        rg.add_to_report("Fleiss' Kappa", result)

    #Visualize/export the report.

    exit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generates reports about data.')

    # General Args.
    general = parser.add_argument_group('General')
    general.add_argument(
        'db_name', help='The name of the database to use.', type=str)
    general.add_argument(
        'rumor_name', help='The name of the rumor to use.', type=str)
    general.add_argument(
        '-ri', '--report_items', help='What type of report to generate.',
        choices=[
            'agreement'
        ], nargs='*', type=str)
    general.add_argument(
        '-p', '--export_path', help='File path to use for export.',
        type=str, required=False, default='../IO/REPORTS/sample.csv')
    general.add_argument(
        '-flc', '--first_level_codes', help='Mutually exclusive codes.',
        type=str, required=False,
        nargs='*', default=[
            'Uncodable',
            'Unrelated',
            'Affirm',
            'Deny',
            'Neutral']
    )
    general.add_argument(
        '-slc', '--second_level_codes',
        help='Secondary codes (non-mutually exclusive)',
        type=str, required=False,
        nargs='*', default=['Uncertainty', 'Ambiguity', 'Implicit'])

    args = parser.parse_args()
    main(args)