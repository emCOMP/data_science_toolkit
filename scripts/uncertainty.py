from TweetProcessor import TweetProcessor
from collections import Counter
from nltk.corpus import stopwords
from nltk.stem.porter import *
from sklearn.feature_extraction.text import TfidfVectorizer
import nltk
import string
import os
import re
import config
import random

class UncertaintyAnalysis(TweetProcessor):

    def __init__(self,event_name,rumor):
        TweetProcessor.__init__(self,event_name=event_name,
                                rumor=rumor)

    def _remove_stopwords(self,words):
        stop_words = stopwords.words('english') + config.filter_words[self.rumor] + config.event_terms[self.event]
        filtered_words = [re.sub("'","",w.lower()) for w in words if not re.sub("'","",w.lower()) in stop_words]
        return filtered_words

    def _stem_words(self,words):
        stemmed = []
        for item in words:
            stemmed.append(PorterStemmer().stem(item))
        return stemmed

    def process_tweet(self,tweet,stem=True,return_list=True):
        text = self._scrub_tweet(text=tweet['text'])
        words = re.findall(r"[\w']+", text)
        words = self._remove_stopwords(words)
        if stem:
            words = self._stem_words(words)
        if return_list:
            return words
        else:
            cleaned = ''
            for word in words:
                cleaned += word + ' '
            return cleaned

    def top_uncertainty_words(self,output=True,sample_size=0):
        temp_uncertainty_tweet_list = self.code_comparison.find({'second_final':'Uncertainty'})
        if sample_size > 0:
            sampled_tweets = [x for x in temp_uncertainty_tweet_list]
            try:
                uncertainty_tweet_list = random.sample(sampled_tweets,sample_size)
                uncertainty_total = len(uncertainty_tweet_list)
            except ValueError:
                uncertainty_total = len(sampled_tweets)
                uncertainty_tweet_list = sampled_tweets
        else:
            uncertainty_tweet_list = temp_uncertainty_tweet_list
            uncertainty_total = uncertainty_tweet_list.count()
        baseline_tweet_list = self.code_comparison.find({'$and':[{'first_final':{'$ne':'Unrelated'}},{'first_final':{'$ne':'Uncodable'}}]})

        baseline_total = baseline_tweet_list.count()
        top_words = Counter()
        baseline_top_words = Counter()
        print '[INFO] creating baseline counts'
        for tweet in baseline_tweet_list:
            try:
                filtered_words = self.process_tweet(tweet=tweet,stem=False)
                baseline_top_words.update(filtered_words)
            except TypeError:
                #print tweet['text']
                pass

        print '[INFO] creating uncertainty counts'
        for tweet in uncertainty_tweet_list:
            try:
                filtered_words = self.process_tweet(tweet=tweet,stem=False)
                top_words.update(filtered_words)
            except TypeError:
                print tweet['text']
        results = {}
        print '[INFO] normalizing counts'
        for count in top_words:
            normalized = float(top_words[count])/float(uncertainty_total)
            normalized_base = float(baseline_top_words[count])/float(baseline_total)
            results[count] = normalized - normalized_base
        if output:
            print '[INFO] sorting'
            ordered_result = [x for x in results]
            ordered_result.sort(key=lambda x: results[x],reverse=True)
            for x in ordered_result[:25]:
                print x,results[x]
        return results

    def uncertainty_tf_idf(self):
        word_counts = Counter()
        tf_idf_counts = Counter()
        tweet_list = self.rumor_collection.find()
        token_dict = {}
        for tweet in tweet_list:
            filtered_words = self.process_tweet(tweet=tweet)
            token_dict[tweet['id']] = filtered_words
        tfidf = TfidfVectorizer()
        tfs = tfidf.fit_transform(token_dict.values())
        print tfs
        ut = [self.process_tweet(tweet=tweet) for tweet in self.rumor_collection.find({'codes.second_code':'Uncertainty'})]
        response = tfidf.transform(ut)
        feature_names = tfidf.get_feature_names()
        for col in response.nonzero()[1]:
            #print feature_names[col],response[0, col]
            tf_idf_counts.update({feature_names[col]:response[0, col]})
            word_counts.update([feature_names[col]])
        results = {}
        #for word in word_counts:
        #    print word,tf_idf_counts[word],word_counts[word]
        #print results

def compare_rumors(event_dict):
    result_counter = Counter()
    for event in event_dict:
        print 'EVENT: %s' % event
        for rumor in event_dict[event]:
            print 'RUMOR: %s' % rumor
            u = UncertaintyAnalysis(event_name=event,rumor=rumor)
            result_counter.update(u.top_uncertainty_words(output=False,
                                                          sample_size=500))
    for x in result_counter.most_common(25):
        print x[0],x[1]

def top_uncertainty(event_dict):
    for event in event_dict:
        print 'EVENT: %s' % event
        for rumor in event_dict[event]:
            print 'RUMOR: %s' % rumor
            u = UncertaintyAnalysis(event_name=event,rumor=rumor)
            u.top_uncertainty_words()

def main():
    # the event identifier
    event_dict = {
        'sydneysiege':['hadley','flag','lakemba','flag','suicide','airspace'],
        'mh17':['americans_onboard'],
        'WestJet_Hijacking':['hijacking'],
        #'baltimore':['church_fire','purse']
    }
    # the rumor identifier
    #u = UncertaintyAnalysis(event_name='sydneysiege',
    #                        rumor=event_dict['sydneysiege'][0])

    #u.top_uncertainty_words()
    #u.uncertainty_tf_idf()

    compare_rumors(event_dict=event_dict)
    #top_uncertainty(event_dict=event_dict)

if __name__ == "__main__":
    main()
