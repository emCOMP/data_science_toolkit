import re

rumor_terms = {
    ###Navy Shooting Rumors##
    'chatanooga_isis':{
        '$and':[
            {'text':re.compile('isis|islam',re.IGNORECASE)},
            {'text':re.compile('predict|warn|fore|mention|time',re.IGNORECASE)},
            {'text':re.compile('tweet|twitter',re.IGNORECASE)}
        ]
    },
    'tennessee_college':{
        '$and':[
            {'text':re.compile('university|college',re.IGNORECASE)},
            {'text':re.compile('shoot',re.IGNORECASE)}
        ]
    },
    ###Boston Rumors ##
    'girl_running_reu':{
        '$and':[
            {'text':re.compile('girl',re.IGNORECASE)},
            {'text':re.compile('running',re.IGNORECASE)}
        ]
    },
    'sunil_reu':{
        '$or':[
            {'text':re.compile('sunil',re.IGNORECASE)},
            {'text':re.compile('tripathi',re.IGNORECASE)}
        ]
    },
    'navy_seals_reu':{
        '$and':[
            {'$or':[
                {'text':re.compile('navy seal',re.IGNORECASE)},
                {'text':re.compile('blackwater',re.IGNORECASE)},
                {'text':re.compile('black ops',re.IGNORECASE)},
                {'$and':[
                    {'text':re.compile('craft',re.IGNORECASE)},
                    {'text':re.compile('security',re.IGNORECASE)}
                ]}
            ]},
            {"text":{'$not':re.compile('call of duty',re.IGNORECASE)}}
        ]
    },
    'proposal_reu':{
        '$and':[
            {'$or':[
                {'text':re.compile('propos',re.IGNORECASE)},
                {'text':re.compile('marry',re.IGNORECASE)}
            ]},
            {'$or':[
                {'text':re.compile('girl',re.IGNORECASE)},
                {'text':re.compile('woman',re.IGNORECASE)}
            ]}
        ]
    },
    ### DC power outage Rumors ##
    'explosion':{
        '$or':[
            {'text':re.compile('explosion',re.IGNORECASE)},
            {'text':re.compile('blast',re.IGNORECASE)},
            {'text':re.compile('boom',re.IGNORECASE)}
        ]
    },
    'foul_play':{
        '$or':[
            {'text':re.compile('foul',re.IGNORECASE)},
            {'text':re.compile('terror',re.IGNORECASE)},
            {'text':re.compile('attack',re.IGNORECASE)},
            {'text':re.compile('hack',re.IGNORECASE)}
        ]
    },
    ### WestJet Rumors ##
    'signal':{
        '$or':[
            {'text':re.compile('squawk',re.IGNORECASE)},
            {'text':re.compile('code',re.IGNORECASE)},
            {'text':re.compile('alarm',re.IGNORECASE)},
            {'text':re.compile('signal',re.IGNORECASE)},
            {'text':re.compile('button',re.IGNORECASE)},
            {'text':re.compile('transponder',re.IGNORECASE)},
            {'text':re.compile('7500')}
        ]
    },
    'hijacking':{
        '$or':[
            {'text':re.compile('squawk',re.IGNORECASE)},
            {'text':re.compile('signal',re.IGNORECASE)},
            {'text':re.compile('button',re.IGNORECASE)},
            {'text':re.compile('plane',re.IGNORECASE)},
            {'text':re.compile('pilot',re.IGNORECASE)},
            {'text':re.compile('transponder',re.IGNORECASE)},
            {'text':re.compile('west',re.IGNORECASE)},
            {'text':re.compile('flight',re.IGNORECASE)},
            {'text':re.compile('jet',re.IGNORECASE)},
            {'text':re.compile('7500')},
        ]
    },
   ### MH17 RUMORS ##
    'blackbox':{
        '$and':[
            {
                '$or':[
                    {'text':re.compile('rebels',re.IGNORECASE)},
                    {'text':re.compile('separatists',re.IGNORECASE)},
                    {'text':re.compile('terrorists',re.IGNORECASE)}
                ]
            },
            {
                '$or':[
                    {'text':re.compile('blackbox',re.IGNORECASE)},
                    {'text':re.compile('black box',re.IGNORECASE)},
                    {'text':re.compile('recorder',re.IGNORECASE)}
                ]
            }
        ]
    },
	# EBOLA RUMORS ##
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
    ## SYDNEY SIEGE RUMORS ##
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
    # unused
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
            {'text':re.compile(' belt',re.IGNORECASE)},
            {'text':re.compile(' vest',re.IGNORECASE)},
            {'text':re.compile('backpack',re.IGNORECASE)},
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
    # unused
    'tweet':
    {
        '$and':[
            {'text':re.compile('police',re.IGNORECASE)},
            {
                '$or':[
                    {'text':re.compile('ask',re.IGNORECASE)},
                    {'text':re.compile('request',re.IGNORECASE)}
                ]
            },
            {
                '$or':[
                    {'text':re.compile('tweet',re.IGNORECASE)},
                    {'text':re.compile('post',re.IGNORECASE)},
                    {'text':re.compile('social media',re.IGNORECASE)},
                    {'text':re.compile('share',re.IGNORECASE)}
                ]
            }
        ]
    },
    # unused
    'priest':
    {
        'text':re.compile('priest',re.IGNORECASE)
    },
    'hadley':
    {
        '$and':[
            {'text':re.compile('hostage',re.IGNORECASE)},
            {
                '$or':[
                    {'text':re.compile('hadley',re.IGNORECASE)},
                    {'text':re.compile('radio host',re.IGNORECASE)}
                ]
            }
        ]
    },
    'lakemba':
    {
        '$and':[
            {'text':re.compile('lakemba',re.IGNORECASE)},
            {'text':re.compile('^((?!vigil).)*$',re.IGNORECASE)},
        ]
    },
    'flag':
    {
        '$and':[
            {'text':re.compile('flag',re.IGNORECASE)},
            {
                '$or':[
                    {'text':re.compile(' isis',re.IGNORECASE)},
                    {'text':re.compile('#isis',re.IGNORECASE)},
                    {'text':re.compile('isil',re.IGNORECASE)}
                ]
            }
        ]
    },
    'americans_onboard':
    {
        '$and':[
            {
                '$or':[
                    {'text':re.compile('passenger',re.IGNORECASE)},
                    {'text':re.compile('board',re.IGNORECASE)},
                    {'text':re.compile('23',re.IGNORECASE)},
                ]
            },
            {
                '$or':[
                    {'text':re.compile('americans',re.IGNORECASE)},
                    {'text':re.compile('us citizen',re.IGNORECASE)},
                ]
            }
        ]
    },
    'rebels':
    {
        '$and':[
            {'text':re.compile('ukrain',re.IGNORECASE)},
            {'text':re.compile('shot',re.IGNORECASE)},
            {
                '$or':[
                    {'text':re.compile(' rebel',re.IGNORECASE)},
                    {'text':re.compile('separatist',re.IGNORECASE)}
                ]
            }
        ]
    },
    'american_falseflag':
    {
        '$and':[
            {
                '$or':[
                    {'text':re.compile('falseflag',re.IGNORECASE)},
                    {'text':re.compile('false flag',re.IGNORECASE)},
                ]
            },
            {
                '$or':[
                    {'text':re.compile('america',re.IGNORECASE)},
                    {'text':re.compile('usa',re.IGNORECASE)},
                ]
            }
        ]
    },
    'israel_falseflag':
    {
        '$and':[
            {
                '$or':[
                    {'text':re.compile('falseflag',re.IGNORECASE)},
                    {'text':re.compile('false flag',re.IGNORECASE)},
                ]
            },
            {
                '$or':[
                    {'text':re.compile('israel',re.IGNORECASE)},
                    {'text':re.compile('zion',re.IGNORECASE)},
                ]
            }
        ]
    },
    'same_plane':
    {
        '$and':[
            {'text':re.compile('mh17',re.IGNORECASE)},
            {'text':re.compile('mh370',re.IGNORECASE)},
            {'text':re.compile('same',re.IGNORECASE)},
        ]
    },
    'blackbox':{
        '$and':[
            {
                '$or':[
                    {'text':re.compile('rebels',re.IGNORECASE)},
                    {'text':re.compile('separatists',re.IGNORECASE)},
                    {'text':re.compile('terrorists',re.IGNORECASE)}
                ]
            },
            {
                '$or':[
                    {'text':re.compile('blackbox',re.IGNORECASE)},
                    {'text':re.compile('black box',re.IGNORECASE)},
                    {'text':re.compile('recorder',re.IGNORECASE)}
                ]
            }
        ]
    },
}
