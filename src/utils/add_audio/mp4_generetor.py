import os
import re
import uuid
import subprocess
import requests
import ffmpeg
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

class ReelGenerator:
    """
    A class to generate a short video reel from a news title and a static image
    by using AI to find and select appropriate background audio.
    """
    def __init__(self, image_path: str, download_dir: str = "./temp_audio"):
        """
        Initializes the ReelGenerator for a specific image file.

        Args:
            image_path (str): The path to the static image for the video.
            download_dir (str, optional): Directory for temporary audio files.
                                          Defaults to "./temp_audio".
        """
        # Check for the image file immediately
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"The specified image file was not found at: {image_path}")
        self.image_path = image_path
        
        # Fetch API keys from environment variables
        self.gemini_api_key = os.getenv("GOOGLE_API_KEY")
        self.freesound_api_key = os.getenv("FREE_SOUND_API_KEY")

        # Validate that the keys were successfully loaded
        if not self.gemini_api_key or not self.freesound_api_key:
            raise ValueError(
                "API keys for Gemini and Freesound are required. "
                "Ensure they are set in your .env file."
            )

        self.download_dir = download_dir
        self.gemini_model = self._configure_gemini(self.gemini_api_key)

    def _configure_gemini(self, api_key: str):
        """Configures the Gemini client and returns a model instance."""
        try:
            genai.configure(api_key=api_key)
            return genai.GenerativeModel('gemini-2.5-flash')
        except Exception as e:
            raise RuntimeError(f"Failed to configure Gemini API: {e}") from e

    @staticmethod
    def check_ffmpeg_installed() -> bool:
        """Checks if the ffmpeg executable is available in the system's PATH."""
        try:
            subprocess.run(
                ["ffmpeg", "-version"], 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("---")
            print("ERROR: ffmpeg executable not found.")
            print("Please install ffmpeg and ensure it's in your system's PATH.")
            print("Download from: https://ffmpeg.org/download.html")
            print("---")
            return False

    def _extract_keywords(self, news_title: str) -> list[str]:
        """Extracts music-related keywords from a news title using the Gemini API."""
        print("Extracting keywords with Gemini...")
        try:
            prompt = f"""
            You are an expert in music, mood, and audio descriptors.
            From the following news title, pick exactly 4 or 5 single-word keywords 
            (instrument, mood, genre, environment, etc.) for searching audio clips.
            If you cannot find 4 or 5, return the best ones you can (min 1).
            Return only a comma-separated list of keywords.

            Title: {news_title}
            """
            resp = self.gemini_model.generate_content(prompt)
            print()
            keywords = [k.strip() for k in resp.text.strip().split(",") if k.strip()]
            print(f"Keywords from Gemini: {keywords}")
            return keywords
        except Exception as e:
            print(f"Error calling Gemini API for keyword extraction: {e}")
            return []

    def _search_and_download(self, keywords: list[str]) -> list[dict]:
        """Searches Freesound and downloads audio previews."""
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        
        audio_files = []
        for word in keywords:
            print(f"Searching Freesound for keyword: '{word}'...")
            try:
                params = {
                    "query": word,
                    "filter": "duration:[10 TO 15]",
                    "sort": "rating_desc",
                    "fields": "id,name,previews"
                }
                headers = {"Authorization": f"Token {self.freesound_api_key}"}
                resp = requests.get("https://freesound.org/apiv2/search/text/", headers=headers, params=params)
                resp.raise_for_status()
                results = resp.json().get("results", [])

                if not results:
                    print(f"No results found for '{word}'.")
                    continue

                first_result = results[0]
                previews = first_result.get("previews", {})
                mp3_url = previews.get("preview-lq-mp3") or previews.get("preview-hq-mp3")

                if mp3_url:
                    audio_content = requests.get(mp3_url).content
                    fpath = os.path.join(self.download_dir, f"{uuid.uuid4().hex}.mp3")
                    with open(fpath, "wb") as f:
                        f.write(audio_content)
                    audio_files.append({'path': fpath, 'name': first_result.get('name', 'Untitled')})
                    print(f"Downloaded '{first_result.get('name')}' for keyword '{word}'.")

            except requests.exceptions.RequestException as e:
                print(f"Error making request to Freesound for '{word}': {e}")
        return audio_files

    def _select_best_audio(self, news_title: str, audio_files: list[dict]) -> str:
        """Selects the best audio track from a list using the Gemini API."""
        if not audio_files:
            return ""

        track_list = "\n".join([f"{i+1}. {audio['name']}" for i, audio in enumerate(audio_files)])
        print("\nAsking Gemini to select the best audio track...")

        try:
            prompt = f"""
            You are an AI assistant selecting background audio for a news video.
            News Headline: "{news_title}"

            Available audio tracks:
            {track_list}

            Which track is most fitting? Return *only the number* of your choice.
            """
            resp = self.gemini_model.generate_content(prompt)
            match = re.search(r'\d+', resp.text)
            
            if not match:
                print(f"Gemini gave an invalid response: '{resp.text}'. Defaulting to the first track.")
                return audio_files[0]['path']

            choice_index = int(match.group(0)) - 1
            if 0 <= choice_index < len(audio_files):
                selected = audio_files[choice_index]
                print(f"Gemini selected track #{choice_index + 1}: \"{selected['name']}\"")
                return selected['path']
            else:
                print(f"Gemini's choice ({choice_index + 1}) is invalid. Defaulting to the first track.")
                return audio_files[0]['path']

        except Exception as e:
            print(f"Error during Gemini audio selection: {e}. Defaulting to first track.")
            return audio_files[0]['path']

    def _create_video(self, audio_path: str, output_path: str = "output.mp4") -> str:
        """Creates a video from the stored image path and an audio file."""
        print("Creating video with ffmpeg...")
        try:
            # Use the image_path stored in the instance
            img = ffmpeg.input(self.image_path, loop=1, framerate=1)
            aud = ffmpeg.input(audio_path)
            
            (
                ffmpeg.output(
                    img.video,
                    aud.audio,
                    output_path,
                    vcodec="libx264",
                    acodec="aac",
                    pix_fmt="yuv420p",
                    shortest=None,
                    movflags="faststart",
                    **{"tune": "stillimage"}
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True, quiet=True)
            )
            print(f"ffmpeg successfully created video at: {output_path}")
            return output_path
        except ffmpeg.Error as e:
            print("An error occurred with ffmpeg:")
            print("FFMPEG stderr:", e.stderr.decode())
            raise

    def _cleanup(self):
        """Removes the temporary audio directory and its contents."""
        if not os.path.exists(self.download_dir):
            return
        try:
            print(f"Cleaning up directory: {self.download_dir}")
            for filename in os.listdir(self.download_dir):
                file_path = os.path.join(self.download_dir, filename)
                os.unlink(file_path)
            os.rmdir(self.download_dir)
            print("Cleanup complete.")
        except Exception as e:
            print(f"Error during cleanup: {e}")

    def generate(self, news_title: str) -> str:
        """
        Orchestrates the full process of generating a video reel.

        Args:
            news_title (str): The news headline to base the reel on.

        Returns:
            str: The file path of the generated video.
        """
        video_file = ""
        try:
            keywords = self._extract_keywords(news_title)
            if not keywords:
                raise RuntimeError("Could not extract keywords from the title.")

            audio_files = self._search_and_download(keywords)
            if not audio_files:
                raise RuntimeError("No audio could be downloaded for any keyword.")
            print("\nDownloaded audio options:", [f['name'] for f in audio_files])

            selected_audio_path = self._select_best_audio(news_title, audio_files)
            if not selected_audio_path:
                raise RuntimeError("Could not select an audio file.")
            print("Final selected audio path:", selected_audio_path)

            # Note: _create_video now gets the image path from `self`
            video_file = self._create_video(selected_audio_path)
        
        finally:
            self._cleanup()
        
        return video_file

# ========== Example Run ==========

# if __name__ == "__main__":
#     if not ReelGenerator.check_ffmpeg_installed():
#         exit()

#     IMAGE_FILE = "insta_post_1757876054_f7c9bb.jpg"
    
#     try:
#         # 1. Create an instance of the generator, passing the image path.
#         # This will fail early if the image doesn't exist.
#         reel_creator = ReelGenerator(image_path=IMAGE_FILE)
        
#         # 2. Define the other inputs
#         news_headline = "Breaking: AI Revolutionizes Healthcare with Predictive Diagnostics"
        
#         # 3. Generate the reel
#         print("\n--- Starting Reel Generation ---")
#         output_video = reel_creator.generate(news_headline)
#         print("\n--- Reel Generation Complete ---")
#         print(f"Video reel created at: {output_video}")

#     except (FileNotFoundError, ValueError, RuntimeError, Exception) as e:
#         print(f"\nAn error occurred: {e}")