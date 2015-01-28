import datetime
import utils
from collections import Counter

def total_tweets_over_time(db,fname):

    title = "%s.csv" % (fname)
    f = utils.write_to_data(path=title)
    f.write('time,total tweets\n')

    #start = datetime.datetime(2014,10,17)
    #end = datetime.datetime(2014,11,13)
    start = db.find().limit(1).sort('created_ts',1).next()['created_ts'].replace(second=0)
        #end = datetime.datetime(2014,10,4)
    end = db.find().limit(1).sort('created_ts',-1).next()['created_ts'].replace(second=0) + datetime.timedelta(minutes=1)
    diff = (end - start).days * 1440
    for date_start in (start + datetime.timedelta(minutes=n) for n in range(diff)):
        date_end = date_start + datetime.timedelta(seconds=59)
        #print "time: %s,%s" % (date_start,date_end)

        raw_data = db.find({
            "created_ts":{
                "$gte":date_start,
                "$lte":date_end
            },
        }).count()

        result = '"%s",%d\n' % (date_start,raw_data)
        f.write(result)

def feature_over_time(db,fname,feature,name,gran):

    title = "%s.csv" % (fname)
    f = utils.write_to_data(path=title)
    f.write('time,total tweets\n')
    if gran == 'hour':
        #start = datetime.datetime(2014,9,30)
        start = db.find().limit(1).sort('created_ts',1).next()['created_ts'].replace(minute=0,second=0)
        #end = datetime.datetime(2014,10,4)
        end = db.find().limit(1).sort('created_ts',-1).next()['created_ts'].replace(minute=0,second=0) + datetime.timedelta(hours=1)
        diff = (end - start).days * 24 #1440 for hour
        for date_start in (start + datetime.timedelta(hours=n) for n in range(diff)):
            date_end = date_start + datetime.timedelta(minutes=59)
            #print "time: %s,%s" % (date_start,date_end)

            if feature == 'hashtag':
                raw_data = db.find({
                    "created_ts":{
                        "$gte":date_start,
                        "$lte":date_end
                    },
                    'hashtags':name
                }).count()

            result = '"%s",%d\n' % (date_start,raw_data)
            f.write(result)

    elif gran == 'minute':
        start = db.find().limit(1).sort('created_ts',1).next()['created_ts'].replace(second=0)
        #end = datetime.datetime(2014,10,4)
        end = db.find().limit(1).sort('created_ts',-1).next()['created_ts'].replace(second=0) + datetime.timedelta(minutes=1)
        diff = (end - start).days * 1440
        for date_start in (start + datetime.timedelta(minutes=n) for n in range(diff)):
            date_end = date_start + datetime.timedelta(seconds=59)
            #print "time: %s,%s" % (date_start,date_end)

            if feature == 'hashtag':
                raw_data = db.find({
                    "created_ts":{
                        "$gte":date_start,
                        "$lte":date_end
                    },
                    'hashtags':name
                }).count()

            result = '"%s",%d\n' % (date_start,raw_data)
            f.write(result)

def multi_feature_over_time(db,feature,names):
    for name in names:
        fname = 'hashtag_%s_over_time' % name
        feature_over_time(db=db,fname=fname,feature='hashtag',name=name,gran='hour')

def codes_over_time(db_name,codes,rumor,gran='hour'):
    db = utils.mongo_connect(db_name=db_name,collection_name=rumor)
    for code in codes:
        fname = '%s_%s_over_time' % (rumor,code)
        _codes_over_time(db=db,fname=fname,code=code,gran=gran)

def _codes_over_time(db,fname,code,gran):
    title = "%s.csv" % (fname)
    f = utils.write_to_data(path=title)
    f.write('time,total tweets\n')
    if gran == 'hour':
        start = db.find().limit(1).sort('created_ts',1).next()['created_ts'].replace(minute=0,second=0)
        end = db.find().limit(1).sort('created_ts',-1).next()['created_ts'].replace(minute=0,second=0) + datetime.timedelta(hours=1)
        diff = (end - start).days * 24 #1440 for hour
        for date_start in (start + datetime.timedelta(hours=n) for n in range(diff)):
            date_end = date_start + datetime.timedelta(minutes=59)
            raw_data = db.find({
                "created_ts":{
                    "$gte":date_start,
                    "$lte":date_end
                },
                'codes.code':code
            }).count()

            result = '"%s",%d\n' % (date_start,raw_data)
            f.write(result)

    elif gran == 'minute':
        start = db.find().limit(1).sort('created_ts',1).next()['created_ts'].replace(second=0)
        end = db.find().limit(1).sort('created_ts',-1).next()['created_ts'].replace(second=0) + datetime.timedelta(minutes=1)
        diff = (end - start).days * 1440
        for date_start in (start + datetime.timedelta(minutes=n) for n in range(diff)):
            date_end = date_start + datetime.timedelta(seconds=59)
            raw_data = db.find({
                "created_ts":{
                    "$gte":date_start,
                    "$lte":date_end
                },
                'codes.code':code
            }).count()

            result = '"%s",%d\n' % (date_start,raw_data)
            f.write(result)

def top_hashtags(db,top,fname=None,write=False):
    if write:
        title = "%s.csv" % (fname)
        f = utils.write_to_data(path=title)
        f.write('tag,count\n')

    data = db.find({
        'counts.hashtags':{
            '$gt':0
        }
    })
    print 'finished query'
    count = Counter()

    for x in data:
        count.update(x['hashtags'])
    print 'finished counting'
    if write:
        for x in count.most_common(top):
            result = '"%s",%s\n' % (x[0],x[1])
            f.write(result.encode('utf-8'))

    return count.most_common(top)

def top_urls(db,top,fname=None,write=False):
    if write:
        title = "%s.csv" % (fname)
        f = utils.write_to_data(path=title)
        f.write('expanded_url,count\n')

    data = db.find({
        'counts.urls':{
            '$gt':0
        }
    })
    print 'finished query'
    count = Counter()

    for x in data:
        for y in x['entities']['urls']:
            count.update([y['expanded_url']])

    print 'finished counting'
    if write:
        for x in count.most_common(top):
            result = '"%s",%s\n' % (x[0],x[1])
            f.write(result.encode('utf-8'))

    return count.most_common(top)

def top_mentions(db,top,fname=None,write=False):
    if write:
        title = "%s.csv" % (fname)
        f = utils.write_to_data(path=title)
        f.write('name,count\n')

    data = db.find({
        'counts.user_mentions':{
            '$gt':0
        }
    })
    print 'finished query'
    count = Counter()

    for x in data:
        for y in x['entities']['user_mentions']:
            count.update([y['name']])

    print 'finished counting'
    if write:
        for x in count.most_common(top):
            result = '"%s",%s\n' % (x[0],x[1])
            f.write(result.encode('utf-8'))

    return count.most_common(top)

def cooccuring_hashtags(db,num_top_nodes,num_co_nodes,fname=None,write=False):
    if write:
        title = "%s.csv" % (fname)
        f = utils.write_to_data(path=title)
        f.write('node1,node2,edge\n')

    nodes = top_hashtags(db=db,top=num_top_nodes)
    network = {}
    for x in nodes:
        network[x[0]] = []
        data = db.find({'hashtags':x[0]})
        print 'finished query'
        count = Counter()

        for y in data:
            count.update(y['hashtags'])
            print 'finished counting'
        for y in count.most_common(num_co_nodes):
            if y[0] not in network:
                network[x[0]].append(y[0])
                network[x[0]].append(y[1])
                if write:
                    result = '"%s","%s",%s\n' % (x[0],y[0],y[1])
                    f.write(result.encode('utf-8'))
    return network

def main():
    db = utils.mongo_connect(db_name='sydneysiege')
    db_name = 'sydneysiege'
    codes = ['Affirm','Deny','Neutral']
    total_tweets_over_time(db=db,fname='total_tweets_over_time_sydneysiege')
    #top_hashtags(db=db,top=100,fname='top_hashtags_ebola',write=True)
    #top_mentions(db=db,top=1000,fname='sydneysiege_top_mentions',write=True)
    #cooccuring_hashtags(db=db,num_top_nodes=100,num_co_nodes=100,fname='cooccuring_sydneysiege_1000',write=True)
    #feature_over_time(db=db,fname='tcot2_over_time',feature='hashtag',name='tcot',gran='hour')
    codes_over_time(db_name=db_name,codes=codes,rumor='hadley',gran='minute')
    '''multi_feature_over_time(db=db,feature='hashtag',names=['illridewithyou',
                                                           'martinplace',
                                                           'prayforsydney',
                                                           '9news',
                                                           'breaking',
                                                           'sydneyhostagecrisis',
                                                           'auspol',
                                                           'isis',
                                                           'news',
                                                           'tcot'])
    '''

if __name__ == "__main__":
    main()
