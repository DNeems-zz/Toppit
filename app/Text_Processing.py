

import re
import re
import nltk
import pymysql as mdb
import numpy as np
def clean(text):
    """
    Function taking a comment and makign it into tokens.  In order http tagged web addreses are removed
    then removes all non alphbetical letters.  Words shorter than 3 charecters and then tokenizes with the 
    default nltk tokenizer 

    Keywords:
    text -- The text of a comment

    return:
    The comment as a single string with all the tokens joined by a space charecter.
    """
    brackets = re.compile(r'(\[|\])')
    html = re.compile(r'\(http://.*\)')
    nonan = re.compile(r'[^a-zA-Z ]')
    shortword = re.compile(r'\W*\b\w{1,2}\b')
    clean_text = brackets.sub('',nonan.sub('',html.sub('',text)))
    words = nltk.word_tokenize(shortword.sub('',clean_text.lower()))
    return ' '.join(word.lower() for word in words )


def heuristic_spam_filter(text):
    """
    Function to look over comments with a set of heuristic rules to see if certian
    words appear in the text.  If thye do the value returns True and the comment can 
    be marked as spam
    Keywords:
    text -- The text of a comment

    return:
    spam -- Boolean that states if the post is spam (True) or not spam (False)
    """
    spam = False
    if r'**:' in text.lower():
        spam = True
    elif r'**were to buy**' in text.lower():
        spam = True
    elif r'were to buy:' in text.lower():
        spam = True
    elif r'acheter:' in text.lower():
        spam = True
    elif r'acheter**' in text.lower():
        spam = True
    elif r'comprar**' in text.lower():
        spam = True    
    elif r'comprar:'  in text.lower():
        spam = True    
    elif r'var kan jag'  in text.lower():
        spam = True    
    elif r'ostopaikat'  in text.lower(): #Finnish
        spam = True    
    elif r'hvor kan jeg'  in text.lower():
        spam = True
    elif r'dove acquistare'  in text.lower(): 
        spam = True    
    elif r'PGP'  in text:
        spam = True
    elif r'\[source'  in text.lower():
        spam = True
    elif r'gotmilk'  in text.lower():
        spam = True
    elif r'givemegossip'  in text.lower():
        spam = True
    #Remove HTML then look for very short posts 
    html = re.compile(r'\http://.*\s')
    text=html.sub('',text)
    if len(text) <250:
        spam = True
    return spam

def wordcount_spam_filter(single_Drug_Dict,comment_ID_list,Drug_Name,comment_pos=0,ID_pos = 1,Freq_Cutoff = 0.05, con =mdb.connect('localhost', 'root', '', 'epi_reddit',charset='utf8', init_command='SET NAMES UTF8')):
    Mention_Rate = []
    for comment in comment_ID_list:
        Comment_Dicts_Clean=(clean(comment[comment_pos]))
        Comment_Dicts_Tokens=Comment_Dicts_Clean.split()
        #Calcluates the number of times the tagged drug appears in the comment and divides it by the number of tokens in the comment
        Mention_Rate.append(Comment_Dicts_Clean.count(Drug_Name.lower())/float(len(Comment_Dicts_Tokens)))
    Mention_Rate = np.array(Mention_Rate)
    
    #Splits results based on the rate at which tokens appear
    New_Spam=[comment_ID_list[x] for x in np.where(Mention_Rate>Freq_Cutoff)[0]]
    New_Good=[comment_ID_list[x] for x in np.where(Mention_Rate<=Freq_Cutoff)[0]]
    #Runs only if new spam is found
    if len(New_Spam) > 0:
        New_Good_ID = [x[ID_pos] for x in New_Good]
        New_Spam_ID = [x[ID_pos] for x in New_Spam]
        single_Drug_Dict['content ID']=New_Good_ID
        #Flag the new spam as spam
        with con: 
            cur = con.cursor()
            ID =','.join(["'"+x+"'" for x in New_Spam_ID])
            cur.execute("""UPDATE content set spam = 1 WHERE content_ID IN (%s) """ % ID)
        single_Drug_Dict['good']=single_Drug_Dict['good']-len(New_Spam)
        single_Drug_Dict['spam']=single_Drug_Dict['spam']+len(New_Spam)
        single_Drug_Dict['spam rate'] = single_Drug_Dict['spam']/float(single_Drug_Dict['mentions'])
    return single_Drug_Dict