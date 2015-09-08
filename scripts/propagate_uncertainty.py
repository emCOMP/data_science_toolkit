from pymongo import MongoClient
import argparse


def main(db, rumor):
    code_comparison = MongoClient('z')['code_comparison'][rumor]
    compression = MongoClient('z')['rumor_compression'][rumor]
    rumor_collection = MongoClient('z')[db][rumor]

    # Find all of the non adjudicated codes.
    coded_uniques = code_comparison.find(
        {'uncertainty_codes': {'$exists': 1}}
    )
    for u in coded_uniques:
        # Get the final codes for the tweet.
        codes = u['uncertainty_codes']

        compression_mapping = compression.find(
            {'db_id': int(u['db_id'])},
        )
        # Pull the tweet out of the iterator.
        compression_mapping = list(compression_mapping)[0]
        # Get the list of tweets which are mapped to this tweet.
        duplicate_ids = map(int, compression_mapping['id'])
        # Propagate the codes.
        query = {'id': {'$in': duplicate_ids}}
        rumor_collection.update(
            query,
            {'$set': codes},
            upsert=False,
            multi=True
        )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Manages tweet flow between the database,\
                    spreadsheets, and the coding tool.')
    parser.add_argument(
        'db_name', help='The name of the database to use.', type=str)
    parser.add_argument(
        'rumor_name', help='The name of the rumor to use.', type=str)
    args = parser.parse_args()
    main(args.db_name, args.rumor_name)
