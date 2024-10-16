import requests
from datetime import datetime,timedelta

class APIRequests:
    def __init__(self):
        self.access_key_AS = "c8af5305b9d8d3367e336086e9835e0a"
        self.access_key_visualcrossing='RERF7RY267CY5754N8W2VZVKT'
        # Token et En-têtes pour API LHOpenAPI
        self.client_id = 'kmcdkm9jsmhrpt4upa7t6tpzb'
        self.client_secret = 'CwUc62danJ'
        self.acces_token_LH = self.get_access_token_LH()
        self.headers_LH = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.acces_token_LH}",
            "X-Originating-IP": "91.205.106.197"
        }

    def get_access_token_LH(self):

        url = "https://api.lufthansa.com/v1/oauth/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        response = requests.post(url, headers=headers, data=data)

        if response.status_code == 200:
            token_info = response.json()
            self.access_token = token_info['access_token']
            print("Nouveau token obtenu :", self.access_token)
            return self.access_token
        else:
            print("Erreur lors de l'obtention du token :", response.json())
       

    def get_flights_list_LH(self, departure_airport, arrival_airport, flight_date):
        api_url_LH = f"https://api.lufthansa.com/v1/operations/customerflightinformation/route/{departure_airport}/{arrival_airport}/{flight_date}"
        response = requests.get(api_url_LH, headers=self.headers_LH)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None

    def get_flight_infos_AS(self, flight_iata):
        api_url_AS = f"https://api.aviationstack.com/v1/flights?access_key={self.access_key_AS}&flight_iata={flight_iata}"
        response = requests.get(api_url_AS)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None

    def get_airport_LH(self, airport_iata):
        api_url_LH = f"https://api.lufthansa.com/v1/mds-references/airports/{airport_iata}?offset=0&LHoperated=0"
        response = requests.get(api_url_LH, headers=self.headers_LH)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None

    
    def get_flights_departure_before_yesterday(self):# souscription payante

        flight_date=(datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')# date au format YYYY-MM-DD
        api_url = f"https://api.aviationstack.com/v1/flights?access_key={self.access_key_AS}&flight_date={flight_date}"
        response = requests.get(api_url)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None

    def get_flights_landed(self):
        status='landed'
        api_url_AS = f"https://api.aviationstack.com/v1/flights?access_key={self.access_key_AS}&flight_status={status}"
        print(api_url_AS)
        response = requests.get(api_url_AS)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None            

    def get_meteo(self,latitude,longitude,dateheure):

        dateheure = datetime.fromisoformat(dateheure).strftime("%Y-%m-%dT%H:%M:%S")

        api_url=f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{latitude},{longitude}/{dateheure}?key={self.access_key_visualcrossing}&include=current"
        response = requests.get(api_url)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None 