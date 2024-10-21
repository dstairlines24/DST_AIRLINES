import requests
from datetime import datetime

class APIRequests:
    def __init__(self):
        self.access_key_AS = "b856567c8b3e0d2e69a0f107f656c213"
        self.access_key_visualcrossing = 'W9NSD6SUADPMWHHEAZWSE5E9W'
        self.client_id = '22642rjuu7z74utsdajwa8b9t'
        self.client_secret = 'U57JwBbEKJ'
        self.acces_token_LH = self.get_access_token_LH()
        self.headers_LH = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.acces_token_LH}"
        }

    # Récupération du token d'accès pour l'API Lufthansa
    def get_access_token_LH(self):
        url = "https://api.lufthansa.com/v1/oauth/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json().get('access_token')
        else:
            raise Exception(f"Erreur lors de l'obtention du token : {response.json()}")

    # Récupération des informations de vols Lufthansa
    def get_flights_list_LH(self, departure_airport, arrival_airport, flight_date):
        api_url_LH = f"https://api.lufthansa.com/v1/operations/customerflightinformation/route/{departure_airport}/{arrival_airport}/{flight_date}"
        response = requests.get(api_url_LH, headers=self.headers_LH)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Erreur lors de la requête API LH : {response.json()}")

    # Récupération des informations sur un vol via AviationStack
    def get_flight_infos_AS(self, flight_iata):
        api_url_AS = f"https://api.aviationstack.com/v1/flights?access_key={self.access_key_AS}&flight_iata={flight_iata}"
        response = requests.get(api_url_AS)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Erreur lors de la requête API AS : {response.json()}")

    # Récupération des informations d'un aéroport via Lufthansa
    def get_airport_LH(self, airport_iata):
        api_url_LH = f"https://api.lufthansa.com/v1/mds-references/airports/{airport_iata}?offset=0&LHoperated=0"
        response = requests.get(api_url_LH, headers=self.headers_LH)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Erreur lors de la requête API LH airport : {response.json()}")

    # Récupération des vols "landed" via AviationStack
    def get_flights_landed(self):
        api_url_AS = f"https://api.aviationstack.com/v1/flights?access_key={self.access_key_AS}&flight_status=landed"
        response = requests.get(api_url_AS)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Erreur lors de la requête API AS landed : {response.json()}")

    # Récupération des données météorologiques
    def get_meteo(self, latitude, longitude, dateheure):
        dateheure = datetime.fromisoformat(dateheure).strftime("%Y-%m-%dT%H:%M:%S")
        api_url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{latitude},{longitude}/{dateheure}?key={self.access_key_visualcrossing}&include=current&unitGroup=metric"
        response = requests.get(api_url)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Erreur lors de la requête API Visualcrossing : {response.json()}")
