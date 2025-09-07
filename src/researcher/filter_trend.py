import json
import re
import uuid
import os
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv
load_dotenv()

class Urls(BaseModel):
    url: str
    source: str



class FilterTrend:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY")) 

    def select_top_3_news_by_viral_potential(self, news_articles: list[dict]):
        # Format articles for the model
        formatted_articles = "\n".join([
            f"{i+1}. Title: {article.get('title', '')}\n"
            f"Description: {article.get('description', '')}\n"
            f"Content: {article.get('content', '')}\n"
            f"URL: {article.get('url', '')}\n"
            for i, article in enumerate(news_articles)
        ])

        print("Formatted articles for Gemini:\n", formatted_articles)

        # Prompt
        prompt_template = f"""
You are an expert social media content editor specializing in technology, startups, fintech, and breakthrough research stories.

From the following list of news articles (title + content), carefully select the most fascinating, viral-worthy articles that would perform exceptionally well on social platforms like Instagram and YouTube. 
These should be the kinds of stories that spark curiosity, wow audiences, or feel like “must-share” tech facts.

Return at least 3 and at most 5 articles, depending on how many are truly exceptional.

Selection priorities:
- High potential for virality and global appeal
- Strong relevance to tech, fintech, startups, or mind-blowing research
- Surprising, futuristic, or emotionally engaging elements

News articles:
{formatted_articles}

### OUTPUT RULES
- Output strictly in raw JSON (array of objects with "url" and "source" keys)
- Do not include backticks, labels, explanations, or any extra text
- Do not add comments or formatting beyond JSON

### Example:
[
    {{"url": "https://example.com/article1", "source": "TechCrunch"}},
    {{"url": "https://example.com/article2", "source": "Wired"}}
]
"""

        # Call Gemini API directly
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_template,
            config={
                "temperature": 0.7,
                "response_mime_type": "application/json"
            },
        )

        raw_output = response.text.strip()
        print("Raw Gemini response:", raw_output)

        # Try strict JSON parsing
        try:
            return json.loads(raw_output)
        except json.JSONDecodeError:
            # Fallback: extract JSON substring with regex
            pattern = r"\[.*\]|\{.*\}"
            match = re.search(pattern, raw_output, re.DOTALL)
            if match:
                json_str = match.group(0).strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    print("⚠️ Still failed to decode JSON. Extracted string:")
                    print(json_str)
                    return []
            else:
                print("⚠️ No JSON found in Gemini response.")
                return []