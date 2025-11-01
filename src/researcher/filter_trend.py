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
        print("Preparing articles for Gemini input...")
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
You are a Viral Content Strategist with a deep understanding of behavioral psychology and media "game theory." Your single mission is to stop the scroll and hijack user attention. You are not just finding "interesting" news; you are finding the one perfect psychological trigger to maximize shares, comments, and views.

You specialize in technology, startups, fintech, and breakthrough research, but you know that the topic is secondary to the trigger.

From the following list of news articles (title + content), you must select the single most potent, "click-worthy" article that will explode on platforms like Instagram (Reels) and YouTube (Shorts).

Your Selection Criteria (The Viral "Game")
Your choice must be based on its ability to exploit one or more of these core psychological drivers. Ask yourself: "Does this story...":

Create a Massive Curiosity Gap?

Does it present a puzzle, a paradox, or a secret that users will feel compelled to solve?

Example Trigger: "This new AI can do what? The creators are trying to shut it down."

Trigger a "Pattern Interrupt" (Shock/Awe)?

Does it shatter a commonly held belief? Does it reveal something that sounds like science fiction but is real today?

Example Trigger: "Scientists just reversed aging... in mice. Humans are next."

Manufacture "Social Currency"?

Will sharing this make the user look smart, informed, or "in-the-know"? Is it a "digital status symbol"?

Example Trigger: "Stop investing in X. This new fintech platform makes it obsolete."

Provoke a Strong Emotional Response (FOMO, Outrage, Hope)?

Does it make the user feel they are missing out on the next big thing?

Does it reveal an injustice or a "hack" that feels unfair?

Does it promise a utopian future or a solution to a massive problem?

Example Trigger: "This startup's new battery could end the climate crisis. Why is nobody talking about it?"

The Task
Review the News articles. Find the one article that best leverages this psychological framework. Do not pick a "good" article. Pick the "addictive" one.

Return strictly the top 8 article that meets this high-stakes criteria.

News articles: {formatted_articles}

OUTPUT RULES
Output strictly in raw JSON (array of objects with "url" and "source" keys)

Do not include backticks, labels, explanations, or any extra text

Do not add comments or formatting beyond JSON

Example:
[ 
{{"url": "https://example.com/article1", "source": "TechCrunch"}},
{{"url": "https://example.com/article2", "source": "Xyz News"}},
{{"url": "https://example.com/article3", "source": "etc News"}},
{{"url": "https://example.com/article4", "source": "TechCrunch"}},
{{"url": "https://example.com/article5", "source": "TechCrunch"}},
{{"url": "https://example.com/article6", "source": "TechCrunch"}},
{{"url": "https://example.com/article7", "source": "TechCrunch"}},
{{"url": "https://example.com/article8", "source": "TechCrunch"}}
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