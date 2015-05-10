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

class UncertaintyAnalysis(TweetProcessor):

    def __init__(self,event_name,rumor):
        TweetProcessor.__init__(self,event_name=event_name,
                                rumor=rumor)

    def _remove_stopwords(self,words):
        stop_words = stopwords.words('english') + config.filter_words[self.rumor] + config.event_terms[self.event]
        filtered_words = [w.lower() for w in words if not w.lower() in stop_words]
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

    def top_uncertainty_words(self,output=True):
        uncertainty_tweet_list = self.rumor_collection.find({'codes.second_code':'Uncertainty'})
        baseline_tweet_list = self.rumor_collection.find({'$and':[{'codes.first_code':{'$ne':'Unrelated'}},{'codes.first_code':{'$ne':'Uncodable'}}]})
        uncertainty_total = uncertainty_tweet_list.count()
        baseline_total = baseline_tweet_list.count()
        top_words = Counter()
        baseline_top_words = Counter()
        print '[INFO] creating baseline counts'
        for tweet in baseline_tweet_list:
            filtered_words = self.process_tweet(tweet=tweet,stem=False)
            baseline_top_words.update(filtered_words)
        print '[INFO] creating uncertainty counts'
        for tweet in uncertainty_tweet_list:
            filtered_words = self.process_tweet(tweet=tweet,stem=False)
            top_words.update(filtered_words)
        results = {}
        print '[INFO] normalizing counts'
        for count in top_words:
            normalized = float(top_words[count])/float(uncertainty_total)
            normalized_base = float(baseline_top_words[count])/float(baseline_total)
            results[count] = normalized - normalized_base
        if output:
            print '[INFO] sorting'
            ordered_result = [x for x in results]
            ordered_result.sort(key=lambda x: results[x])
            for x in ordered_result:
                x,results[x]
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
    results_dict = {}
    for event in event_dict:
        for rumor in event_dict[event]:
            u = UncertaintyAnalysis(event_name=event,rumor=rumor)

def main():
    # the event identifier
    event = 'sydneysiege'
    # the rumor identifier
    rumor = 'hadley'

    u = UncertaintyAnalysis(event_name=event,rumor=rumor)

    u.top_uncertainty_words()
    #u.uncertainty_tf_idf()

if __name__ == "__main__":
    main()
