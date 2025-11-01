# from pydantic import BaseModel
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
load_dotenv()
# from operator import itemgetter

# from site_scraper import scrape_website

# NEWS_API_KEY = "f4e427c002914d8fb09da36d8d46f1e6"
import os
tech_news_domains = [
    "techcrunch.com",
    "beebom.com",
    "thenextweb.com",
    "engadget.com",
    "mashable.com",
    "arstechnica.com",
    "venturebeat.com",
    "recode.net",
    "digitaltrends.com",
    "gadgets360.com",
    "inc42.com",
    "yourstory.com",
    "livemint.com",
    "economictimes.indiatimes.com",
]
class NewsAPI:
    def __init__(self, api_key: str = os.getenv("NEWS_API_KEY"), domains: list[str] = None):
        self.api_key = api_key
        self.domains = domains if domains is not None else tech_news_domains

    def get_top_news(self, topic: str | None = None, count: int = 50) -> list[dict]:
        domains = ",".join(self.domains)
        from_date = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")
        to_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if topic:
            url = (
                f"https://newsapi.org/v2/everything?q={topic}"
                f"&sortBy=popularity&searchIn=title,content,description"
                f"&pageSize={count}&language=en&domains={domains}"
                f"&from={from_date}&to={to_date}&apiKey={self.api_key}"
            )
        else:
            url = (
                f"https://newsapi.org/v2/everything"
                f"?sortBy=popularity"
                f"&pageSize={count}&language=en&domains={domains}"
                f"&from={from_date}&to={to_date}&apiKey={self.api_key}"
            )

        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Error fetching news: {response.status_code} - {response.text}")

        articles = response.json().get("articles", [])
        if not articles:
            raise ValueError("No news articles found for the given parameters.")
        return articles

