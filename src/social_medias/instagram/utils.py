from PIL import Image, ImageDraw, ImageFont
import textwrap
from google import genai

class InstagramPostCreator:    
    def __init__(self, image_path, news_dict, output_path=None, font_path=None):
        import os
        self.image_path = image_path
        self.news_dict = news_dict
        self.output_path = output_path
        # Set default font path if not provided
        if font_path is None:
            noto_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "fonts", "Noto_Serif", "NotoSerif-VariableFont_wdth,wght.ttf")
            dm_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "fonts", "DM_Sans", "DMSans-VariableFont_opsz,wght.ttf")
            self.font_path = noto_path if os.path.exists(noto_path) else dm_path
        else:
            self.font_path = font_path
        self.client=genai.Client(api_key="AIzaSyBrfnzJTeygWBx8ZKu4PyaADT5ZuL9MgwQ")

    def generate_content(self, news_dict):
        """
        Generate heading, description, caption, and hashtags for a news post using Gemini LLM.
        Args:
            news_dict (dict): Should contain 'title', 'description', and optionally 'context' or 'source'.
        Returns:
            dict: {"heading": ..., "description": ..., "caption": ..., "hashtags": ...}
        """
        import json
        title = news_dict.get("title") or news_dict.get("topic") or "Untitled"
        description = news_dict.get("description") or news_dict.get("context") or "No description available."
        context = news_dict.get("context") or ""
        # Prompt for Gemini
        prompt = f'''
You are a social media content expert. Given the following news, generate:
- heading: a catchy, concise headline (max 30 words)
- description: a short, attractive concise crux summary (max strictly under 60 words)
- caption: a creative, engaging Instagram caption (max 60 words)
- hashtags: 5-10 relevant hashtags (comma separated, no # in the list)

Keep heading and description together under 200 words total. Make all text easy to read and suitable for Instagram. Do not repeat the title in the description or caption. Do not use quotes or markdown. Output as a JSON object with keys: heading, description, caption, hashtags.

News Title: {title}
News Description: {description}
News Context: {context}
'''
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "temperature": 0.7,
                "response_mime_type": "application/json"
            },
        )
        raw_output = response.text.strip()
        print("Gemini content output:", raw_output)
        try:
            return json.loads(raw_output)
        except json.JSONDecodeError:
            # Fallback: extract JSON substring with regex
            import re
            pattern = r"\{.*\}"  # match JSON object
            match = re.search(pattern, raw_output, re.DOTALL)
            if match:
                json_str = match.group(0).strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    print("⚠️ Still failed to decode JSON. Extracted string:")
                    print(json_str)
                    return {}
            else:
                print("⚠️ No JSON found in Gemini response.")
                return {}

    def validate_image(self, image_path):
        # Validate the image file for Instagram requirements (e.g., file type, size)
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
        max_size_mb = 10  # Maximum size in MB

        if not any(image_path.endswith(ext) for ext in valid_extensions):
            raise ValueError("Invalid image format. Supported formats are: jpg, jpeg, png, gif.")
        
        import os
        if os.path.getsize(image_path) > max_size_mb * 1024 * 1024:
            raise ValueError("Image size exceeds the maximum limit of 10 MB.")
        
        return True


    def generate_instagram_post(self, image_path, heading, description,
                                output_path=None, font_path="fonts/Noto_Serif/NotoSerif-VariableFont_wdth,wght.ttf"):
        import os
        WIDTH, HEIGHT = 1080, 1920
        IMAGE_HEIGHT = int(HEIGHT * 0.45)

        img = Image.open(image_path).convert("RGB")
        img = img.resize((WIDTH, IMAGE_HEIGHT), Image.LANCZOS)

        base = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        base.paste(img, (0, 0))
        draw = ImageDraw.Draw(base)

        # Use provided font_path or the default from self.font_path
        font_path = font_path or self.font_path
        try:
            heading_font = ImageFont.truetype(font_path, 60) if font_path else ImageFont.load_default(2)
            desc_font = ImageFont.truetype(font_path, 40) if font_path else ImageFont.load_default(10)
        except OSError:
            print(f"⚠️ Could not load font at {font_path}. Falling back to default font.")
            heading_font = ImageFont.load_default()
            desc_font = ImageFont.load_default()

        draw.rectangle([(0, IMAGE_HEIGHT), (WIDTH, HEIGHT)], fill=(0, 0, 0))

        x_center = WIDTH // 2
        y = IMAGE_HEIGHT + 50

        for line in textwrap.wrap(heading, width=30):
            bbox = draw.textbbox((0, 0), line, font=heading_font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            draw.text((x_center - w / 2, y), line, font=heading_font, fill=(255, 255, 255))
            y += h + 10

        y += 50

        # Render description text
        for line in textwrap.wrap(description, width=50):
            bbox = draw.textbbox((0, 0), line, font=desc_font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            draw.text((x_center - w / 2, y), line, font=desc_font, fill=(200, 200, 200))
            y += h + 6

        # Save to assets folder if output_path is not provided
        if not output_path:
            assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "assets")
            os.makedirs(assets_dir, exist_ok=True)
            import time
            import uuid
            filename = f"insta_post_{int(time.time())}_{uuid.uuid4().hex[:6]}.jpg"
            output_path = os.path.join(assets_dir, filename)

        base.save(output_path)
        print(f"Saved to {output_path}")
        return output_path

    def process_insta_post(self):
        content = self.generate_content(self.news_dict)
        post_image = self.generate_instagram_post(
            image_path=self.image_path,
            heading=content["heading"],
            description=content["description"],
            output_path=self.output_path,
            font_path=self.font_path
        )
        return {
            "post_image": post_image,
            "caption": content.get("caption", "") + "\n" + content.get("hashtags", "")
        }
if __name__ == "__main__":
    post= InstagramPostCreator(
        image_path="/WhatsApp Image 2025-07-21 at 12.23.33 PM.jpeg",
        news_dict={
            "title": "Meta Acquires Play AI: Powering Next-Gen Natural Voices",
            "description": "Meta has acquired Play AI, a startup behind hyper-realistic AI-generated voices for audio content creation. The entire Play AI team joins Meta, boosting projects in Meta AI, audio-based content tools, and future wearables."
        },)
    post.generate_instagram_post(
        image_path="social_post_1757262816_hu3end_e703de_1.png",
        heading=" Tesla's $1T Pay Package for Elon Musk Sparks Debate: Are the Goals Too Easy?",
        description="Tesla's board has proposed an unprecedented $1 trillion compensation package for CEO Elon Musk. However, critics point out that the performance benchmarks are significantly less ambitious than Musk's own previous pledges, such as reducing a 20 million electric vehicle per year goal to 20 million total over a decade. This move comes as Tesla's sales growth has stalled, raising questions about accountability and the true value of the proposed deal, which still requires shareholder approval.",
        output_path="output_post.jpg",
        font_path="fonts/Noto_Serif/NotoSerif-VariableFont_wdth,wght.ttf"
    )
