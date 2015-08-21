import argparse
from dstk.management.TweetManager import TweetManager

"""
Usage:
    python manage_tweets.py EVENT RUMOR ACTION --options ...

Example:
    python manage_tweets.py sydneysiege hadley generate_training -ss 80

    This will generate a training sheet for the Hadley
    rumor containing 80 tweets.


AVALIABLE ACTIONS:
    (See individual function documentation for more
     details on each action).

    compress:
        Locates all unique tweets by mapping duplicate
        tweets and retweets to an original tweet, and
        storing these mappings in a rumor_compression
        database.

    generate_training:
        Generates a sample of tweets from the specified rumor
        for training.

    generate_coding:
        Generates coding sheets for the specified rumor, assigning
        tweets based on the loads specified in a coder_assignments
        csv file.

    generate_adjudication:
        Generates adjudication sheets for the specified level of codes
        (first-level codes only, both, or second-level codes only).

    upload_adjudication:
        Uploads adjudication sheets to the database.

    propagate_codes:
        Propagates codes from the code_comparison database to the
        event database. (Applies codes from each unique tweet to
        all duplicates of that tweet).
"""

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
            'upload_coding',
            'generate_adjudication',
            'upload_adjudication',
            'propagate_codes'
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
        default='dstk/management/resources/coding_tool_ids.json')

    # Args for generate_training().
    training = parser.add_argument_group('Generate Training')
    training.add_argument(
        '-p', '--export_path', help='File path to use for export.',
        type=str, required=False, default='IO/EXPORT/sample.csv')
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
        type=str, required=False, default='IO/EXPORT')
    gen_coding.add_argument(
        '-ca', '--coder_assignments',
        help='A path to a csv containing coder names and the number\
                of tweets each will code.',
        type=str, required=False, default='IO/coder_assignments.csv')

    # Args for generate_adjudication().
    adjudicate = parser.add_argument_group('Adjudicate')
    adjudicate.add_argument(
        '-al', '--adjudication_level',
        help='Which of the three adjudication cases to \
                generate sheets for (first level only, \
                both, or second level only)',
        type=str, required=False, choices=[
            'first',
            'both',
            'second',
            ]
    )
    adjudicate.add_argument(
        '-ud', '--upload_dir', help='Path to input folder for \
                                    completed coding/adjudication sheets.',
        type=str, required=False, default='IO/IMPORT')
    adjudicate.add_argument(
        '-aa', '--adjudicator_assignments',
        help='A path to a csv containing adjudicator \
            names and the number of tweets each will adjudicate.',
        type=str, required=False,
        default='IO/adjudicator_assignments.csv')
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
