"""YouTube API interactions."""

import datetime
import logging
import sys

from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow
from httplib2 import Http
from apiclient.discovery import build


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
        self.youtube_scope = 'https://www.googleapis.com/auth/youtube'
        self.youtube_api_service_name = "youtube"
        self.youtube_api_version = "v3"
        self.youtube = None

    def get_authenticated_service(self):
        """Authenticate with YouTube"""
        flow = flow_from_clientsecrets(self.client_secrets_file, scope=self.youtube_scope)

        path, python_file = sys.argv[0].rsplit("/", 1)
        storage = Storage("{}/resources/{}-oauth2.json".format(path, python_file))
        credentials = storage.get()

        if credentials is None or credentials.invalid:
            flags = argparser.parse_args()
            credentials = run_flow(flow, storage, flags)

        self.youtube = build(self.youtube_api_service_name, self.youtube_api_version,
                             http=credentials.authorize(Http()))

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
    
        logger.info("Created new playlist with id: %s" %
                    playlists_insert_response["id"])
    
        return playlists_insert_response["id"]

    def add_video_to_playlist(self, video_id, playlist_id):
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
    
            logger.info("Added video {} to playlist {}".format(video_id, playlist_id))
        except:
            logging.warning("Skipping video {}".format(video_id))
    
        return None
    
    def get_playlist_id_for_today(self, subreddit):
        """Get the playlist id for today's playlist.
    
        Parameters
        ----------
        subreddit : str
            Subreddit name
    
        Returns
        -------
        None
        """
        playlist_ids = self.youtube.playlists().list(
            part="snippet",
            mine=True
        ).execute()
    
        for playlist in playlist_ids['items']:
            if str(datetime.datetime.now().date()) in playlist['snippet']['title'] and \
                    subreddit in playlist['snippet']['title']:
                return playlist['id']

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
                                           playlist_id=playlist_id)
            else:
                logger.info("Skipping video {0} in playlist {1}".format(
                    new_video_id,
                    playlist_id
                ))
    
        return None

if __name__ == "__main__":
    youtube = YouTube("resources/client_secret.json")
    youtube.get_authenticated_service()

    playlist_id = youtube.create_playlist(subreddit="Test")

    youtube.add_video_to_playlist(video_id="qsMxUp82YeA",
                                  playlist_id=playlist_id)
