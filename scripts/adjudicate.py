import csv,utils,os,kappa


# processor class for importing and adjudicating tweets
class Processor(object):

    def __init__(self,rumor,num_coders):

        # db for raw and finals codes
        self.code_comparison = utils.mongo_connect(db_name='code_comparison',
                                                   collection_name=rumor)
        # db for mapping unique tweets to non-uniques
        self.compression = utils.mongo_connect(db_name='sydneysiege_cache',
                                               collection_name=rumor)
        # db mapping coder names to coder ids
        self.coders = utils.mongo_connect(db_name='coders',
                                          collection_name='coders')
        # first level codes (pick 1, mutually exclusive)
        self.first_codes = ['Uncodable','Unrelated','Affirm','Deny','Neutral']
        # second level codes (choose any)
        self.second_codes = ['Uncertainty','Ambiguity','Implicit']
        # number of coders per tweet
        self.num_coders = num_coders
        # directory path for raw coding sheets
        self.code_dir = os.path.join(os.path.dirname(__file__),os.pardir,'codes/')

    # helper method for mapping coder names to coder ids
    # if no name exists, create a new coder
    def _check_coder(self,coder_name=None,coder_id=None):
        if not coder_name and not coder_id:
            raise TypeError
        elif coder_name:
            coder = self.coders.find_one({'name':coder_name})
            if coder:
                return coder
        elif coder_id:
            coder = self.coders.find_one({'coder_id':coder_id})
            if coder:
                return coder
        try:
            coder_id = self.coders.find().sort('coder_id',-1).limit(1).next()['coder_id'] + 1
        except StopIteration:
            coder_id = 0
        coder = {'name':coder_name,
                 'coder_id':coder_id}
        self.coders.insert(coder)
        return coder

    # import codes from the coding directory into the code_comparison db
    def read_codes(self):
        test = self.code_comparison.find_one()
        user_in = 'y'
        if test:
            print 'codes db already exists!'
            print 'DO NOT upload duplicates'
            print 'add codes anyway (y/n)?'
            user_in = raw_input('>> ')
        if user_in =='y':
            for filename in os.listdir(self.code_dir):
                if not filename.startswith('.'):
                    print 'enter coder name (file: %s)' % filename
                    coder_name = raw_input('>> ')
                    coder = self._check_coder(coder_name=coder_name)
                    path = self.code_dir + filename
                    with open(path, 'rb') as codesheet:
                        reader = csv.reader(codesheet)
                        first_row = True
                        header = []
                        for row in reader:
                            if first_row:
                                header = row
                                first_row = False
                            else:
                                codes = {'coder_id':coder['coder_id']}
                                tweet_id = None
                                tweet_text = None
                                for count,col in enumerate(row):
                                    if header[count] == 'db_id':
                                        tweet_id = col
                                    elif header[count] == 'text':
                                        tweet_text = col.decode('latin-1').encode('utf-8')
                                    elif col is not '' and header[count] in self.first_codes:
                                        codes['first'] = header[count]
                                    elif col is not '' and header[count] in self.second_codes:
                                        codes[header[count]] = 1
                                if tweet_id:
                                    self.code_comparison.update(
                                        {'db_id':tweet_id,'text':tweet_text},
                                        {
                                            #'$setOnInsert':{'codes':[]},
                                            '$addToSet':{'codes':codes}
                                        },
                                        upsert=True
                                    )
            return True
        else:
            print 'aborting code import...'
            return False

    # Adjudicate codes for each coded tweet.
    # Add fields for first and second tier codes
    def adjudicate_db(self):
        tweets = self.code_comparison.find()
        for tweet in tweets:
            code_counts = {}
            for codes in tweet['codes']:
                code_counts[codes['first']] = code_counts.get(codes['first'],0) + 1
                for code in self.second_codes:
                    code_counts[code] = code_counts.get(code,0) + codes.get(code,0)
            second_final = []
            for code in self.second_codes:
                if code_counts[code] == 1:
                    second_final = ['Adjudicate']
                    break
                elif float(code_counts.get(code,0))/self.num_coders > .5:
                         second_final.append(code)
            self.first_codes.sort(key=lambda x: code_counts.get(x,0), reverse=True)
            if code_counts.get(self.first_codes[0],0) > .5:
                first_final = self.first_codes[0]
            else:
                first_final = 'Adjudicate'
            self.code_comparison.update({'db_id':tweet['db_id']},
                                        {
                                            '$set':{'first_final':first_final},
                                            '$addToSet':{
                                                'second_final':{
                                                    '$each':second_final
                                                }
                                            }
                                        }
                                    )

    def process(self,in_name,out_name):
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

    def adjudicate(self):
        print 'enter a valid input file name (include file extension):'
        fname_in = raw_input('>> ')
        print 'enter a valid output file name (include file extension):'
        fname_out = raw_input('>> ')
        fname_out = os.path.join(os.path.dirname(__file__),os.pardir,'samples/') + fname_out
        process(in_name=fname_in,out_name=fname_out)

    def coder_agreement(self,db,coders,codes=None):
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

    def agreement_sheet(self,db,coders):
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
    #codes = ['Uncodable','Unrelated','Affirm','Deny','Neutral']
    #alt_codes = [['Uncertainty'],['Ambiguity'],['Implicit']]
    rumor = 'lakemba'
    coders = 3
    #code_comparison = utils.mongo_connect(db_name='code_comparison',collection_name=rumor)
    #compression = utils.mongo_connect(db_name='sydneysiege_cache',collection_name=rumor)
    p = Processor(rumor=rumor,num_coders=coders)
    #p.read_codes()
    p.adjudicate_db()
    #adjudicate_db(db=code_comparison,coders=coders)
    #coder_agreement(db=code_comparison,coders=coders,codes=alt_codes)
    #for x in alt_codes:
    #    coder_agreement(db=code_comparison,coders=coders,codes=x)
    #agreement_sheet(db=code_comparison,coders=coders)

if __name__ == "__main__":
    main()
