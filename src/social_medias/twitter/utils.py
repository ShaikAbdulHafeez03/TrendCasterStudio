def format_tweet(tweet_content):
    if len(tweet_content) > 280:
        raise ValueError("Tweet content exceeds the maximum length of 280 characters.")
    return tweet_content.strip()

def validate_media(media):
    if not isinstance(media, (str, list)):
        raise TypeError("Media must be a string or a list of strings.")
    if isinstance(media, list):
        for item in media:
            if not isinstance(item, str):
                raise TypeError("All media items must be strings.")
    return True