from TweetProcessor import TweetProcessor
import utils

class OverlapCalculator(TweetProcessor):

    def __init__(self,event_name,rumor):
        TweetProcessor.__init__(self,event_name,rumor)
        self.overlap_db = utils.mongo_connect(db_name='embedings',
                                              collection_name=self.rumor)

    def _create_overlap_db(self):
