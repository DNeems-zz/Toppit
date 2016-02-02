import sys
sys.path.append("/home/dneems/Data/Eppiemico Data/functions")
from gensim import corpora, models, similarities
from flask import render_template, request
from app import app
import pymysql as mdb
import SQL_Calls
import os
from collections import Counter
import matplotlib.pyplot as plt
import Word_Processing
from wordcloud import WordCloud
from Word_Processing import Frequency_dist as FD
import Text_Filtering
import pickle
from flask import jsonify
import pickle
import json 



@app.route('/autocomplete_drugname',methods=['GET'])
def autocomplete():
    db = mdb.connect(user="root", host="localhost", db="epi_reddit",  charset='utf8') 
    with db: 
      cur = db.cursor()
      cur.execute("SELECT name FROM product ")
      All_Drug_Names = cur.fetchall()
      All_Drug_Names = [x[0] for x in All_Drug_Names]

    search = request.args.get('autocomplete')
    app.logger.debug(search)
    return jsonify(json_list=All_Drug_Names) 


@app.route('/summaries')
def summaries():
  with open('/home/dneems/app/Data/Drug_Summary.pkl','rb') as f:
    Sorted_Found_Drug= pickle.load(f)
  return render_template("summaries.html", drug_summary = Sorted_Found_Drug)

@app.route('/')

@app.route('/index')
def index():
 return render_template("index.html")

@app.route('/input')
def cities_input():
  return render_template("input.html")

@app.route('/Single_Drug')
def query_drug():
  #pull 'ID' from input field and store it
  product_name = request.args.get('Drug_ID')
  requested_subreddits = int(request.args.get('Num_SR'))
  con = mdb.connect('localhost', 'root', '', 'epi_reddit',charset='utf8', init_command='SET NAMES UTF8') #host, user, password, #database
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

  with con: 
      cur = con.cursor()
      cur.execute("""SELECT product_ID FROM product WHERE name LIKE '%s'""" % product_name )
      Product_ID = cur.fetchall()
      Product_Name = Product_ID[0][0]
      sql_statment = """SELECT c.subreddit,c.body,c.spam,c.permalink,c.title 
                        FROM content c
                        INNER JOIN product_lookup pl 
                           on c.content_ID = pl.content_ID
                        WHERE pl.product_ID = '%s'""" % Product_Name
      cur.execute(sql_statment)
      Result = cur.fetchall()
  Good_Result = [x for x in Result if x[2] == 0]
  product_name = product_name.capitalize()
  Product_Info = {'name': product_name,'id':Product_ID[0][0],'spam': len(Result)-len(Good_Result),'other':len(Good_Result),'total':len(Result),'spam rate':'%0.002f%%' % (float(len(Result)-len(Good_Result))/len(Result)*100)}
  File = 'Comments for %s' % Product_ID[0][0]
  with open('app/static/Tokens/drug/'+ File,'rb') as f:
    Comments = pickle.load(f)
  Tokens = [x['Tokens'] for x in Comments]
  L = models.LdaModel.load('app/static/model/All_Drug_Drugs_RM_WC_SPAM.mdl', mmap='r')
  dictionary = corpora.Dictionary.load('app/static/model/All_Drug_Drugs_RM_WC_SPAM.dict')
  Topic_List = []
  for T in Tokens:
    Fit = L.get_document_topics(dictionary.doc2bow(T))
    tempTopic = [0,0]
    for F in Fit:
        if F[1]>tempTopic[1]:
            tempTopic = F
    Topic_List.append(tempTopic[0])
  Topic_Order = [6,10,9,5,1,2,3,7,4,8]
  Ordered_Topic_List = []
  for T in Topic_List:
      Ordered_Topic_List.append(Topic_Order[T])

  Word_Bubble = []
  for i,c in dict(Counter(Ordered_Topic_List)).items():
    Word_Bubble.append({'name':Topic[i-1],'size':c})
  print 'test'
  subreddit_list = [x[0] for x in Good_Result]
  subreddit_freq_List = []
  for k,v in (dict(Counter(subreddit_list))).iteritems():
    subreddit_freq_List.append({'name':k, 'number':v })
  subreddit_freq_List = sorted(subreddit_freq_List, reverse=True, key=lambda k: k['number']) 
  #json_list = json.dumps(subreddit_freq_List[:requested_subreddits])
  return render_template("Single_Drug.html", prod_table = Product_Info, num_subreddits = requested_subreddits,
    drug =product_name, subreddits=subreddit_freq_List[:requested_subreddits], Word_Bubble=Word_Bubble) 



@app.route('/output_nospam')
def cities_output_nospam():
  #pull 'ID' from input field and store it
  product_name = request.args.get('Drug_ID')
  requested_subreddits = int(request.args.get('Num_SR'))

  db = mdb.connect(user="root", host="localhost", db="epi_reddit",  charset='utf8') 
  
  with db: 
    cur = db.cursor()
    #just select the product name from the epi_reddit that the user inputs
    cur.execute("SELECT name, product_ID FROM product WHERE name='%s';" % product_name)
    query_results = cur.fetchall()
    products = []
    for result in query_results:
        products.append(dict(name=result[0], product_ID=result[1]))
        cur.execute("SELECT COUNT(*) FROM product_lookup WHERE product_ID='%s';" % result[1])
        result = cur.fetchall()
        products[-1]['mentions']=str(result[0][0])

    Single_Drug = SQL_Calls.Single_Product_Table(name=product_name)
    gr = Text_Filtering.id_spam(Single_Drug[1])
    Spam_Rate=Text_Filtering.spam_rate(gr,Single_Drug[1])
    Single_Drug=Text_Filtering.rm_spam(gr,Single_Drug[1],Single_Drug[0])
    products[-1]['mentions']=str(len(Single_Drug[1]))


    Reddit_Counter = Counter(list(Single_Drug[0].subreddit));
    subreddits = []
    for sr in Reddit_Counter.most_common(requested_subreddits):
        subreddits.append(dict(name=sr[0], number=sr[1]))
    plt.ioff()
    Tokens = Word_Processing.create_tokens(Single_Drug[1], min_char = 3)
    wordcloud = WordCloud().generate(' '.join(Tokens))
    plt.imshow(wordcloud)
    plt.axis("off")
    plt.savefig('/home/dneems/app/static/Word_Cloud_%s_nospam.png' % product_name)
    plt.close()
        
    fdist=FD([Tokens])
    Freqncy = []
    for w in fdist.most_common(25):
        try:
           Freqncy.append(Freqncy[-1] +fdist.freq(w[0]))
        except:
           Freqncy.append(fdist.freq(w[0]))
           
          
    plt.plot(Freqncy)
    plt.xticks(range(25), [str(w[0]) for w in fdist.most_common(25)], rotation = "vertical")
    plt.subplots_adjust(bottom=0.25)
    Max_Val=round((max(Freqncy)*100 % 5) *5 + max(Freqncy)*100)
    plt.yticks([x/100.0 for x in range(0,int(Max_Val)+1,5)],['{:3.2f}%'.format(x) for x in range(0,int(Max_Val)+1,5)])
    plt.title('Top 25 Most Common Words')
    plt.savefig('/home/dneems/app/static/Common_Words_%s_nospam.png' % product_name)
    plt.close()
   



  #call a function from a_Model package. note we are only pulling one result in the query
  #pop_input = products[0]['population']
  #the_result = ModelIt(city, pop_input)
  return render_template("output_nospam.html", prod_table = products, num_subreddits = requested_subreddits, 
         subreddits = subreddits, drug =product_name, spam_rate = Spam_Rate)
