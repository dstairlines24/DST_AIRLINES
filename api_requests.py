import requests

class APIRequests:
    def __init__(self):
        self.access_key_AS = "e292961c46cccfb991e67890429bc71b"
        # Token et En-têtes pour API LHOpenAPI
        self.acces_token_LH = 'hgw9bcg7a86qhdtkrp88em2p'
        self.headers_LH = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.acces_token_LH}",
            "X-Originating-IP": "91.205.106.197"
        }

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

    

