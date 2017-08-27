"""YouTube API interactions."""
import os
import datetime
import logging
import sys

from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow
from httplib2 import Http
from apiclient.discovery import build

from reddit_playlist import database


# Set up logging
logger = logging.getLogger(__name__)


class YouTube:
    """
    YouTube interaction API wrapper.  This class will handle all of the YouTube API interactions.
    """
    def __init__(self, client_secrets_file):
        """Initialize the YouTube interaction API wrapper
        
        Parameters
        ----------
        client_secrets_file : str
            The path to the YouTube JSON credentials file
        """
        self.client_secrets_file = client_secrets_file
        self._create_secrets_file(client_secrets_file)
        self.youtube_scope = 'https://www.googleapis.com/auth/youtube'
        self.youtube_api_service_name = "youtube"
        self.youtube_api_version = "v3"
        self.youtube = None
        self.database = database.DatabaseManager()

    def _create_secrets_file(self, client_secrets_file):
        """Create a secrets file from the environment variables since the flow needs one.
        
        Parameters
        ----------
        client_secrets_file : str
            The path to the credentials file
        """
        if not os.path.exists("resources"):
            os.makedirs("resources")
        with open(client_secrets_file, "w") as f:
            f.write(os.environ["CLIENT_SECRET"])

    def _create_token_file(self):
        """Create a token file for YouTube."""
        path, python_file = sys.argv[0].rsplit("/", 1)
        if not os.path.exists("{}/resources".format(path)):
            os.makedirs("{}/resources".format(path))
        with open("{}/resources/{}-oauth2.json".format(path, python_file), "w") as f:
            f.write(os.environ["YOUTUBE_TOKEN"])

    def get_authenticated_service(self):
        """Authenticate with YouTube"""
        self._create_token_file()
        flow = flow_from_clientsecrets(self.client_secrets_file, scope=self.youtube_scope)

        path, python_file = sys.argv[0].rsplit("/", 1)
        storage = Storage("{}/resources/{}-oauth2.json".format(path, python_file))
        credentials = storage.get()

        if credentials is None or credentials.invalid:
            flags = argparser.parse_args()
            credentials = run_flow(flow, storage, flags)

        self.youtube = build(self.youtube_api_service_name, self.youtube_api_version,
                             http=credentials.authorize(Http()), cache_discovery=False)

    @staticmethod
    def _build_resource(properties):
        """Build a resource object based upon properties given as key-value pairs. This allows the
        user to submit YouTube properties with periods in the name (e.g. snippet.title).  This
        method will handle splitting these out without explicit input from the user.
        
        Parameters
        ----------
        properties : dict
            A dictionary of key-value properties.
            
        Note
        ----
        This idea was taken from the YouTube API develop docs.
        https://developers.google.com/youtube/v3/docs/
        """
        resource = {}
        for prop_key, prop_value in properties.items():
            current_level = resource
            prop_key_array = prop_key.split(".")
            for i, prop_key_piece in enumerate(prop_key_array):
                if i == (len(prop_key_array) - 1):
                    current_level[prop_key_piece] = prop_value
                else:
                    if prop_key_piece not in current_level:
                        current_level[prop_key_piece] = {}
                    current_level = current_level[prop_key_piece]

        return resource

    def create_playlist(self, subreddit, date=datetime.datetime.now().date()):
        """Create a YouTube playlist.
        
        Parameters
        ----------
        subreddit : str
            Subreddit name
        date : str or datetime object
            The date of the playlist
        
        Returns
        -------
        str
            The playlist id
        """
        playlist_resource = self._build_resource(
            {
                "snippet.title": "{} playlist for {}".format(subreddit, date),
                "snippet.description": "{} playlist for {}".format(subreddit, date),
                "status.privacyStatus": "public"
            }
        )
        playlists_insert_response = self.youtube.playlists().insert(
            part="snippet,status",
            body=playlist_resource
        ).execute()

        self.database.add_subreddit_to_db(subreddit)
        self.database.insert_playlist(playlists_insert_response["id"], subreddit)
    
        logger.info("Created new playlist with id: %s" %
                    playlists_insert_response["id"])
    
        return playlists_insert_response["id"]

    def add_video_to_playlist(self, video_id, playlist_id, reddit_post_url):
        """Add a single video an existing playlist.
        
        Parameters
        ----------
        video_id : str
            The id for a YouTube video
        playlist_id : str
            The id for a YouTube playlist
            
        Returns
        -------
        None
        """
        try:
            playlist_item = self._build_resource(
                {
                    'snippet.playlistId': playlist_id,
                    'snippet.resourceId.kind': 'youtube#video',
                    'snippet.resourceId.videoId': video_id,
                    'snippet.position': 0
                }
            )
            self.youtube.playlistItems().insert(
                part="snippet",
                body=playlist_item
            ).execute()

            self.database.insert_video(video_id, playlist_id, reddit_post_url)
            logger.info("Added video {} to playlist {}".format(video_id, playlist_id))
        except:
            logging.warning("Skipping video {}".format(video_id))
    
        return None
    
    def get_playlist_id_for_today(self, subreddit, date=datetime.datetime.now().date()):
        """Get the playlist id for today's playlist.
    
        Parameters
        ----------
        subreddit : str
            Subreddit name
        date : date object
            The date to search for, defaults to today
    
        Returns
        -------
        None
        """
        playlist_ids = self.youtube.playlists().list(
            part="snippet",
            mine=True
        ).execute()
    
        for playlist in playlist_ids['items']:
            if str(date) in playlist['snippet']['title'] and \
                    subreddit in playlist['snippet']['title']:
                return playlist['id']

        return None

    def bulk_add_videos_to_playlist(self, video_id_list, playlist_id):
        """Add several videos to a playlist.
    
        Parameters
        ----------
        video_id_list : list of str
            A list of video ids to add
        playlist_id : str
            The id for a YouTube playlist
        
        Returns
        -------
        None
        """
        # Get current video id list
        response = self.youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50
        ).execute()
    
        current_video_ids = []
        for video in response['items']:
            current_video_ids.append(video['snippet']['resourceId']['videoId'])
    
        for new_video_id in video_id_list:
            if new_video_id not in current_video_ids:
                self.add_video_to_playlist(video_id=new_video_id,
                                           playlist_id=playlist_id,
                                           reddit_post_url="test")
            else:
                logger.info("Skipping video {0} in playlist {1}".format(
                    new_video_id,
                    playlist_id
                ))
    
        return None

    @staticmethod
    def get_playlist_url(playlist_id):
        """Return a playlist url given a playlist id.
        
        Parameters
        ----------
        playlist_id : str
        
        Returns
        -------
        str
            A playlist url
        """
        return "https://www.youtube.com/playlist?list={}".format(playlist_id)

    def _delete_playlist(self, playlist_id):
        """Delete a given playlist.
        
        Parameters
        ----------
        playlist_id : str
            A YouTube playlist id

        Returns
        -------
        None
        """
        self.youtube.playlists().delete(id=playlist_id).execute()

        return None

    def _delete_all_playlists(self):
        """Delete all of the playlists in the database."""
        playlist_ids = self.database.get_all_playlist_ids()
        for playlist_id in playlist_ids:
            logger.info("Deleting playlist {}".format(playlist_id))
            self._delete_playlist(playlist_id)

        return None

if __name__ == "__main__":
    youtube = YouTube("resources/client_secret.json")
    youtube.get_authenticated_service()

    playlist_id = youtube.create_playlist(subreddit="Test")

    youtube.add_video_to_playlist(video_id="qsMxUp82YeA",
                                  playlist_id=playlist_id,
                                  reddit_post_url="test")
