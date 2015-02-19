"""
Inputs (via command-line):
1. Path to CSV containing tweets you want to code. Defaults to sample.csv
2. Path to CSV containing to a CSV containing coder names and the associated # of tweets they have to code. Defaults to coder_assignments.csv

Example: python sheets.py lakemba_full.csv coder_assignments.csv

Outputs: n unique but overlapping coding sheets for a set of coders using a pseudo-random approach
"""
from collections import Counter
import csv, random, sys
import itertools

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
current_coverage = 0 # We first hit all tweets with 0 coverage, then 1 coverage and so on. This variable controls that

for coder in coders[1:]: # 1 coder at a time
  assigned_tweets = []
  unassigned_tweets = tweets[1:]

  while int(coder[1]) > 0: #While they still have capacity
    coder[1] = int(coder[1]) - 1
    unassigned_tweets_by_level = [i for i in unassigned_tweets if i[5] == current_coverage]
    if len(unassigned_tweets_by_level) == 1: # if we exhaust tweets at the current coverage level we move on
      current_coverage = current_coverage + 1
      tweet = unassigned_tweets[0]
    else:
      tweet = random.choice(unassigned_tweets_by_level[1:])
    assigned_tweets += [tweet[:4]]
    unassigned_tweets.remove(tweet)
    tweet = tweets[tweets.index(tweet)]
    tweet[5] = tweet[5] + 1
    if tweet[5] == COVERAGE: #if the tweet has been covered the requisite number of times take it out
      tweets.remove(tweet)
  write_to_csv(coder[0], assigned_tweets)

if len(tweets) > 1:
  print "WARNING: Coders have been fully assigned but {} tweets are not being covered by {} coders. You might want to check your math!".format(len(tweets)-1, COVERAGE)
