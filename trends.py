import streamlit as st
import praw
import openai
import requests
from bs4 import BeautifulSoup
import pandas as pd
from pytrends.request import TrendReq
import time

# --- Setup API Keys and Reddit Client ---
REDDIT_CLIENT_ID = ''Your Reddit Client ID''
REDDIT_CLIENT_SECRET = 'Your Reddit Client Secret'
OPENAI_API_KEY = 'sk-Your OpenAI API Key'

reddit = praw.Reddit(client_id=REDDIT_CLIENT_ID,
                     client_secret=REDDIT_CLIENT_SECRET, user_agent='trending_topic_fetcher')
openai.api_key = OPENAI_API_KEY

# --- Functions for Various Tasks ---
# (Including get_sentiment, fetch_article_content, get_keywords_from_article, check_google_trends, get_tshirt_ideas, get_article_summary)

# ... (Your existing function definitions go here, unchanged) ...


def get_sentiment(headline):
    response = openai.Completion.create(
        engine="gpt-3.5-turbo-instruct",
        prompt=f"What is the sentiment of this headline? Positive, neutral, or negative? \"{headline}\"",
        max_tokens=1000
    )
    sentiment = response.choices[0].text.strip().lower()
    return sentiment


def fetch_article_content(url, headline):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        page = requests.get(url, headers=headers)
        soup = BeautifulSoup(page.content, 'html.parser')
        article_text = ' '.join([p.get_text() for p in soup.find_all('p')])
        return article_text
    except requests.RequestException:
        print(
            f"Error fetching article for URL: {url}. Using headline as the content.")
        return headline  # return the headline if there's an error fetching the article


# get keywords from article
def get_keywords_from_article(article):
    response = openai.Completion.create(
        engine="gpt-3.5-turbo-instruct",
        prompt=f"We are identifying keywords from the below news article. Extract five keywords from the below article in the format of Word1,word2,word3,word4,word5 \n\narticle:{article}",
        max_tokens=2000
    )
   # Sample text from response.choices[0].text
    text = response.choices[0].text
    text_cleaned = text.replace("\n", "").strip()
    keywords = text_cleaned.split(',')
    return keywords

# fetch trends for the keywords


def check_google_trends(keyword):
    pytrends = TrendReq(hl='en-US', tz=360)
    keyword = keyword.strip()
    kw_list = [keyword]
    try:
        pytrends.build_payload(kw_list)
        data_region = pytrends.interest_by_region()
        mean_region_scores = data_region.mean()
        return mean_region_scores[keyword]
    except Exception as e:
        return 0


# Use OpenAI to get t-shirt ideas
def get_tshirt_ideas(keywords, article_text):
    prompt = f"Using the keyword data which has the trending score next to the keyword: {keywords} and the article text: \"{article_text}\", suggest 2 memeworthy t-shirt ideas and also suggest an appropriate picture to go with it"

    response = openai.Completion.create(
        engine="gpt-3.5-turbo-instruct",
        prompt=prompt,
        max_tokens=1500
    )
    idea = response.choices[0].text.strip()
    return idea


def get_article_summary(article):
    prompt = f"Please summarize the following article:\n\n{article}"
    response = openai.Completion.create(
        engine="gpt-3.5-turbo-instruct",
        prompt=prompt,
        max_tokens=1500
    )
    return response.choices[0].text.strip()


# --- Streamlit Interface ---
st.title("Memeworthy Article Analyzer")

# User Inputs
subreddit_input = st.text_input("Enter subreddit (e.g., news)", value="news")
time_filter = st.selectbox("Select time filter", [
                           "day", "week", "month", "year", "all"])
article_limit = st.number_input(
    "Number of articles to fetch", min_value=1, max_value=20, value=5)

if st.button("Fetch and Analyze Articles"):
    with st.spinner("Fetching articles from Reddit..."):
        top_posts = reddit.subreddit(subreddit_input).top(
            time_filter=time_filter, limit=article_limit)

        # Initialize DataFrame
        df = pd.DataFrame(columns=['Article Headline', 'Article Link', 'Article Summary',
                          'Article Keywords', 'Keyword Trend Values', 'TShirt Idea'])

        for post in top_posts:
            headline = post.title
            sentiment = get_sentiment(headline)
            if "positive" in sentiment:
                url = post.url
                article_content = fetch_article_content(url, headline)
                article_summary = get_article_summary(article_content)
                keywords = get_keywords_from_article(article_content)
                keyword_scores = [
                    f"{kw}: {check_google_trends(kw)}" for kw in keywords]
                keyword_data_str = ', '.join(keyword_scores)
                tshirt_idea = get_tshirt_ideas(
                    keyword_data_str, article_content)
                df.loc[len(df)] = [headline, url, article_summary,
                                   ', '.join(keywords), keyword_data_str, tshirt_idea]
                time.sleep(2)  # Avoid hitting rate limits

        st.success("Articles fetched and analyzed!")
        st.write(df)

        # Download button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(label="Download data as CSV", data=csv,
                           file_name='memeworthy_articles.csv', mime='text/csv')

# --- End of Streamlit App ---
