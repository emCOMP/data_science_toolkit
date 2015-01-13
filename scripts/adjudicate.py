import csv,utils,os

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

def main():
    adjudicate()

if __name__ == "__main__":
    main()
