import re
from nltk.corpus import stopwords
from nltk.stem.snowball import EnglishStemmer


class TweetCleaner(object):

    def __init__(self, user_settings={}, all_ops=None):

        # The default settings for the Cleaner.
        #   Ops which are 'True' will be applied to each tweet.
        #   Ops which are 'False' willl not.
        self.settings = {
            'scrub_non_ascii': True,
            'scrub_url': True,
            'lowercase': True,
            'scrub_newlines': True,
            'scrub_hashtags': False,
            'scrub_retweet_text': True,
            'scrub_quotes': True,
            'scrub_punctuation': False,
            'scrub_mentions': False,
            'remove_stopwords': False,
            'stem_words': False,
        }

        # The order of this list is the order that
        # ops will be applied to tweets.
        self.op_prioirty = [
            'scrub_non_ascii',
            'scrub_url',
            'lowercase',
            'scrub_newlines',
            'scrub_hashtags',
            'scrub_retweet_text',
            'scrub_quotes',
            'scrub_punctuation',
            'scrub_mentions',
            'remove_stopwords',
            'stem_words'
        ]

        # User-specified settings.
        if all_ops:
            self.settings = {k: True for k in self.settings.keys()}
        else:
            self.settings.update(user_settings)

        # Find the ops we will use.
        enabled_ops = [k for k, v in self.settings.iteritems() if v]

        # Get the enabled ops in order of priority.
        ordered_ops = [op for op in self.op_prioirty if op in enabled_ops]

        # Map the op names to the actual op functions.
        self.ops = [self.__getattribute__(op_name)
                    for op_name in ordered_ops]

        # Run any op specific setup.
        self.__op_setup__()

    def clean(self, text):
        # Handle null input.
        if text is None:
            return None

        else:
            result = text
            for op in self.ops:
                result = op(result)

            return result

    # Put any op-specific setup operations here.
    #   Wrap them in an if statement like so:
    #
    #       if self.ops[<op_name>]:
    #           <op-specific setup here>

    def __op_setup__(self):

        if self.settings['stem_words']:
            self.stemmer = EnglishStemmer(True)

        if self.settings['remove_stopwords']:
            self.stops = frozenset(stopwords.words("english"))

##########################################
#           Define Ops Here              #
##########################################

    def scrub_newlines(self, text):
        return text.replace('\n','')

    def lowercase(self, text):
        return text.lower()

    # Scrubs any unicode characters which can't be converted to ASCII.
    def scrub_non_ascii(self, text):
        return re.sub(r'[^\x00-\x7F]+', u'', text)

    def scrub_url(self, text):
        result = re.sub(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            u'', text)
        return result

    def scrub_retweet_text(self, text):
        s = ur'\u201c' + '@.*?:'
        result = text
        result = re.sub('RT .*?:', '', result).strip()
        result = re.sub('"@.*?:', '', result).strip()
        result = re.sub(s, '', result).strip()
        result = re.sub('via @.*?:', '', result).strip()
        result = re.sub('via @.*?\b', '', result).strip()
        result = re.sub('@.*?\b', '', result).strip()
        return result

    def scrub_quotes(self, text):
        return text.replace('"', '')

    def scrub_punctuation(self, text):
        return re.sub(r'[\.,-\/!$%\^&\*;:{}=\-_`~()]', '', text)

    def scrub_mentions(self, text):
        return re.sub(r'@\w+', u'', text)

    def scrub_hashtags(self, text):
        return re.sub(r'#\w+', '', text)

    def stem_words(self, text):
        # Cast to lower case if we have not already.
        if not self.settings['lowercase']:
            text = self.lowercase(text)

        # Scrub punctuation if we have not already.
        if not self.settings['scrub_punctuation']:
            text = self.scrub_punctuation(text)

        tmp = text.split()
        stemmed = [self.stemmer.stem(w) for w in tmp]
        text = ' '.join(stemmed)
        return text

    def remove_stopwords(self, text):
        # Cast to lower case if we have not already.
        if not self.settings['lowercase']:
            text = self.lowercase(text)

        # Scrub punctuation if we have not already.
        if not self.settings['scrub_punctuation']:
            text = self.scrub_punctuation(text)

        tmp = text.split()
        non_stopwords = [w for w in tmp if w not in self.stops]
        text = ' '.join(non_stopwords)
        return text
