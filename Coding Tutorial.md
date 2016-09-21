This tutorial is designed for an EMCOMP DRG student using the data science toolkit for the first time. For full documentation, see https://github.com/emCOMP/data_science_toolkit/wiki

#*How to use the Data Science Toolkit to code a rumor*

##Step 1: Set up your rumor in Mongo

In order to code a rumor, you must first have a database entry in mongo for your rumor, and the event it belongs to. 

##Step 2: Familiarize yourself with the toolkit

In order for the toolkit to work, it needs to be run from your account on the Boston server. To run it, you have to 
navigate to data_science_toolkit/package. It's here that you'll find manage_tweets.py, which is the script you'll be 
using to do everything from training to adjudication. I'll walk you through a complete coding process, but for 
reference's sake, here's documentation on the proper format as well as all possible parameters and links to details on 
each:


The script should be called from the terminal, passing parameters to the script like so:

    python manage_tweets.py ACTION EVENTNAME RUMORNAME --other_options

**ACTION** is one of the available actions listed [below](https://github.com/emCOMP/data_science_toolkit/wiki/Tweet-
Management#available-actions).

**EVENTNAME** is the event name (this must be the same as the database name for the event).

**RUMORNAME** is the name of the rumor (must match the rumor name in the database).

**--other_options** is any number of extra parameters. .

<h3>Example</h3>
    python manage_tweets.py generate_training sydneysiege hadley -ss 80

This will generate a training sheet for the Hadley rumor containing 80 tweets.

***

<h2>Available Actions:</h2>

* **[compress](https://github.com/emCOMP/data_science_toolkit/wiki/compress):** Locates all unique tweets by mapping 
duplicate tweets and retweets to an original tweet, and storing these mappings in a rumor_compression database.

* **[generate_training](https://github.com/emCOMP/data_science_toolkit/wiki/generate_training):**
Generates a sample of tweets from the specified rumor for training.

* **[generate_coding](https://github.com/emCOMP/data_science_toolkit/wiki/generate_coding):**
Generates coding sheets for the specified rumor, assigning tweets based on the loads specified in a coder_assignments 
csv file.

* **[generate_adjudication](https://github.com/emCOMP/data_science_toolkit/wiki/generate-adjudication):**
Generates adjudication sheets for the specified level of codes (first-level codes only, both, or second-level codes 
only).

* **[upload_adjudication](https://github.com/emCOMP/data_science_toolkit/wiki/upload_adjudication):**
Uploads adjudication sheets to the database.

* **[propagate_codes](https://github.com/emCOMP/data_science_toolkit/wiki/propagate_codes):**
Propagates codes from the code_comparison database to the event database. (Applies codes from each unique tweet to all 
duplicates of that tweet).

* **[upload_coding](https://github.com/emCOMP/data_science_toolkit/wiki/upload_coding):**
Uploads the codes after each coder has finished with their individual sheet. This must be done before the adjudication 
sheets can be created.

##Step 3: Training

The coding process begins by compiling a list of training tweets (usually around 100) to be tackled by your coding 
group in order to help refine their understanding of the rumor, and your definiton. manage_tweets.py will generate 
this csv automatically. Simply type the following:

    python manage_tweets.py generate_training EVENTNAME RUMORNAME -ss 100

This will generate a training csv for RUMORNAME within EVENTNAME containing 100 tweets.

The csv output path can be modified with -p, but by default, your csv will be found in IO/EXPORT/sample.csv

***

To begin training, go into the DRG google drive, create a folder for your rumor, add a definition document that 
details the exact definition of your rumor, convert the csv to a google sheet, and put it in the folder as well.

When you're done training, you can move on to coding.

##Step 4: Coding

There are two things you'll need to learn before you generate coding csvs.

+ The --coders_per parameter. It determines the number of times each tweet will be coded by a human. If you aren't 
sure what this should be for your rumor, contact Kate.
+ You need to supply the toolkit with a csv that dictates how the tweets will be distributed for each coder. The csv 
should be put into data_science_toolkit/package/IO/coder_assignments.csv and be in this format:
![alt text](http://i.imgur.com/j4pLUQi.png)

Once you're ready, your command should look something like this:


    python manage_tweets.py generate_coding EVENTNAME RUMORNAME --coders_per 2

***

Your coding csvs will be found in /data_science_toolkit/package/IO/EXPORT. Put them into a coding folder for your 
rumor on google drive, name them after each coder, and convert them to google sheets. 

Once your rumor has been coded, saving the codes is fairly simple. Take your completed sheets off Google, convert them 
back into csvs, and place them in data_science_toolkit/package/IO/IMPORT. be sure that this folder is *otherwise empty 
with the exception of your new coding sheets.* Once that's finished, input

    python manage_tweets.py upload_coding EVENTNAME RUMORNAME --coders_per 2

Make sure all parameters match the parameters you used to generate the coding sheets in the first place.

##Step 5: Adjudication

Before you generate your adjudication sheets, you need to know a few things.

**1. The 'adjudication level' for which to generate sheets.** _(required parameter)_

There are three 'adjudication levels':

1. Tweets Requiring Adjudication on First-Level Codes Only **'first'**
2. Tweets Requiring Adjudication on Both Levels **'both'**
3. Tweets Requiring Adjudication on Second-Level Codes Only **'second'**

To specify this pass the appropriate string from the list above using the **-al** or **--adjudication_level** 
parameters:

    python manage_tweets.py generate_adjudication sydneysiege hadley -al 'both'

**2. The how many tweets should be assigned to each adjudicator.** _(required)_

To specify this, you should construct a CSV file using the following format:
![alt text](http://i.imgur.com/GxRzDRN.png)

This csv file should be placed in:

    data_science_toolkit/package/IO/adjudicator_assignments.csv

***

Once you're ready, your call should look something like this:

    python manage_tweets.py generate_adjudication EVENTNAME RUMORNAME -al 'both'

***

Pass your adjudication sheets on to your adjudicators in whichever method you prefer. Once adjudication is finished, 
place the completed sheets in data_science_toolkit/package/IO/IMPORT. Again, make sure that this folder is *completely 
empty* save for your adjudication sheets.

Once you're done, make the following command:

    python manage_tweets.py upload_adjudication EVENTNAME RUMORNAME -al 'both'

As with coding, make sure you use the same parameters here that you used to generate these sheets in the first place.

##Step 5: Save your codes to the database

Simply input the following command, making sure EVENTNAME and RUMORNAME match your event.

    python manage_tweets.py propagate_codes EVENTNAME RUMORNAME
