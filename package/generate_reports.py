import argparse
from dstk.analysis import ReportGenerator

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