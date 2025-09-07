# news_to_social_image.py

import random
import re
import string
import time
import uuid
from google import genai
from google.genai.types import PersonGeneration
from google.genai import types
from PIL import Image
from io import BytesIO
import requests
from dotenv import load_dotenv
import os
load_dotenv()
# AIzaSyBrfnzJTeygWBx8ZKu4PyaADT5ZuL9MgwQ (premium key)
# AIzaSyD8jXzLsFKwLeSnz6a58aRYwE-AurXJWa4
# AIzaSyAbp_V5exN4hQL9uBoFsNdZEnb9_Glxp5A
class NewsSocialImageGenerator:
    def __init__(self, news_dict, api_key=os.getenv("GOOGLE_API_KEY")):
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
        self.news_dict = news_dict
        self.MAX_RETRIES = 3
        self.RETRY_DELAY_SECONDS = 2
        self.BROWSER_HEADER = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
        }

    @staticmethod
    def clean_url(url: str) -> str:
        """Remove unwanted characters like quotes, commas, and brackets from URL."""
        return re.sub(r"[\"'\],]", "", url).strip()

    def download_images(self, image_sources):
        images = []
        for src in image_sources:
            if isinstance(src, Image.Image):
                images.append(src)
                continue

            if not isinstance(src, str):
                print(f"Unsupported type: {type(src)}")
                continue

            src = self.clean_url(src)

            response = None
            for attempt in range(self.MAX_RETRIES):
                try:
                    response = requests.get(
                        src, headers=self.BROWSER_HEADER, timeout=15
                    )
                    response.raise_for_status()
                    break
                except requests.exceptions.RequestException as e:
                    print(f"⚠️ Attempt {attempt + 1}/{self.MAX_RETRIES} failed for {src}: {e}")
                    if attempt + 1 == self.MAX_RETRIES:
                        print(f"🛑 All retries failed for {src}. Skipping.")
                        response = None
                    else:
                        time.sleep(self.RETRY_DELAY_SECONDS)

            if not response:
                continue

            try:
                img = Image.open(BytesIO(response.content)).convert("RGB")
                images.append(img)
            except Exception as e:
                print(f"❌ Failed to process image from {src} (invalid image content): {e}")

        return images

    def filter_relevant_images(self):
        """
        Given a news_dict and a list of image URLs, returns a filtered list of URLs
        that are relevant for creating a social media post.
        """
        image_urls = list(self.news_dict.get("image", []))

        text_prompt = (
            f"From the below news, return only the list of image URLs that are most relevant to the news select only if its related to the news"
            f"and can be used to create a social media post.\n\n"
            f"News Title: {self.news_dict.get('topic')}\n"
            f"News Description: {self.news_dict.get('description')}\n"
            f"News Source: {self.news_dict.get('source')}\n"
            f"Image URLs: {image_urls}"
            "\n\n### NOTE\n Strictly only output the list of URLs and nothing else. And only select the most relevant upto only atmost 2 or 3"
            " STRICTLY DON NOT CHANGE THE URL FORMAT OR ADD OR REMOVE ANY EXTRA CHARACTERS"
        )

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[text_prompt]
        )
        output_text = response.text
        print(output_text)
        print("Model output:", output_text)

        import re
        urls = [url.strip("`") for url in re.findall(r"https?://[^\s`]+", output_text)]
        download_images = self.download_images(urls)
        print(f"Filtered {len(urls)} relevant images.")
        return download_images

    def generate_social_prompt(self, images):
        """
        Generate a clear, concise, and visually descriptive image prompt
        for an image generation model. Takes reference images (PIL Image objects)
        and a news article, then asks Gemini to write a Photoshop-like prompt
        that blends the images with the news context into one Instagram-ready visual.
        """

        # Use images directly (already PIL.Image objects)
        image_objects = images

        # Input text for Gemini
        text_input = (
            "You are an expert social media image prompt writer. "
            "Your job is to generate a **single clear image prompt** for an AI image generator. "
            "The AI will be given both this prompt and the reference images provided. "
            "The goal is to create one Instagram-ready image that visually explains the news story.\n\n"
            "Instructions:\n"
            "- Use the reference images as the foundation, blending them together if needed.\n"
            "- Clearly represent the news story in a visually compelling way.\n"
            "- Preserve any people shown in the images with photorealism.\n"
            "- Keep the style consistent and professional, unless the news tone suggests otherwise.\n"
            "- Write the prompt as if you are describing what Photoshop should create.\n"
            "- Be concise (under 400 tokens), but descriptive enough for image generation.\n\n"
            f"News Title: {self.news_dict.get('topic')}\n"
            f"News Description: {self.news_dict.get('description')}\n"
            f"News Source: {self.news_dict.get('source')}\n\n"
            "Now, generate the **final prompt** for the image model."
        )

        # Call Gemini
        response = self.client.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=image_objects + [text_input],
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You are a professional AI image prompt writer for news media. "
                    "Always output ONE clear and direct prompt that blends the news story "
                    "with the reference images into a single, Instagram-ready final image. "
                    "Keep it minimal (under 400 tokens)."
                ),
                temperature=0.7,
            ),
        )

        refined_prompt = response.text if response.text else None

        if not refined_prompt:
            raise RuntimeError("Gemini did not return any text for the social prompt")

        print("Refined Prompt:", refined_prompt)
        return refined_prompt
    
    def generate_image(self, prompt: str, images):
        """
        Generate a final news-based social media image.
        Takes the refined prompt (from Gemini text model) and reference images,
        then calls the image generation model to create one high-quality,
        Instagram-ready image.
        """

        # Unique file name for saving
        timestamp = int(time.time())
        rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        unique_id = uuid.uuid4().hex[:6]
        output_filename = f"./src/assets/social_post_{timestamp}_{rand_str}_{unique_id}.png"

        # Combine prompt and images
        contents = [prompt] + images

        # Call Gemini Image Model
        response = self.client.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You are an AI image editor and generator for tech news posts. "
                    "Your task is to create a single, polished Instagram-ready image "
                    "based on the provided prompt and input images.\n\n"
                    "Guidelines:\n"
                    "- Always blend or enhance the input images rather than discarding them.\n"
                    "- Clearly illustrate the news story in a compelling, professional way.\n"
                    "- Maintain photorealism unless the prompt explicitly asks otherwise.\n"
                    "- FINAL OUTPUT SIZE MUST BE 1080x1080 pixels for Instagram posts.\n"
                    "- Ensure the result is visually clean, shareable, and high-quality.\n"
                    "### NOTE: Only output one final image per request."
                )
            ),
        )

        # Extract and save image(s)
        print(f"Image response: {response.candidates[0].content}")
        parts = response.candidates[0].content.parts
        for idx, part in enumerate(parts, start=1):
            if part.inline_data is not None:
                image = Image.open(BytesIO(part.inline_data.data))
                file_name = output_filename.replace(".png", f"_{idx}.png")
                image.save(file_name)
                print(f"✅ Saved generated image as {file_name}")
            elif part.text is not None:
                print("⚠️ Model returned text instead of an image:", part.text)

        return file_name
    def process_news(self):
        """
        Full pipeline: convert image set to list, download images, select relevant, 
        generate prompt, and produce final image. Skips if no images can be downloaded.
        """
        print("news taken for processing:", self.news_dict.get("topic"))
        
        filter_relevant_images = self.filter_relevant_images()
        
        # Check if any image URLs were found in the first place
        if not filter_relevant_images:
            print("🛑 No relevant image URLs found. Skipping this news item.")
            return

        print(f"Found {len(filter_relevant_images)} potential images, attempting to download...")
        images = self.download_images(filter_relevant_images)

        # --- ADD THIS CHECK ---
        # If the list of downloaded images is empty, stop processing this news item.
        if not images:
            print("🛑 No images were successfully downloaded after trying all URLs. Skipping this news item.")
            return  # Exit the function early
        # --------------------

        print(f"✅ Successfully downloaded {len(images)} images.")

        print("Generating social media prompt...")
        prompt = self.generate_social_prompt(images)

        print("Generating final image...")
        file_path =self.generate_image(prompt, images)

        return file_path


# Example usage
# if __name__ == "__main__":
#     news_data = {
#         'topic': 'Self-Proclaimed Nazi Kanye West Announces ‘New Economy, Built on Chain’',
#         'image': 
#             {'https://gizmodo.com/app/uploads/2025/07/superman-james-gunn-david-corenswet-336x224.jpg',
#               'https://gizmodo.com/app/uploads/2025/08/Kanye-1200x675.jpg',
#             'https://gizmodo.com/app/uploads/2025/04/GettyImages-2198663028.jpg',
#               'https://gizmodo.com/app/uploads/2024/11/Justin-Sun-founder-of-Tron.jpg', 
#               'https://gizmodo.com/app/uploads/2025/07/bitcoin-photo.jpg',
#                 'https://gizmodo.com/app/uploads/2025/08/Watch-US-Open-Live-on-a-Free-Channel-160x160.jpg',
#                   'https://gizmodo.com/app/uploads/2025/06/trump_memecoin.jpg',
#                     'https://gizmodo.com/app/uploads/2025/07/TCL-D2-Pro-smart-lock-review-7-336x224.jpg',
#                       'https://gizmodo.com/app/uploads/2025/08/kingo-eternals-336x224.jpg',
#                         'https://gizmodo.com/app/uploads/2025/08/kingo-eternals-160x160.jpg',
#                           'https://gizmodo.com/app/uploads/2025/08/Watch-US-Open-Live-on-a-Free-Channel-336x224.jpg',
#                             'https://sb.scorecardresearch.com/p?c1=2&c2=39636245&cv=3.9.1&cj=1', 
#                             'https://gizmodo.com/app/uploads/2025/07/superman-james-gunn-david-corenswet-160x160.jpg',
#                               'https://secure.gravatar.com/avatar/ba4895e6465556d7ce329f935e1167b8?s=46&d=mm&r=g',
#                                 'https://gizmodo.com/app/uploads/2025/08/starwars-visionshed-160x160.jpg', 
#                                 'https://gizmodo.com/app/uploads/2025/08/Kanye.jpg',
#                                   'https://gizmodo.com/app/uploads/2025/08/bladerunner2049-160x160.jpg',
#                                     'https://gizmodo.com/app/uploads/2022/04/db035252532bbc24f6d808a7fd7b6177-300x200.jpg',
#                                       'https://gizmodo.com/app/uploads/2025/08/Bose-QuietComfort-Gen2-2-336x224.jpg',
#                                         'https://gizmodo.com/app/uploads/2024/08/Eric-Trump-and-Donald-Trump-Jr.-.jpg',
#                                           'https://gizmodo.com/app/uploads/2025/08/Genki-Attack-Vector-Switch-2-Case-Battery-Pack-12-336x224.jpg',
#                                             'https://gizmodo.com/app/uploads/2022/04/db035252532bbc24f6d808a7fd7b6177-150x150.jpg',
#                                               'https://gizmodo.com/app/uploads/2025/07/starship-flight-10-160x160.jpeg',
#                                                 'https://gizmodo.com/app/uploads/2025/08/The-Batman-Robert-Pattinson-160x160.jpg',
#                                                   'https://gizmodo.com/app/uploads/2025/08/Sony-Inzone-H9-II-gaming-headphones-PC-and-PS5-10-336x224.jpg',
#                                                     'https://gizmodo.com/app/uploads/2024/11/GettyImages-2163296066.jpg'}, 
#     'description': 'The artist formerly known as Kanye West (he changed his name to “Ye” legally in 2018) is, in addition to being a self-proclaimed “Nazi,” now a denizen of the web3 world he once derided.\n\nOn Wednesday, West took to social media to announce YZY coin. “The official Yeezy token just dropped,” said a bored-looking West in a video posted on his X account. Within hours, YZY had climbed to a market cap of some $3 billion, Wired reports. Not long afterward, the coin predictably plummeted in value and eventually settled around $1.5 billion, Forbes writes.\n\nWest also shared a link to a website with additional details about the new crypto asset, although it doesn’t provide much information. “YZY Money is a concept to put you in control, free from centralized authority,” it says, vaguely. There doesn’t appear to be any sort of white paper or other explanatory note sharing how the asset works. Instead, the site includes a familiar disclaimer: “Users acknowledge that digital assets involve inherent risks and potential for complete loss. Nothing on this site constitutes financial legal or investment advice.” The site’s terms and conditions page also appears to include the stipulation that users waive their right to participate in a class action lawsuit.\n\nWest once claimed that meme coins were not his thing. Wired notes that, in a since-deleted social post, West once said: “I’M NOT DOING A COIN,” adding: “COINS PREY ON THE FANS WITH HYPE.”\n\nThe rapper’s increasingly erratic and bizarre behavior has left many onlookers searching for an explanation. West, himself, has claimed he suffers from a number of mental illnesses, alleging—back in 2018—that he was bi-polar. However, earlier this year, West claimed that, actually, he had been diagnosed with autism, and that the previous diagnosis was incorrect. All we really know is that, at one point, West was releasing killer singles like “Gold Digger” and “Stronger” and going on Ellen Degeneres and then, at some point, he was ranting about Jews, wearing the MAGA hat, showing up to interviews in outfits like this, and dating a woman whose dress code leaves little to the imagination.\n\nTo add to the astounding devolution, West declared earlier this year that he was a “Nazi” and released a single online called “Heil Hitler.” Platforms scrambled to rid themselves of the song, but it persisted, popping up under various pseudonyms on YouTube and Spotify. West’s career has not recovered, so the shitcoin feels like a natural next step.\n\nGizmodo was unable to reach West for comment....',
#     'source': 'Gizmodo',
#     'url': 'https://gizmodo.com/kanye-west-memecoin-cryptocurrency-yzy-2000646460'}
    

#     generator = NewsSocialImageGenerator()
#     print(generator.process_news(news_data))
