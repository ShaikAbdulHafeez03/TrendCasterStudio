from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
import time

# === Your Imports ===
from src.social_medias.twitter.api import TwitterAPI
from src.researcher.filter_trend import FilterTrend
from src.researcher.news_api import NewsAPI
from src.researcher.process_news import NewsSocialImageGenerator
from src.researcher.site_scraper import scrape_website
from src.social_medias.instagram.api import InstagramAPI
from src.social_medias.instagram.utils import InstagramPostCreator
from src.utils.file_uploader.upload_file import upload_file
from src.utils.add_audio.mp4_generetor import ReelGenerator


scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
news_list = []       # will store top 8 news dicts (5 main + 3 backup)
used_indexes = set() # track which indexes were already successfully posted


def prepare_daily_news():
    global news_list, used_indexes
    used_indexes.clear()
    print(f"[{datetime.now()}] 📰 Starting daily news preparation...")

    fetch_trending_news = NewsAPI()
    all_news = fetch_trending_news.get_top_news(count=50)
    print(f"Total news articles fetched: {len(all_news)}")

    filter_top_news = FilterTrend()
    news_list = filter_top_news.select_top_3_news_by_viral_potential(all_news)[:8]

    print(f"[{datetime.now()}] ✅ Prepared {len(news_list)} news items for today.")


def process_and_post(index: int):
    global news_list, used_indexes

    next_index = None
    for i in range(index, len(news_list)):
        if i not in used_indexes:
            next_index = i
            break

    if next_index is None:
        print(f"[{datetime.now()}] ⚠️ No unused news left to post.")
        return
    item = news_list[next_index]
    print(f"[{datetime.now()}] 🚀 Attempting to post news #{next_index + 1}: {item.get('title', '')[:60]}...")

    try:
        get_scrape = scrape_website(item['url'], item['source'])
        generator = NewsSocialImageGenerator(get_scrape)
        file_path = generator.process_news()
        if not file_path:
            print(f"⚠️ No image found for news #{next_index + 1}, trying next backup...")
            used_indexes.add(next_index)
            return process_and_post(next_index + 1)  


        gen_insta = InstagramPostCreator(image_path=file_path, news_dict=get_scrape)
        content = gen_insta.process_insta_post()

        # Create reel
        reel_creator = ReelGenerator(image_path=content["post_image"])
        output_video = reel_creator.generate(get_scrape["topic"])
        file_url = upload_file(output_video)

        # Post to Twitter
        twitter_api = TwitterAPI()
        twitter_api.tweet_content(get_scrape, content["post_image"])

        # Post to Instagram
        insta_post = InstagramAPI()
        container_id = insta_post.create_image_container(
            image_url=file_url,
            caption=content["caption"],
        )
        container_id = insta_post.create_reel_container(
            video_url=file_url,
            caption=content["caption"]
        )
        insta_post.publish_media(container_id["id"])

        used_indexes.add(next_index)
        print(f"[{datetime.now()}] ✅ Successfully posted news #{next_index + 1}.")

    except Exception as e:
        print(f"[{datetime.now()}] ❌ Error posting news #{next_index + 1}: {e}")
        used_indexes.add(next_index)
        # Try next backup automatically
        return process_and_post(next_index + 1)



scheduler.add_job(prepare_daily_news, "cron", hour=19, minute=35)


scheduler.add_job(process_and_post, "cron", hour=19, minute=9, args=[0])
scheduler.add_job(process_and_post, "cron", hour=13, minute=30, args=[1])
scheduler.add_job(process_and_post, "cron", hour=16, minute=30, args=[2])
scheduler.add_job(process_and_post, "cron", hour=19, minute=30, args=[3])
scheduler.add_job(process_and_post, "cron", hour=21, minute=30, args=[4])

scheduler.start()

print("✅ Scheduler started. Waiting for jobs...")

try:
    while True:
        time.sleep(60)
except (KeyboardInterrupt, SystemExit):
    scheduler.shutdown()
