"""Database interactions."""

import sqlite3
import datetime


class DatabaseManager:
    """A sqlite database object.
    
    Notes
    -----
    Idea taken from here:  
    https://stackoverflow.com/questions/4610791/can-i-put-my-sqlite-connection-and-cursor-in-a-function
    """

    def __init__(self, database_path):
        """Create a sqlite database object.
        
        Parameters
        ----------
        database_path : str
            The path to the database file
        """
        self.conn = sqlite3.connect(database_path)
        self.cur = self.conn.cursor()

    def _create_tables(self):
        """Create subreddit_playlists and subreddit_playlist_videos tables."""
        self.cur.execute(
            """CREATE TABLE subreddit_playlists (
                playlist_id text primary key,
                date_created datetime,
                subreddit_name text
            )"""
        )

        self.cur.execute(
            """CREATE TABLE subreddit_playlist_videos (
                video_id text primary key,
                date_added datetime,
                playlist_id text,
                reddit_post_url text
            )"""
        )

        self.cur.execute(
            """CREATE TABLE subreddit_playlists_created (
                subreddit_name text,
                date_added datetime
            )"""
        )

        self.conn.commit()

    def _delete_tables(self):
        """Delete subreddit_playlists and subreddit_playlist_videos tables."""
        self.cur.execute("DROP TABLE IF EXISTS subreddit_playlists")
        self.cur.execute("DROP TABLE IF EXISTS subreddit_playlist_videos")
        self.cur.execute("DROP TABLE IF EXISTS subreddit_playlists_created")
        self.conn.commit()

    def _reset_database(self):
        """Delete and recreate tables."""
        self._delete_tables()
        self._create_tables()

    def query(self, sql, parameters=None):
        """Perform a query on the database.
        
        Parameters
        ----------
        sql : str
            A SQL query
            
        parameters : Iterable
            A list of parameters to insert (defaults to None)
        
        Returns
        -------
        None
        """
        if parameters is None:
            self.cur.execute(sql)
        else:
            self.cur.execute(sql, parameters)
        self.conn.commit()
        return self.cur

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
            VALUES (?, ?)
            """,
            (subreddit_name, datetime.datetime.now())
        )

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
            VALUES (?, ?, ?)
            """,
            (playlist_id, datetime.datetime.now(), subreddit_name)
        )

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
            WHERE subreddit_name = ? AND DATE(date_created) = ?
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
            VALUES (?, ?, ?, ?)
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
