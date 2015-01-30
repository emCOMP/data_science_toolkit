"""
Inputs (via command-line):
1. Path to CSV containing tweets you want to code. Defaults to sample.csv
2. Path to CSV containing to a CSV containing coder names and the associated # of tweets they have to code. Defaults to coder_assignments.csv

Example: python sheets.py lakemba_full.csv coder_assignments.csv

Outputs: n unique but overlapping coding sheets for a set of coders
"""
from collections import Counter
import csv, random, sys

COVERAGE = 3 # number of passes needed on a particular tweet

# Some helper functions
def get_sample_file():
  if len(sys.argv) >= 2:
    return sys.argv[1]
  else:
    return "sample.csv"

def get_coder_file():
  if len(sys.argv) >= 3:
    return sys.argv[2]
  else:
    return "coder_assignments.csv"

def read_from_csv(file_name):
  with open(file_name, 'rb') as f:
    reader = csv.reader(f)
    return map(list, reader)

def write_to_csv(coder_name, tweets):
  with open("{coder_name!s}_coding_sheet.csv".format(**locals()), "wb") as f:
      writer = csv.writer(f)
      writer.writerows(tweets)

# Entry point
tweets = [tweet+[0] for tweet in read_from_csv(get_sample_file())]
coders = read_from_csv(get_coder_file())

for coder in coders[1:]: #
  assigned_tweets = []
  while int(coder[1]) > 0:
    coder[1] = int(coder[1]) - 1
    tweet = random.choice(tweets[1:])
    assigned_tweets += [tweet[:4]]
    tweet[5] = tweet[5] + 1
    if tweet[5] == COVERAGE:
      tweets.remove(tweet)
  write_to_csv(coder[0], assigned_tweets)

if len(tweets) > 1:
  print "WARNING: Coders have been fully assigned but {} tweets are not being covered by {} coders. You might want to check your math!".format(len(tweets)-1, COVERAGE)
