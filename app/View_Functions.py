#!/usr/bin/python
from scipy.stats.distributions import binom
from collections import Counter
import operator

def Ranked_List(inputfile, sort_col=1, number_entires = 25, desecending = True):
	"""creates a list from a file that is ranked and then returns the top number of elements .
	Keyword arguments:
	inputfile -- the location of a csv file that contains the list to be ranked 
	number_entires -- number of entires from the list to be returned
	descending -- should list be done in descending order
	sort_col -- column to sort the list of list based on   

	return:
	Top_List -- list of the top N values taken from a sorting of the input csv files
	"""
	Top_List = []
	with open(inputfile,'r') as f:
		for line in f:
			Top_List.append(line.strip().split(',-'))
		Top_List = sorted(Top_List,key=lambda x: float(x[sort_col]),reverse=desecending)
	return Top_List[:number_entires]

def Comment_Topic_ID(LDA_Model,Corpus_Dict,List_of_Tokens,Topic_Order = [10, 4, 7, 9, 8, 2, 6, 5, 1, 3]):

	"""Take's in a list of comments as tokens and returns a list of assigned topic 
	IDs that have been transfomed have numbers that match the LDA visulization

	Keywords:
	LDA_Model -- LDA model object from Gensim 
	Corpus_Dict -- dictonary from all comments made with gensim
	List_of_Tokens -- List of the tokenized comments
	Topic_Order -- List of topic order from the pylDAVis to that topic numbers in 
	               in the graphic meet the labels

	return:
	Ordered_Topic_List -- List of all the topics of the commnents reordered to corespond to the pylDAVis numbers.  The length
	                      of the list is the number of comments and the values at each postion are the topics they best fit
	"""      
	Topic_List = []
	for T in List_of_Tokens:
		Fit = LDA_Model.get_document_topics(Corpus_Dict.doc2bow(T))
		tempTopic = [0,0]
		for F in Fit:
			if F[1]>tempTopic[1]:
				tempTopic = F
		Topic_List.append(tempTopic[0])
	#Reorder the returned topics to 
	print Topic_List
	Ordered_Topic_List = []
	for T in Topic_List:
		Ordered_Topic_List.append(Topic_Order[T])
	return Ordered_Topic_List

def Build_Global_Freq_Dict(filename):
	"""Take's in csv file and build a dict out of it 
	Keywords:
	filename -- location of file 
	
	return:
	Topic_Counts -- dictonary with topics as keys and freqeuncies as values 
	"""
	with open(filename,'r') as f:
          Topic_Counts = {}
          for line in f:
            A = line.strip().split(',')
            Topic_Counts[A[0]] = float(A[1])
	return Topic_Counts
      
def Compute_Binomial_Prob(Topic_List,Global_Topic_Count):
	"""Commutes pValues from a binomial probility distribution given a list of events
	   and a dictonary that descirbes the freqeuncy those events are expected to be 
	   observed at.  The values in the Topic_List must be the keys is in the Global_Topic_Count   
	Keywords:
	Topic_List -- List of all the topics that are being test for disbution, each value should have a labled topic and thats what this list is 
	Global_Topic_Count -- dictonary containing the expected distrbution of topics
	
	returns:
	List_of_Topics_Dict -- List of Dicts with keys as ['names','obs','expected','pval'] sorted by obs
	"""
	
	List_of_Topic_Dict =[]
	Global_Keys =Global_Topic_Count.keys()
	i = 0
	for key,val in dict(Counter(Topic_List)).items():
		List_of_Topic_Dict.append({'name':key,'obs':val,'exp':int(len(Topic_List)*Global_Topic_Count[Global_Keys[i]])})
		if  List_of_Topic_Dict[-1]['exp']>=List_of_Topic_Dict[-1]['obs']:
			List_of_Topic_Dict[-1]['pVal']=binom.cdf(List_of_Topic_Dict[-1]['obs'], len(Topic_List),Global_Topic_Count[Global_Keys[i]] )
		else:
			List_of_Topic_Dict[-1]['pVal']=1-binom.cdf(List_of_Topic_Dict[-1]['obs'], len(Topic_List), Global_Topic_Count[Global_Keys[i]])
		i +=1
	return sorted(List_of_Topic_Dict, key=lambda x: x['obs'], reverse=True)

def Style_from_pVal(List_of_Topic_Dict, colors = ['red','green'],cutoff_pval = 0.05):
	""" Stylizes the Input values for the html page that will display them based on the pVales from the bionmal CDF test
	Keywords:
	List_of_Topics_Dict -- List of Dicts with keys as ['names','obs','expected','pval']
	colors -- colors to code deplted and enriched entires respectivly
	cutoff_pval -- value at which an enriched or depleted tag is applied 

	returns:
	List_of_Topics_Dict -- with html tags added to the enriched and depleted entires as well as a key for 'status' which is [Enriched,Expected,Depleted]

	"""
	for T in range(len(List_of_Topic_Dict)):
		if (List_of_Topic_Dict[T]['obs'] < List_of_Topic_Dict[T]['exp']) and (List_of_Topic_Dict[T]['pVal'] <cutoff_pval):
		  List_of_Topic_Dict[T]['name']= '<font color="'+colors[0]+'">'+List_of_Topic_Dict[T]['name']+'</font>'
		  List_of_Topic_Dict[T]['obs']= '<font color="'+colors[0]+'">'+str(List_of_Topic_Dict[T]['obs'])+'</font>'
		  List_of_Topic_Dict[T]['status'] = '<font color="'+colors[0]+'">'+'Depleted'+'*'+'</font>'
		elif (List_of_Topic_Dict[T]['obs'] > List_of_Topic_Dict[T]['exp']) and (List_of_Topic_Dict[T]['pVal'] <cutoff_pval):
		  List_of_Topic_Dict[T]['name']= '<font color="'+colors[1]+'">'+List_of_Topic_Dict[T]['name']+'</font>'
		  List_of_Topic_Dict[T]['obs']= '<font color="'+colors[1]+'">'+str(List_of_Topic_Dict[T]['obs'])+'</font>'
		  List_of_Topic_Dict[T]['status'] = '<font color="'+colors[1]+'">'+'Enriched'+'*'+'</font>'
		else:
		  List_of_Topic_Dict[T]['status'] = 'Expected'
	return List_of_Topic_Dict

def Build_WordCloud_Input(Tokens,Corpus_Dict,size_freq_mod = 75.0, num_words = 100):
	""" Takes a list of tokens and returns the input dict to the Word_Cloud D3.js function
	Keywords:
	Tokens -- List of lists of Tokens for each comment
	Corpus_Dict -- dictonary from all comments made with gensim
	size_freq_mod -- multiplier to control the size ofhte largest word in the visulization
	num_words -- Limit the total number of words to return from a freqency sorted desceding list

	returns:
	Word_Cloud --  Input for D#.js Word_Cloud function
	"""
	All_Tokens = []
	for T in Tokens:
	    All_Tokens.extend([Corpus_Dict[x[0]] for x in Corpus_Dict.doc2bow(T)])
	Token_Freq = dict(Counter(All_Tokens))
	Sorted_Token_Freq = sorted(Token_Freq.items(), key=operator.itemgetter(1),reverse = True)
	Word_Cloud =[]
	for x in Sorted_Token_Freq:
	    tempDict = {}
	    tempDict['text']=x[0]
	    tempDict['size']=int(round(x[1]*size_freq_mod/Sorted_Token_Freq[0][1]))
	    Word_Cloud.append(tempDict)
	return Word_Cloud[:num_words]