"""
Inputs (via command-line):
1. Path to CSV containing tweets you want to analyze for patterns by tweet users. Defaults to sample.csv

Example: python sheets.py lakemba_full.csv

Outputs (via CSV): 
1. Tweeters who followed particular pre-defined patterns on the sample in tweeter_results.csv
2. The tweets for those tweeters in tweet_results.csv
"""

from collections import Counter
import csv, random, sys
import itertools

# Helper functions
def get_sample_file():
  if len(sys.argv) >= 2:
    return sys.argv[1]
  else:
    return "sample.csv"

def read_from_csv(file_name):
  with open(file_name, 'rb') as f:
    reader = csv.reader(f)
    return map(list, reader)

def write_to_csv(name,data):
  with open("{name!s}_results.csv".format(**locals()), "wb") as f:
      writer = csv.writer(f)
      writer.writerows(data)

def is_affirm(tweet):
  return tweet[8]=="Affirm"

def is_probably_retweet(tweet):
  return tweet[10]!="0"

def was_deleted(tweet):
  return tweet[7]=="DELETED"

def was_probably_deleted_by_user(tweet):
  return ((not is_probably_retweet(tweet)) or (is_probably_retweet(tweet) and original_tweet_not_deleted(tweet)))

def original_tweet_not_deleted(tweet):
  return tweet[11]=="FOUND" or tweet[11]==""

# Entry point
tweets = [tweet for tweet in read_from_csv(get_sample_file())][1:]
tweeters = list(set([tweet[0] for tweet in tweets]))
written_tweeters=[]
written_tweets=[]

for tweeter in tweeters: #we iterate over the list of tweeters
  matches = [x for x in tweets if x[0] == tweeter and (x[8]=="Affirm" or x[8]=="Deny")] #we only pick up affirms and denials for the tweeter
  code = ""
  for match in matches: # for each matched tweet we check its deletion status and primary code
    if is_affirm(match):
      code +="A"
    else:
      code +="D"
    if was_deleted(match):
      if was_probably_deleted_by_user(match):
        code +="(DEL)"
      else:
        code +="(DEL*)"

  group = "" # here we figure out which pattern the user falls under
  if code !="A" and code !="":
    if code.find("A")!=-1 and code.find("AD")==-1 and code.find("A(")==-1: #Affirm+
      group = "Affirm+"
    elif code.find("A")!=-1 and code.find("AD")==-1 and code.find("A(")!=-1: ## Affirm+ Delete+
      group = "Affirm+ Delete+"
    elif code.find("A")!=-1 and code.find("AD")!=-1 and code.find("A(")==-1: ## Affirm+ Deny+
      group = "Affirm+ Deny+"
    elif code.find("A")!=-1 and code.find("D")!=-1 and code.find("A(")!=-1: ## Affirm+ Deny+ Delete+
      group = "Affirm+ Deny+ Delete+"
    elif code.find("D")!=-1 and code.find("A")==-1: ## Deny+
      group = "Deny+"
    else:
      group = "Error"
      print "Super special tweeting person detected!"

    written_tweeters += [[code] + [group] + matches[0][0:5]] # append results to the output set
    for match in matches:
      written_tweets += [[match[0]] + 
                          match[5:7] + 
                          [match[8]] + 
                          [was_deleted(match)] + 
                          [is_probably_retweet(match)] + 
                          [not original_tweet_not_deleted(match)] + 
                          [was_deleted(match) and was_probably_deleted_by_user(match)]]

write_to_csv("tweeter", ([["Code"] + 
                          ["Group"] + 
                          ["Screen Name"] + 
                          ["Name"] + 
                          ["Followers Count"] + 
                          ["Friends Count"] + 
                          ["Location"]] + 
                        written_tweeters))

write_to_csv("tweets", ([["Screen Name"] + 
                          ["Created"] + 
                          ["Text"] + 
                          ["Code"] + 
                          ["Deleted?"] + 
                          ["Retweet?"] + 
                          ["Original Tweet Deleted?"] + 
                          ["Likely Deleted by User?"]] +
                        written_tweets))
