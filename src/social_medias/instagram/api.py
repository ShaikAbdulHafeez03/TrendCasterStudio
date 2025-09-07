import json
import os
import requests
import time

from dotenv import load_dotenv

# from instagram.utils import InstagramPostCreator
load_dotenv()


INSTAGRAM_ACCESS_TOKEN=os.getenv("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_ACCOUNT_ID=os.getenv("INSTAGRAM_ACCOUNT_ID")

class InstagramAPI:
    def __init__(self, access_token=INSTAGRAM_ACCESS_TOKEN, ig_user_id=INSTAGRAM_ACCOUNT_ID):
        self.access_token = access_token
        self.ig_user_id = ig_user_id

    def create_image_container(self, image_url, caption):
        """
        Creates a container for posting an image.

        Args:
            image_url (str): Publicly accessible image URL
            caption (str): Image caption
            share_to_feed (bool): Whether to share to feed
        """
        url = f"https://graph.facebook.com/v23.0/{self.ig_user_id}/media"
        params = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.access_token,
        }

        response = requests.post(url, params=params)
        result = response.json()
        print("📷 Image Container Creation Response:", result)
        return result    

    def create_reel_container(self,video_url,caption,share_to_feed=True,collaborators=None,cover_url=None,audio_name=None,user_tags=None,location_id=None,thumb_offset=None):
            """
            Creates a container for posting a REEL video.

            Args:
                video_url (str): Publicly accessible MP4 URL
                caption (str): Reel caption
                share_to_feed (bool): Whether to share to feed
                collaborators (list[str]): Instagram usernames to tag as collaborators
                cover_url (str): URL of cover image
                audio_name (str): Optional custom audio name
                user_tags (list[dict]): Format: [{'username': 'user1', 'x': 0.5, 'y': 0.5}]
                location_id (str): Facebook location ID
                thumb_offset (int): Offset in seconds for thumbnail
            """

            url = f"https://graph.facebook.com/v23.0/{self.ig_user_id}/media"

            params = {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "share_to_feed": str(share_to_feed).lower(),
                "access_token": self.access_token,
            }

            if collaborators:
                params["collaborators"] = ",".join(collaborators)

            if cover_url:
                params["cover_url"] = cover_url

            if audio_name:
                params["audio_name"] = audio_name

            if user_tags:
                # Must be a JSON array string
                params["user_tags"] = json.dumps(user_tags)

            if location_id:
                params["location_id"] = location_id

            if thumb_offset is not None:
                params["thumb_offset"] = thumb_offset

            response = requests.post(url, params=params)
            result = response.json()
            print("🎬 Reels Container Creation Response:", result)

            return result

    def get_container_status(self, container_id):
        """
        Checks the status of the created reels container.

        Args:
            container_id (str): The ID of the reels container.
        """
        url = f"https://graph.facebook.com/v23.0/{container_id}"
        params = {
            "access_token": self.access_token,
            "fields": "status,status_code"
        }
        response = requests.get(url, params=params)
        result = response.json()
        print("📦 Container Status Response:", result)
        return result
    
    def wait_until_published(self, container_id, timeout=1000, poll_interval=5):
        """
        Waits until the Instagram container's status_code becomes 'PUBLISHED'.
        
        Exits early if status_code becomes 'ERROR' or 'EXPIRED'.

        Args:
            container_id (str): Instagram container ID
            timeout (int): Max time to wait in seconds
            poll_interval (int): Time between checks (in seconds)
        """
        start_time = time.time()

        while True:
            status = self.get_container_status(container_id)

            status_code = status.get("status_code")
            status = status.get("status")

            print(f"📦 status_code: {status_code}, status: {status}")

            if status_code == "FINISHED":
                print("✅ Container has been published!")
                return True
            elif status_code in ("ERROR", "EXPIRED"):
                print(f"❌ Container failed with status: {status_code}")
                return False

            if time.time() - start_time > timeout:
                print("⏰ Timed out waiting for container to publish.")
                return False

            time.sleep(poll_interval)

    def publish_media(self, container_id):
        """
        Uploads a video to Instagram Business account using a publicly accessible video URL.

        Args:
            reels_container_id (str): The ID of the reels container created by create_reel_container.
        """
        url = f"https://graph.facebook.com/v23.0/{self.ig_user_id}/media_publish"
        params = {
            "access_token": self.access_token,
            "creation_id": container_id
        }
        self.wait_until_published(container_id)
        response = requests.post(url, params=params)
        result = response.json()
        print("📹 Video Post Response:", result)
        return result


# api = InstagramAPI()

# container_id = api.create_image_container(
#     image_url="https://storage.googleapis.com/social_automator/videos/Gemini_Generated_Image_pzxythpzxythpzxy.png",
#     caption="Check out this amazing reel!",
# )

# api.publish_media(container_id["id"])