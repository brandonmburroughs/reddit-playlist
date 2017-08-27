import datetime
import logging
import argparse
from flask import Flask, g, request, flash, render_template, redirect, url_for

from reddit_playlist import database
from reddit_playlist import reddit
from reddit_playlist import youtube

# Set up logging
logger = logging.getLogger(__name__)


# Set up app
app = Flask(__name__)
app.secret_key = 'some secret'


def get_playlist_id(subreddit_name, date=datetime.datetime.now().date()):
    """Get the playlist for a particular subreddit and date.

    Parameters
    ----------
    subreddit_name : str
        The name of the subreddit
    date : datetime.date
        A datetime date object (defaults to today)

    Returns
    -------
    str
        playlist_id
    """
    db = database.DatabaseManager()
    response = db.query(
        """
        SELECT playlist_id
        FROM subreddit_playlists
        WHERE subreddit_name = %s AND DATE(date_created) = %s
        """,
        (subreddit_name, date)
    ).fetchall()

    if len(response) > 0:
        return response[0][0]
    else:
        return None


def create_and_or_update_playlist(subreddit_name):
    """Create and/or update subreddit playlist
    
    Parameters
    ----------
    subreddit_name : str
        The subreddit name to create or update a playlist for

    Returns
    -------
    None
    """
    # Get posts from given subreddit
    try:
        posts = reddit.get_top_subreddit_posts(subreddit_name)
    except Exception:
        return None
    youtube_posts = reddit.filter_youtube_videos(posts)
    video_id_list = [post['video_id'] for post in youtube_posts]

    # Connect to YouTube, get or create playlist, and add videos
    youtube_conn = youtube.YouTube("resources/client_secret.json")
    youtube_conn.get_authenticated_service()
    playlist_id = get_playlist_id(subreddit_name)
    if playlist_id is None:
        playlist_id = youtube_conn.create_playlist(subreddit_name)
    youtube_conn.bulk_add_videos_to_playlist(video_id_list, playlist_id)

    return None


def get_subreddits_available_in_db():
    """Get all of the subreddit names that are in the database."""
    db = database.DatabaseManager()
    response = db.query(
        """
        SELECT subreddit_name
        FROM subreddit_playlists_created
        ORDER BY subreddit_name ASC
        """
    ).fetchall()

    subreddit_names = [subreddit_name[0] for subreddit_name in response]

    return subreddit_names


def bulk_create_and_or_update_playlists():
    """Get all subreddits and bulk update the playlists."""
    subreddit_names = get_subreddits_available_in_db()
    for subreddit_name in subreddit_names:
        logger.debug("Updating videos for {}!".format(subreddit_name))
        create_and_or_update_playlist(subreddit_name)


@app.route('/<string:subreddit_name>', methods=['GET'])
def subreddit_playlist(subreddit_name):
    return render_template("index.html", subreddit_name=subreddit_name,
                           subreddit_playlist_url=get_playlist_id(subreddit_name),
                           subreddits_available=get_subreddits_available_in_db())


@app.route('/add', methods=['POST'])
def add_subreddit():
    subreddit_name = request.form['subreddit_name']
    flash("%s was added to the list of subreddit playlists!".format(subreddit_name))
    create_and_or_update_playlist(subreddit_name)

    return redirect(url_for('subreddit_playlist', subreddit_name=subreddit_name))

@app.route('/')
def index():
    bulk_create_and_or_update_playlists()
    return "Hello, world!"


def parse_args():
    """Parse the CLI args"""
    parser = argparse.ArgumentParser(description='Update all of the playlists')
    parser.add_argument("--update-playlists", dest="update_playlist", default=False, action="store_true",
                        help="Update all of the playlists (default: False)")

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    if args.update_playlist:
        bulk_create_and_or_update_playlists()
    else:
        app.run(host="0.0.0.0")
