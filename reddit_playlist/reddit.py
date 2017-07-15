"""Reddit API calls."""
import requests
import requests.auth
import logging

# Set up logging
logger = logging.getLogger(__name__)


def get_top_subreddit_posts(subreddit, sort_by='hot', limit=50):
    """Get the top posts from a specified subreddit.
    
    Parameters
    ----------
    subreddit : str
        The name of the subreddit
    sort_by : str
        How to sort the subreddit, defaults to 'hot'
    limit : int
        How many top posts to get, defaults to 50
    
    Returns
    -------
    list of dict
        A list of dictionaries of posts
    """
    headers = {
        "User-Agent": "PostGetter/0.1 by brandonmburroughs"
    }

    url = "https://www.reddit.com/r/{}/{}/.json?limit={}".format(subreddit, sort_by, limit - 2)

    response = requests.get(url, headers=headers)
    logger.info("Response {} from {}".format(response.status_code, url))

    if response.ok:
        posts = [post['data'] for post in response.json()['data']['children']]
    else:
        error_message = "Expected status code 200, but got status code {}\n{}".format(
            response.status_code,
            response.text
        )
        logger.error(error_message)
        raise requests.ConnectionError(error_message)

    return posts


def get_youtube_video_id_from_url(video_url):
    """Get the youtube video id from a url.
    
    Parameters
    ----------
    video_url : str
        A YouTube video url
    
    Returns
    -------
    str
        The video id
    """
    if video_url.find("?v=") >= 0:
        video_id = video_url.split("?v=")[1].split("&")[0]
    elif video_url.find("youtu.be") >= 0:
        video_id = video_url.split("youtu.be/")[1]
    else:
        raise Exception("Video id could not be found in {}!".format(video_url))

    return video_id

def filter_youtube_videos(posts):
    """Filter the list of posts to only contain YouTube videos.
    
    Parameters
    ----------
    posts : list of dict
        A list of post dictionaries
    
    Returns
    -------
    list of dict
        A list of post dictionaries that contain youtube URLs
    """
    youtube_bases = ['youtube.com', 'youtu.be']

    youtube_posts = []
    for post in posts:
        if any([base in post["url"] for base in youtube_bases]) and "playlist" not in post["url"]:
            post["video_id"] = get_youtube_video_id_from_url(post["url"])
            youtube_posts.append(post)
            logger.debug("Youtube Post: {}".format(post["url"]))
        else:
            logger.debug("NOT Youtube Post: {}".format(post["url"]))

    return youtube_posts
