import csv
from random import sample


def main(path, out_path, k):
    '''
    Selects a random sample of k lines from a csv.

    Args:
        path (str): filepath to the csv to sample from
        out_path (str): path to write the sample to
        k (int): the number of rows to sample
    '''
    # Get the number of lines
    with open(path, 'rb') as f:
        reader = csv.reader(f)
        num_lines = sum(1 for i in reader)
    # Select k indices from those lines.
    indices = sample(xrange(num_lines), k)

    # Write a new csv with the specified lines.
    with open(path, 'rb') as f:
        with open(out_path, 'wb') as output:
            reader = csv.reader(f)
            writer = csv.writer(output)
            for i, line in enumerate(reader):
                if i in indices:
                    writer.writerow(line)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='Selects a random sample of k lines from a csv')
    parser.add_argument(
        'in_path', help='The path to the csv to draw the saple from.', type=str)
    parser.add_argument(
        'out_path', help='The path to output the sample to.', type=str)
    parser.add_argument(
        'k', help='The desired sample size.', type=int)

    args = parser.parse_args()
    main(args.in_path, args.out_path, args.k)