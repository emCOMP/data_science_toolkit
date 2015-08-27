import re
from nltk.corpus import stopwords
from nltk.stem.snowball import EnglishStemmer
import string


class TweetCleaner(object):
    """
    Processes tweet text using a set of specified operations.

    NOTE:   All ops is applied before user_settings, so
            it is possible to combine the two.

    Ex:     Passing (all_ops=False, user_settings={'lowercase': True})
            will apply only the lowercase op.

    Args:
        all_ops (bool): If this is passed, the default settings will
                be overridden with the value passed.
                Ex. If True is passed all ops will be set to True.

        user_settings ({str: bool}): Keys are cleaning operations,
                                    values are bools:
                                    Ops which are 'True' will be applied
                                    to each tweet.
                                    Ops which are 'False' willl not.
    """

    def __init__(self, all_ops=None, user_settings={}):

        # The default settings for the Cleaner.
        self.settings = {
            'scrub_non_ascii': True,
            'scrub_url': True,
            'lowercase': True,
            'scrub_newlines': True,
            'scrub_hashtags': False,
            'scrub_retweet_text': True,
            'scrub_quotes': True,
            'scrub_mentions': False,
            'scrub_punctuation': False,
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
            'scrub_mentions',
            'scrub_punctuation',
            'remove_stopwords',
            'stem_words'
        ]

        # User-specified settings.
        if all_ops == True:
            self.settings = {k: True for k in self.settings.keys()}
        elif all_ops == False:
            self.settings = {k: False for k in self.settings.keys()}

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
        """
        Applies all of the instance's enabled ops to the
        string passed in as 'text'.

        Args:
            text (str): The tweet text to be cleaned.

        Returns:
                (str): The resulting string after all enabled ops
                        are applied to 'text'.
        """
        if text is None:
            return None

        else:
            result = text
            for op in self.ops:
                result = op(result)

            return result

    def __op_setup__(self):
        """
        Provides any op-specific setup required for ops.
        (Eg. importing new libraries, constructing other objects, etc.)

        Put any op-specific setup operations here.
            Wrap them in an if statement like so:

                if self.settings[<op_name>]:
                    <op-specific setup here>
        """
        if self.settings['stem_words']:
            self.stemmer = EnglishStemmer(True)

        if self.settings['remove_stopwords']:
            self.stops = frozenset(stopwords.words("english"))

##########################################
#           Define Ops Here              #
##########################################

    # Removes newline characters.
    def scrub_newlines(self, text):
        return text.replace('\n', '')

    # Casts all characters to lowercase.
    def lowercase(self, text):
        return text.lower()

    # Scrubs any unicode characters which can't be converted to ASCII.
    def scrub_non_ascii(self, text):
        return re.sub(r'[^\x00-\x7F]+', u'', text)

    # Removes URLs
    def scrub_url(self, text):
        result = re.sub(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            u'', text)
        return result

    # Removes all types of 'retweet text'.
    def scrub_retweet_text(self, text):
        s = ur'\u201c' + '@.*?:'
        result = text
        result = re.sub(r'RT .*?:', '', result).strip()
        result = re.sub(r'"@.*?:', '', result).strip()
        result = re.sub(s, '', result).strip()
        result = re.sub(r'via @.*?:', '', result).strip()
        result = re.sub(r'via @.*?\b', '', result).strip()
        result = re.sub(r'@.*?\b', '', result).strip()
        return result

    # Removes quotation marks.
    def scrub_quotes(self, text):
        return text.replace('"', '')

    # Removes puncutation.
    def scrub_punctuation(self, text):
        return text.translate(
            string.maketrans("",""), string.punctuation)

    # Removes user-mentions.
    # NOTE: This removes the entire mention, not just the @.
    def scrub_mentions(self, text):
        return re.sub(r'@\w+', u'', text)

    # Removes hashtags.
    def scrub_hashtags(self, text):
        return re.sub(r'#\w+', '', text)

    # Stems all words in the tweet.
    # NOTE: Applies lowercase and scrub_punctuation
    #       if they are not already applied.
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

    # Removes stopwords (are, this, the, is, etc.)
    # NOTE: Applies lowercase and scrub_punctuation
    #       if they are not already applied.
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
