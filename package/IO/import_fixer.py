from pymongo import MongoClient
import pandas as pd
import os

"""
A fixer script which retrives the db_id for each tweet in a folder of csvs
using the Tweet ID and adds the db_id to a new column in each csv.
(Use this if you have completed sheets with tweet_ids but no db_ids)

!!!Be sure to change the rumor and csv_dir to the appropriate ones!!!
"""
rumor = ''
csv_dir = ''
db = MongoClient('z')['rumor_compression'][rumor]

for f in os.listdir(csv_dir):
    if f.endswith('.csv'):
        path = csv_dir + f

        df = pd.DataFrame.from_csv(path, index_col=False)
        df['id'] = df['db_id'].astype(str)
        del df['db_id']
        ids = list(df['id'])
        compression_result = list(db.find({'id':{'$in':ids}},{'id':1, 'db_id':1}))
        id_to_db_id = pd.DataFrame({'db_id':[t['db_id'] for t in compression_result], 'id':[t['id'][0] for t in compression_result]})
        df = df.merge(id_to_db_id, on='id', how='left')
        df.to_csv(f, index=False)