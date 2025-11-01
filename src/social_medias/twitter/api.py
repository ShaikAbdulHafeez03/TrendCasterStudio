import os
from dotenv import load_dotenv
import tweepy
from google import genai

load_dotenv()

class TwitterAPI:
    def __init__(self):
        self.api_key = os.getenv("TWITTER_API_KEY")
        self.api_secret_key = os.getenv("TWITTER_API_SECRET")
        self.access_token = os.getenv("ACCESS_TOKEN")
        self.access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self.gen_client = self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

        # Initialize the client if needed elsewhere
        self.client = tweepy.Client(
            bearer_token=self.bearer_token,
            consumer_key=self.api_key,
            consumer_secret=self.api_secret_key,
            access_token=self.access_token,
            access_token_secret=self.access_token_secret
        )
        
        # Authenticate using OAuth1 for media upload
        self.authenticate()

    def authenticate(self):
        auth = tweepy.OAuth1UserHandler(
            self.api_key, self.api_secret_key, self.access_token, self.access_token_secret
        )
        self.api = tweepy.API(auth)

    def create_tweet_content(self, content):
        """Create tweet content."""
        prompt_template = f"""
You are a social media content expert. Given the following news, generate a catchy and concise tweet (max 280 characters) that is engaging and suitable for Twitter. Do not use hashtags or mentions ### CONTENT {content}"""
        response = self.gen_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_template,
            config={
                "temperature": 0.7,
                
            },
        )

        raw_output = response.text.strip()
        print("Raw Gemini response for twitter :", raw_output)
        return raw_output
    
    def tweet_content(self, content, image_path=None):
        """Post a text-only tweet or a tweet with an image."""
        if image_path:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            media = self.api.media_upload(filename=image_path)
            media_id = media.media_id
            response = self.client.create_tweet(text=self.create_tweet_content(content), media_ids=[media_id])
            print(f"Tweet posted successfully! Tweet ID: {response.data['id']}")
            print("Tweet with image posted!")
        else:
            self.api.update_status(status=self.create_tweet_content(content))
            print("Text tweet posted!")

# Usage
if __name__ == "__main__":
    twitter_api = TwitterAPI()
    twitter_api.tweet_content("This is a test tweet with an image.", "Screenshot 2025-09-08 005600.png")
