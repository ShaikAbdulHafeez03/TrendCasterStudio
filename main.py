
from src.social_medias.twitter.api import TwitterAPI
from src.researcher.filter_trend import FilterTrend
from src.researcher.news_api import NewsAPI
from src.researcher.process_news import NewsSocialImageGenerator
from src.researcher.site_scraper import scrape_website
from src.social_medias.instagram.api import InstagramAPI
from src.social_medias.instagram.utils import InstagramPostCreator
from src.utils.file_uploader.upload_file import upload_to_gcs


def main():
    fetch_trending_news=NewsAPI()
    news_list=fetch_trending_news.get_top_news()
    print("Total news articles fetched:", len(news_list))
    filter_top_news=FilterTrend()
    get_top_urls=filter_top_news.select_top_3_news_by_viral_potential(news_list)

    for item in get_top_urls:
        get_scrape=scrape_website(item['url'],item['source'])
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


if __name__ == "__main__":
    main()