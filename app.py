# load libraries
from flask import Flask, render_template, request, redirect, send_file
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from googletrans import Translator
from collections import Counter
from joblib import load
import pandas as pd
import warnings
import tweepy
import time
import re


warnings.filterwarnings('ignore')

# initial variable
access_token = "1264627461712678913-VaK0Ou4Fd5hYBgdUxSLKb0K8B6cOvH"
access_token_secret = "wl0TMFXiJ3fKO3obXxQGjj8Kl2goPv3yuhRu2GD6v4ew6"
consumer_key = 'NWtNg2CAgVc5MFVHGZK2s5Qab'
consumer_secret = "J4mr7Bu5Wb5R6WJXhPKpVC5YDN4iio2AIUNtlKwIhWhsoLjX8L"

# access Twitter API using our key
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token = (access_token, access_token_secret)
api = tweepy.API(auth, wait_on_rate_limit=True)

# helper function

def search_query(text_query: str, count: int):
	"""
	Function for get list of twitter from twitter API search by input tag
	& maximal count tweets
	"""
	try:
		# creation of query method using parameters
		tweets = tweepy.Cursor(api.search, q=text_query, tweet_mode="extended",
								lang='in').items(count)

		# getting the information from twitter object
		tweet_list = [[tweet.created_at, tweet.id, tweet.full_text] for tweet
		              in tweets]
		# creating a data frame from the list
		tweet_df_from_query = pd.DataFrame(tweet_list,
		                                   columns=['Date', 'tweet_id',
		                                            'tweet_text'])
		# return result
		return tweet_list
	except BaseException as e:
		print('failed_on_status', str(e))
		time.sleep(3)

def preprocess_tweet(tweet):
	"""
	Preprocess the text in a single tweet
	arguments: tweet = a single tweet in form of string
	"""
	# convert the tweet to lower case
	tweet.lower()
	# convert "a-thread" to empty strin
	tweet = tweet.replace("a thread", "")
	# convert "-11fess" to empty string
	tweet = tweet.replace("-11fess", "")
	# convert sumber: to empty string
	tweet = tweet.replace("(sumber:", "")
	# convert RT to empty string
	tweet = tweet.replace("RT", "")
	# convert all urls to sting "URL"
	tweet = re.sub('((www\.[^\s]+)|(https?://[^\s]+))', '', tweet)
	# convert all @username to "AT_USER"
	tweet = re.sub('@[^\s]+', '', tweet)
	# correct all multiple white spaces to a single white space
	tweet = re.sub('[\s]+', ' ', tweet)
	# convert "#topic" to just "topic"
	tweet = re.sub(r'#([^\s]+)', r'\1', tweet)
	# convert emoticon
	tweet = ''.join(s for s in tweet if ord(s) > 31 and ord(s) < 126)
	return tweet


def load_from_file(model_file):
	try:
		return load(model_file)
	except:
		raise "Model File Not Found"



def prediction(list_cleaned_tweet):
	"""
	Function for Generate Predicted Label using Naive Bayes Model
	"""
	# define translate & sentiment_polarity
	translator = Translator()
	analytics = SentimentIntensityAnalyzer()
	# Store each row label in this list
	label = []
	# iterate each tweets
	for word in list_cleaned_tweet:
		# load model into textBlob
		textblob = load_from_file("model.pkl")
		try:
			# main algorithm
			translated = translator.translate(word, src='id', dest='en')
			hasil_analisa = analytics.polarity_scores(translated.text)
			hasil_analisa = hasil_analisa['compound']
			# convert numerical predicted label become string label
			if hasil_analisa > 0.2:
				label.append("Positif")
			elif hasil_analisa < -0.2:
				label.append("Negatif")
			else:
				label.append("Netral")
		# exception handler
		except Exception as E:
			print(E)
			label.append("Netral")
			pass
	return label

app = Flask(__name__, template_folder="template", static_folder="static")

tag = []


@app.route("/", methods=["GET", "POST"])
def main():
	if request.method == "POST":
		input_tag = request.form["search"]
		tag.append(input_tag)
		return redirect("/result")
	return render_template("index.html")

# ref : https://stackoverflow.com/questions/52644035/how-to-show-a-pandas-dataframe-into-a-existing-flask-html-table
@app.route("/show", methods=["GET", "POST"])
def show():
	# read data
	data = pd.read_excel("data_sentiment.xlsx")
	# parse excel dataset into html format
	return data.to_html()


# ref : https://stackoverflow.com/questions/24577349/flask-download-a-file
@app.route("/download", methods=['GET', 'POST'])
def download():
	# download files
	return send_file('data_sentiment.xlsx', as_attachment=True)


@app.route("/result", methods=["GET", "POST"])
def result():
	# crawling tag by user input
	input_tag = "".join(tag[-1])
	# get tweets by tag & clean tweets
	raw_result = [text[2] for text in search_query(input_tag, 50)]
	clean_result = [preprocess_tweet(word) for word in raw_result]
	# get label sentiment base on model ML
	predict_label = prediction(clean_result)
	# generate dataframe and save to excel file
	data = pd.DataFrame({"Tweets":clean_result,
	                     "Labels":predict_label})
	data.to_excel("data_sentiment.xlsx", index=False)
	# count sentiment
	count = Counter(predict_label)
	# get example sentiment for each label
	try:
		pos_text = data[data["Labels"] == "Positif"]["Tweets"].tolist()[0]
	except:
		print("i")
		pos_text = "Tweets Positive 404"
	try:
		neg_text = data[data["Labels"] == "Negatif"]["Tweets"].tolist()[0]
	except:
		print("ii")
		neg_text = "Tweets Negative 404"
	try:
		neu_text = data[data["Labels"] == "Netral"]["Tweets"].tolist()[0]
	except:
		print("iii")
		neu_text = "Tweets Neutral 404"

	# most count sentiment
	most_count = max(count, key=count.get)

	return render_template("result.html", pos = count["Positif"],
	                       neg = count["Negatif"], neu = count["Netral"],
	                       pos_text = pos_text, neu_text = neu_text,
	                       neg_text = neg_text, most_count = most_count)


if __name__ == "__main__":
	app.run(debug=True, use_reloader=False)