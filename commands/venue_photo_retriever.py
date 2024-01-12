import os
import requests
from typing import Optional


class VenuePhotoRetriever:
    PHOTO_SIZE = '300x300'
    BASE_URL = 'https://api.foursquare.com/v3/places'
    
    def __init__(self, client_id: str, client_secret: str, foursquare_auth_key: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.foursquare_auth_key = foursquare_auth_key
    
    def get_venue_photos(self, venue_id: str) -> Optional[str]:
        response = self._make_request(venue_id)
        
        if response and response.status_code == 200:
            return self._extract_photo_url(response.json())
        return None
    
    def _make_request(self, venue_id: str) -> requests.Response:
        url = f"{self.BASE_URL}/{venue_id}/photos"
        
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        headers = {
            "accept": "application/json",
            "Authorization": self.foursquare_auth_key
        }
        
        try:
            return requests.get(url, params=params, headers=headers)
        except requests.exceptions.RequestException as e:
            print(f'An error occurred: {e}')
            return None
    
    def _extract_photo_url(self, photos):
        if photos:
            first_photo = photos[0]
            return f"{first_photo.get('prefix')}{self.PHOTO_SIZE}{first_photo.get('suffix')}"
        return None
            
