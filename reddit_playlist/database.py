"""Database interactions."""
import os
import psycopg2
from psycopg2.extras import DictCursor
import urllib.parse
import datetime
import logging


# Set up logging
logger = logging.getLogger(__name__)


class DatabaseManager:
    """A sqlite database object.
    
    Notes
    -----
    Idea taken from here:  
    https://stackoverflow.com/questions/4610791/can-i-put-my-sqlite-connection-and-cursor-in-a-function
    """

    def __init__(self):
        """Create a Postgres database object."""
        self.conn = self._get_db()
        self.cur = self.conn.cursor()
        self.dict_cur = self.conn.cursor(cursor_factory=DictCursor)
        logger.info("Connected to Postgres database!")

    def __del__(self):
        """Close the database connection when the object is deleted."""
        self.conn.close()

    @staticmethod
    def _get_db():
        urllib.parse.uses_netloc.append("postgres")
        url = urllib.parse.urlparse(os.environ["DATABASE_URL"])

        conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )

        return conn

    def _create_tables(self):
        """Create subreddit_playlists and subreddit_playlist_videos tables."""
        self.cur.execute(
            """CREATE TABLE subreddit_playlists (
                playlist_id TEXT PRIMARY KEY,
                date_created TIMESTAMP,
                subreddit_name TEXT
            )"""
        )

        self.cur.execute(
            """CREATE TABLE subreddit_playlist_videos (
                video_id TEXT PRIMARY KEY,
                date_added TIMESTAMP,
                playlist_id TEXT,
                reddit_post_url TEXT
            )"""
        )

        self.cur.execute(
            """CREATE TABLE subreddit_playlists_created (
                subreddit_name TEXT,
                date_added TIMESTAMP
            )"""
        )

        self.conn.commit()

        logger.info("Created tables!")

    def _delete_tables(self):
        """Delete subreddit_playlists and subreddit_playlist_videos tables."""
        self.cur.execute("DROP TABLE IF EXISTS subreddit_playlists")
        self.cur.execute("DROP TABLE IF EXISTS subreddit_playlist_videos")
        self.cur.execute("DROP TABLE IF EXISTS subreddit_playlists_created")
        self.conn.commit()
        logger.info("Deleted tables!")

    def _reset_database(self):
        """Delete and recreate tables."""
        self._delete_tables()
        self._create_tables()

    def query(self, sql, parameters=None, dict_results=False):
        """Perform a query on the database.

        Parameters
        ----------
        sql : str
            A SQL query
        parameters : Iterable
            A list of parameters to insert (defaults to None)
        dict_results : bool
            Return the results as a dictionary or not (defaults to False)

        Returns
        -------
        None
        """
        if dict_results:
            cursor = self.dict_cur
        else:
            cursor = self.cur

        if parameters is None:
            cursor.execute(sql)
        else:
            cursor.execute(sql, parameters)
        self.conn.commit()

        logger.debug("Executed query\n{}\nwith parameters\n{}".format(sql, parameters))
        return cursor

    def __del__(self):
        """Close the database connection when the object is deleted."""
        self.conn.close()

    def add_subreddit_to_db(self, subreddit_name):
        """Add a subreddit to the list of subreddits in the db

        Parameters
        ----------
        subreddit_name : str
            The subreddit to be added

        Returns
        -------
        None
        """
        self.query(
            """
            INSERT INTO subreddit_playlists_created (subreddit_name, date_added)
            VALUES (%s, %s)
            """,
            (subreddit_name, datetime.datetime.now())
        )
        logger.info("Added subreddit {} to the database!".format(subreddit_name))

        return None

    def insert_playlist(self, playlist_id, subreddit_name):
        """Insert a created playlist into the subreddit_playlists table.
        
        Parameters
        ----------
        playlist_id : str
            The YouTube id for the playlist
        subreddit_name : str
            The name of the subreddit
        
        Returns
        -------
        None
        """
        self.query(
            """
            INSERT INTO subreddit_playlists(playlist_id, date_created, subreddit_name)
            VALUES (%s, %s, %s)
            """,
            (playlist_id, datetime.datetime.now(), subreddit_name)
        )
        logger.info("Added playlist {} for subreddit {} to database".format(playlist_id, subreddit_name))

    def get_playlist_id(self, subreddit_name, date=datetime.datetime.now().date()):
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
        response = self.query(
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

    def insert_video(self, video_id, playlist_id, reddit_post_url):
        """Insert a playlist video into the subreddit_playlist_videos table.
        
        Parameters
        ----------
        video_id : str
            The YouTube video id
        playlist_id : str
            The YouTube playlist id
        reddit_post_url : str
            The reddit post url

        Returns
        -------
        None
        """
        self.query(
            """INSERT INTO subreddit_playlist_videos(video_id, date_added, playlist_id, reddit_post_url)
            VALUES (%s, %s, %s, %s)
            """,
            (video_id, datetime.datetime.now(), playlist_id, reddit_post_url)
        )

    def get_all_playlist_ids(self):
        """Get all of the playlist ids."""
        response = self.query(
            """SELECT playlist_id
            FROM subreddit_playlists
            """
        ).fetchall()

        playlist_ids = [playlist_id[0] for playlist_id in response]

        return playlist_ids
