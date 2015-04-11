import csv,utils,os,kappa


# processor class for importing and adjudicating tweets
class Processor(object):

    def __init__(self,rumor,num_coders):

        # db for raw and finals codes
        self.code_comparison = utils.mongo_connect(db_name='code_comparison',
                                                   collection_name=rumor)
        # db for mapping unique tweets to non-uniques
        self.compression = utils.mongo_connect(db_name='rumor_compression',
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
        # rumor to process
        self.rumor = rumor

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
                                    elif header[count].lower() == 'text':
                                        tweet_text = col.decode('latin-1').encode('utf-8')
                                    elif col is not '' and header[count] in self.first_codes:
                                        codes['first'] = header[count]
                                        codes[header[count]] = 1
                                    elif col is not '' and header[count] in self.second_codes:
                                        codes[header[count]] = 1
                                if 'first' not in codes:
                                    codes['first'] = None
                                if tweet_id:
                                    self.code_comparison.update(
                                        {'db_id':tweet_id,},
                                        {
                                            '$setOnInsert':{'text':tweet_text},
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
        print 'Machine adjudicate without adjudication sheet (Y/n)?'
        user_in = raw_input('>> ')
        if user_in == 'n':
            machine_adj = False
        else:
            machine_adj = True
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
            if float(code_counts.get(self.first_codes[0],0))/self.num_coders > .5:
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

    # create a coding csv file of just tweets needing human adjudication
    def write_adjudication(self):
        print '1st or 2nd level adjudication (1/2)?'
        level = raw_input('>> ')
        print 'enter a valid file name'
        fname = raw_input('>> ')
        f_out = utils.write_to_samples(path=(fname + '.csv'))
        f_out.write('"db_id","rumor","text"\n')
        if level == 1:
            query = {'first_final':'Adjudicate'}
        else:
            query = {'second_final':'Adjudicate'}
        tweets = self.code_comparison.find(query)
        for tweet in tweets:
            final_codes = ''
            for code in tweet['codes']:
                if level == 1:
                    final_codes += '%s,' % code['first']
                else:
                    for x in code:
                        if x in self.second_codes:
                            final_codes += '%s,' % x
            result = '"%s","%s","%s","%s",\n' % (tweet['db_id'],self.rumor,tweet['text'],final_codes)
            f_out.write(result.encode('utf-8'))

    # old helper method for adjudicating to file
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

    # old method for adjudicating to file
    def adjudicate(self):
        print 'enter a valid input file name (include file extension):'
        fname_in = raw_input('>> ')
        print 'enter a valid output file name (include file extension):'
        fname_out = raw_input('>> ')
        fname_out = os.path.join(os.path.dirname(__file__),os.pardir,'samples/') + fname_out
        process(in_name=fname_in,out_name=fname_out)

    # calculate agreement for first tier codes
    # based on new schema using key 'first'
    def first_coder_agreement(self):
        mat = []
        tweets = self.code_comparison.find()
        for tweet in tweets:
            result = []
            code_counts = {}
            num_codes = 0
            for code in tweet['codes']:
                if code['first'] in self.first_codes:
                    code_counts[code['first']] = code_counts.get(code['first'],0) + 1
                    num_codes += 1
            for code in self.first_codes:
                if code in code_counts:
                    result.append(code_counts[code])
                else:
                    result.append(0)
            result.append(self.num_coders-num_codes)
            mat.append(result)
        print mat
        aggreement = kappa.computeKappa(mat)


    # calculate agreement for any coding scheme
    # do NOT use key 'first'
    def coder_agreement(self,code_scheme):
        mat = []
        tweets = self.code_comparison.find()
        for tweet in tweets:
            result = []
            code_counts = {}
            num_codes = 0
            for code in tweet['codes']:
                if code.key() in code_scheme:
                    code_counts[code.key()] = code_counts.get(code.key(),0) + 1
                    num_codes += 1
            for code in code_scheme:
                if code in code_counts:
                    result.append(code_counts[code])
                else:
                    result.append(0)
            result.append(self.num_coders-num_codes)
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
    # the rumor identifier
    rumor = 'hijacking'
    # the number of pre-adjudication coders
    coders = 3
    p = Processor(rumor=rumor,num_coders=coders)
    #comment/uncomment this to read codes from sheets
    #p.read_codes()
    p.adjudicate_db()
    
    #Uncomment these to get the adjudication sheets
    p.write_adjudication()

if __name__ == "__main__":
    main()
