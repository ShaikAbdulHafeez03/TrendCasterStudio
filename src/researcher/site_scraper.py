import requests
from bs4 import BeautifulSoup
from newspaper import Article

def scrape_website(url: str,source:str) -> dict:
    try:

        article = Article(url)
        article.download()
        article.parse()

        title = article.title
        image = article.images if article.images else None
        description = article.text[:3000] + "..."  

        if not description.strip():
            resp = requests.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                description = meta_desc.get("content")

        return {
            "topic": title,
            "image": image,
            "description": description,
            "source": source,
            "url": url
        }

    except Exception as e:
        return {"error": str(e), "source": source, "url": url}


# if __name__ == "__main__":
#     url = "https://www.ndtv.com/india-news/improper-phrases-poll-body-on-rahul-gandhis-vote-chori-charge-9102026?pfrom=home-ndtv_topscroll_Imagetopscroll"
#     data = scrape_website(url)
#     print(data)
