import requests

class APIRequests:
    def __init__(self):
        # Token et En-têtes pour API LHOpenAPI
        self.acces_token = 'ce4465a83ws4nmdr3yx2xkt2'
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.acces_token}",
            "X-Originating-IP": "91.205.106.197"
        }

    def get_flight_information(self, departure_airport, arrival_airport, flight_date):
        api_url = f"https://api.lufthansa.com/v1/operations/customerflightinformation/route/{departure_airport}/{arrival_airport}/{flight_date}"
        response = requests.get(api_url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
