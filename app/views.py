#import statements
import sys
from gensim import corpora, models, similarities
from flask import render_template, request
from app import app
import pymysql as mdb
import os
from collections import Counter
import matplotlib.pyplot as plt
import pickle
from flask import jsonify,Response, make_response
import pickle
import json 
from collections import Counter
import operator
from scipy.stats.distributions import binom
import View_Functions as VF

@app.route('/autocomplete_drugname',methods=['GET'])
#Build an autocomplete list for drug names
def autocomplete():
    #Connects to local SQL database that contains all the product names and numbers
    db = mdb.connect(user="root", host="localhost", db="epi_reddit",  charset='utf8') 
    with db: 
      cur = db.cursor()
      cur.execute("SELECT name FROM product ")
      All_Drug_Names = cur.fetchall()
      All_Drug_Names = [x[0] for x in All_Drug_Names]
    #Returns a JSON that is used to help autocomplete drug names in drug databse 
    return jsonify(json_list=All_Drug_Names) 


@app.route('/summaries')
#Builds top rank list for the users to perform a more general survey of the drugs
def summaries():
  #Top 25 by total mentions
  Top_Mentions = VF.Ranked_List('app/static/Data/Drugs_Mention_Counts_Table.csv', sort_col = 4)
  #Top 25 by non-spam comments
  Top_Good_Mentions = VF.Ranked_List('app/static/Data/Drugs_Mention_Counts_Table.csv',sort_col = 1)
  #Top 25 subreeddit normalized by diving post number by log10 of SR subscribers  
  Top_SRs = VF.Ranked_List('app/static/Data/SubReddit_Mention_Counts_Table.csv', sort_col=2)
  return render_template("summaries.html", Top_Mentions = Top_Mentions, Top_Good_Mentions=Top_Good_Mentions,Top_SRs=Top_SRs)


#@app.route('/index')
#def index():
# return render_template("index.html")

@app.route('/slides')
def slides():
 return render_template("slides.html")

@app.route('/')
@app.route('/input')
def input():
  return render_template("input.html")

@app.route('/Single_Drug')
def query_drug():
  #pull from input fields within input.html and store the values
  
  #Name of the product inputed
  product_name = request.args.get('Drug_ID')
  #Number of Subreddits requested
  requested_subreddits = int(request.args.get('Num_SR'))
  #Pulls the name of each the user inputed topic feilds from below the model 
  Topic = [[] for x in range(10)]
  Topic[0] = request.args.get('Topc1')
  Topic[1] = request.args.get('Topc2')
  Topic[2] = request.args.get('Topc3')
  Topic[3] = request.args.get('Topc4')
  Topic[4] = request.args.get('Topc5')
  Topic[5] = request.args.get('Topc6')
  Topic[6] = request.args.get('Topc7')
  Topic[7] = request.args.get('Topc8')
  Topic[8] = request.args.get('Topc9')
  Topic[9] = request.args.get('Topc10')
  #Pull the posts that mention a specfic drug from SQL
  
  con = mdb.connect('localhost', 'root', '', 'epi_reddit',charset='utf8', init_command='SET NAMES UTF8')
  with con: 
      cur = con.cursor()
      cur.execute("""SELECT product_ID FROM product WHERE name LIKE '%s'""" % product_name )
      Product_ID = cur.fetchone()
      sql_statment = """SELECT c.subreddit,c.body,c.spam,c.permalink,c.title 
                        FROM content c
                        INNER JOIN product_lookup pl 
                           on c.content_ID = pl.content_ID
                        WHERE pl.product_ID = '%s'""" % Product_ID
      cur.execute(sql_statment)
      Result = cur.fetchall()

  #Filter out the posts that are flagged as spam 
  Good_Result = [x for x in Result if x[2] == 0]
  product_name = product_name.capitalize()
  
  #Check to make sure the drug is in the list or the drug is not 100% classified as spam posts 
  if len(Good_Result) != 0:
      #Build a dictonary to descirbe the product information that will be passed as prod-table and populate the first row ofthe Single_Drug.html document 
      Product_Info = {'name': product_name,'id':Product_ID[0],'spam': len(Result)-len(Good_Result),'other':len(Good_Result),'total':len(Result),'spam rate':'%0.002f%%' % (float(len(Result)-len(Good_Result))/len(Result)*100)}
      
      #Open stored tokenized comments for the selected drug
      File = 'Comments for %s.txt' % Product_ID[0]
      Tokens = []
      with open('app/static/Tokens/only token txt/'+ File,'rb') as f:
        for line in f:
          Tokens.append(line.strip().split(','))
      # Looks to see if the file has exactly 500 comments in it, because if it does that means that total topics have been cut off to the top 500 comments by score 
      # and is only reporting those comments in the topic list and word bubble.  This then triggers a warning a string to let the user know this happened on the page that returns  
      if len(Tokens) == 500:
        At_500 = 'Only Data for the Top 500 Posts are Shown'
      else:
        At_500 =''

      #Load in pre-trained LDA model 
      L = models.LdaModel.load('app/static/model/All_Drug_Drugs_RM_WC_SPAM.mdl', mmap='r')
      dictionary = corpora.Dictionary.load('app/static/model/All_Drug_Drugs_RM_WC_SPAM.dict')

      #Build and stylize topic list for selected topics        
      #Assign Topics
      Ordered_Topic_List=VF.Comment_Topic_ID(L,dictionary,Tokens)
      #Open global topic freqeuncy list
      Topic_Counts = VF.Build_Global_Freq_Dict('app/static/Data/Total_Topic_Freq.txt')
      #Calculate pVals with a binomail CDF test
      Topic_List=VF.Compute_Binomial_Prob(Ordered_Topic_List,Topic_Counts)
      #Change Key values to names
      for p in Topic_List:
        p['name'] = Topic[int(p['name'])-1]
      #Style table for a return to the HTML based on the pValues from the previosu test
      Topic_List=VF.Style_from_pVal(Topic_List)


      #Build Dictionary for word cloud
      Word_Cloud =VF.Build_WordCloud_Input(Tokens,dictionary)
      #SECTION ON SUBREDDIT FREQ 

      #Open global SR freqeuncy list
      Unique_Mentions_SRs_FreqDict = VF.Build_Global_Freq_Dict('app/static/Data/Total_UniqueComment_SR_Freq.txt')
      # Grab all the subreddits from the SQL query
      Subreddits = [x[0] for x in Good_Result]
      SR_List=VF.Compute_Binomial_Prob(Subreddits,Unique_Mentions_SRs_FreqDict)
      for SR in SR_List:
        SR['url'] = SR['name']
      SR_List=VF.Style_from_pVal(SR_List)
      return render_template("Single_Drug.html", prod_table = Product_Info, num_subreddits = requested_subreddits,
      drug =product_name, Word_Cloud=Word_Cloud, Topic_List = Topic_List, Warning=At_500, subreddits=SR_List[:requested_subreddits]) 

  else: 
    #Return if the drug name is not found or if it is 100% spam posts that are found
    if len(Result) == 0:
      Source = product_name + ' was not found in any Reddit comments' 
    else:
      Source = '100 Percent of ' +product_name + ' mentions were spam'
    return render_template("No_Drug.html", Source=Source)

