class CityDataService:
    def __init__(
        self,
        http_client,
        google_api_key,
        geocoding_api_url,
        logger
    ):
        self.http_client = http_client
        self.google_api_key = google_api_key
        self.geocoding_api_url = geocoding_api_url
        self.logger = logger

    def fetch_city_data(self, city_name: str) -> dict:
        response = self.http_client.get(
            self.geocoding_api_url,
            params={
                "address": city_name,
                "key": self.google_api_key
            }
        )

        try:
            city_data = response.json()
        except ValueError as e:
            self.logger.log('error', f'Fetching city data failed: {e}')
            return f"Error parsing JSON: {e}"

        return city_data.get('results')
