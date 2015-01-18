import re

rumor_terms = {
    'red_cross':{
        '$and':[
            {'text':re.compile('vaccine',re.IGNORECASE)},
            {
                '$or':[
                    {'text':re.compile('red cross|redcross',re.IGNORECASE)},
                    {'text':re.compile(' ARC ',re.IGNORECASE)},
                    {'text':re.compile(' IRC ',re.IGNORECASE)}
                ]
            }
        ]
    },
    'semen':{
        '$or':[
            {'text':re.compile('semen',re.IGNORECASE)},
            {'text':re.compile('breast milk',re.IGNORECASE)},
            {'text':re.compile('breastmilk,re.IGNORECASE')}
        ]
    },
    'frontier':{
        '$and':[
            {'text':re.compile('frontier',re.IGNORECASE)},
            {
                '$or':[
                    {'text':re.compile('ban',re.IGNORECASE)},
                    {'text':re.compile('grounded',re.IGNORECASE)}
                ]
            }
        ]
    },
    'quarantine':
    {
        '$or':[
            {'text':re.compile('camps',re.IGNORECASE)},
            {'text':re.compile('trailers',re.IGNORECASE)}
        ]
    },
    'gunmen':
    {
        '$or':[
            {
                '$and':[
                    {'text':re.compile('gunman',re.IGNORECASE)},
                    {
                        '$or':[
                            {'text':re.compile('single',re.IGNORECASE)},
                            {'text':re.compile('one',re.IGNORECASE)},
                            {'text':re.compile(' 1 ',re.IGNORECASE)},
                            {'text':re.compile('only',re.IGNORECASE)},
                        ]
                    }
                ]
            },
            {
                '$and':[
                    {'text':re.compile('gunmen',re.IGNORECASE)},
                    {
                        '$or':[
                            {'text':re.compile(' 2',re.IGNORECASE)},
                            {'text':re.compile('2 ',re.IGNORECASE)},
                            {'text':re.compile(' 3',re.IGNORECASE)},
                            {'text':re.compile('3 ',re.IGNORECASE)},
                            {'text':re.compile('two',re.IGNORECASE)},
                            {'text':re.compile('three',re.IGNORECASE)},
                            {'text':re.compile('multiple',re.IGNORECASE)},
                        ]
                    }
                ]
            }
        ]
    },
    'isis':
    {
        '$or':[
            {'text':re.compile(' isis',re.IGNORECASE)},
            {'text':re.compile('#isis',re.IGNORECASE)},
        ]
    },
    'suicide':
    {
        '$or':[
            {'text':re.compile('suicide',re.IGNORECASE)},
            {'text':re.compile('belt',re.IGNORECASE)},
            {'text':re.compile('vest',re.IGNORECASE)}
        ]
    },
    'airspace':
    {
        '$or':[
            {'text':re.compile('airspace',re.IGNORECASE)},
            {'text':re.compile('air space',re.IGNORECASE)},
            {'text':re.compile('flights',re.IGNORECASE)},
            {'text':re.compile('no-fly',re.IGNORECASE)},
            {'text':re.compile('no fly',re.IGNORECASE)}
        ]
    },
    'tweet':
    {
        '$and':[
            {'text':re.compile('police',re.IGNORECASE)},
            {'text':re.compile('tweet',re.IGNORECASE)},
        ]
    },
    'priest':
    {
        'text':re.compile('priest',re.IGNORECASE)
    },
    'hadley':
    {
        '$and':[
            {'text':re.compile('hadley',re.IGNORECASE)},
            {
                '$or':[
                    {'text':re.compile('hostage',re.IGNORECASE)},
                    {'text':re.compile('radio host',re.IGNORECASE)}
                ]
            }
        ]
    }
}
