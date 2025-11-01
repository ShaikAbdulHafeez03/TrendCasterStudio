from flask import Flask, render_template, request, redirect, url_for, flash
from src.social_medias.twitter.api import TwitterAPI
from src.researcher.filter_trend import FilterTrend
from src.researcher.news_api import NewsAPI
from src.researcher.process_news import NewsSocialImageGenerator
from src.researcher.site_scraper import scrape_website
from src.social_medias.instagram.api import InstagramAPI
from src.social_medias.instagram.utils import InstagramPostCreator
from src.utils.file_uploader.upload_file import upload_to_gcs
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "SUPER_SECRET_KEY")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    import io
    import sys
    log_stream = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = log_stream
    results = []
    try:
        fetch_trending_news = NewsAPI()
        news_list = fetch_trending_news.get_top_news()
        filter_top_news = FilterTrend()
        get_top_urls = filter_top_news.select_top_3_news_by_viral_potential(news_list)
        for item in get_top_urls:
            get_scrape = scrape_website(item['url'], item['source'])
            generator = NewsSocialImageGenerator(get_scrape)
            file_path = generator.process_news()
            gen_insta = InstagramPostCreator(
                image_path=file_path,
                news_dict=get_scrape
            )
            content = gen_insta.process_insta_post()
            file_url = upload_to_gcs(content["post_image"])
            twitter_api = TwitterAPI()
            twitter_api.tweet_content(get_scrape, content["post_image"])
            insta_post = InstagramAPI()
            container_id = insta_post.create_image_container(
                image_url=file_url,
                caption=content["caption"],
            )
            insta_post.publish_media(container_id["id"])
            results.append({
                "news": get_scrape,
                "image_url": file_url,
                "caption": content["caption"]
            })
        flash("Content generated and posted successfully!", "success")
        logs = log_stream.getvalue()
        sys.stdout = old_stdout
        return render_template("result.html", results=results, logs=logs)
    except Exception as e:
        sys.stdout = old_stdout
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
