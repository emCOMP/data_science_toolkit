import csv,utils,os,kappa

def process(in_name,out_name):
    f_out = utils.write_to_samples(path=out_name)
    with open(in_name, 'rb') as f_in:
        reader = csv.reader(f_in)
        for row in reader:
            counts = {}
            for col in row[6:]:
                if col is not '':
                    codes = col.split(';')
                    for code in codes:
                        code = code.strip()
                        counts[code] = counts.get(code,0) + 1
            for col in row[:6]:
                f_out.write('%s,' % col)
            adjudicate = True
            for code in counts:
                if counts[code] > 1:
                    f_out.write('%s;' % code)
                    if code == 'affirm' or code == 'deny' or code == 'neutral (use sparingly)' or code == 'unrelated':
                        adjudicate = False
            if adjudicate:
                f_out.write(',true')
            else:
                f_out.write(',false')
            f_out.write('\n')

def adjudicate():
    print 'enter a valid input file name (include file extension):'
    fname_in = raw_input('>> ')
    print 'enter a valid output file name (include file extension):'
    fname_out = raw_input('>> ')
    fname_out = os.path.join(os.path.dirname(__file__),os.pardir,'samples/') + fname_out
    process(in_name=fname_in,out_name=fname_out)

def adjudicate_db(db,coders):
    tweets = db.find()
    for tweet in tweets:
        final = []
        if float(tweet.get('Implicit',0))/coders > .5:
            final.append('Implicit')
        if float(tweet.get('Uncertainty',0))/coders > .5:
            final.append('Uncertainty')
        first = ['Affirm','Deny','Neutral (use sparingly)','Uncodable','Unrelated']
        first.sort(key=lambda x: tweet.get(x,0), reverse=True)
        if tweet.get(first[0],0) > .5:
            final.append(first[0])
        else:
            final.append('Adjudicate')
        db.update({'db_id':tweet['db_id']},
                  {'$addToSet':{
                      'final':{
                          '$each':final
                      }
                  }
               }
        )

def read_codes(dir_in,db):
    for filename in os.listdir(dir_in):
        path = dir_in + filename
        with open(path, 'rb') as codesheet:
            reader = csv.reader(codesheet)
            first_row = True
            header = []
            for row in reader:
                if first_row:
                    header = row
                    first_row = False
                else:
                    codes = {}
                    tweet_id = None
                    tweet_text = None
                    for count,col in enumerate(row):
                        if header[count] == 'db_id':
                            tweet_id = col
                        if header[count] == 'text':
                            tweet_text = col.decode('latin-1').encode('utf-8')
                        if col is not '' and header[count] != 'text' and header[count] != 'rumor' and header[count] != 'id' and header[count] != 'db_id':
                            codes[header[count]] = codes.get(header[count],0) + 1
                    if tweet_id:
                        db.update(
                            {'db_id':tweet_id,'text':tweet_text},
                            {'$inc':codes},
                            upsert=True
                        )

def coder_agreement(db,coders,codes=None):
    if not codes:
        codes  = ['Uncodable','Unrelated','Affirm','Deny','Neutral']
    mat = []
    tweets = db.find()
    for tweet in tweets:
        result = []
        num_codes = 0
        for code in codes:
            if code in tweet:
                result.append(tweet[code])
                num_codes += tweet[code]
            else:
                result.append(0)
        result.append(coders-num_codes)
        mat.append(result)
    print mat
    aggreement = kappa.computeKappa(mat)

def agreement_sheet(db,coders):
    print 'enter a valid output file name:'
    fname_out = raw_input('>> ')
    f_out = utils.write_to_samples(path=fname_out)
    codes  = ['id','text','Uncodable','Unrelated','Affirm','Deny','Neutral','Implict','Ambiguity','Uncertainty','Difficult']
    for header in codes:
        f_out.write('"%s",' % header)
    f_out.write('\n')
    tweets = db.find()
    for tweet in tweets:
        print tweet
        result = ''
        agreement = True
        for code in codes:
            if code in tweet:
                if type(tweet[code]) != int:
                    result += ('"%s",' % tweet[code].encode('utf-8'))
                else:
                    result += (str(tweet[code]) + ',')
                    if float(tweet[code])/coders < .7:
                        agreement = False
            else:
                result += (str(0) + ',')
        result += '\n'
        if not agreement:
            f_out.write(result)

def main():
    #adjudicate()
    codes = ['Uncodable','Unrelated','Affirm','Deny','Neutral']
    alt_codes = ['Affirm']
    rumor = 'hadley'
    coders = 2
    code_comparison = utils.mongo_connect(db_name='code_comparison',collection_name=rumor)
    compression = utils.mongo_connect(db_name='sydneysiege_cache',collection_name=rumor)
    read_codes('../codes/',db=code_comparison)
    adjudicate_db(db=code_comparison,coders=3)
    #coder_agreement(db=code_comparison,coders=2,codes=alt_codes)
    #agreement_sheet(db=code_comparison,coders=coders)

if __name__ == "__main__":
    main()
