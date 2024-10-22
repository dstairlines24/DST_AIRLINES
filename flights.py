from pymongo import MongoClient
from datetime import datetime
from api_requests import APIRequests 
from functions import FlightProcessor, FlightDataError

# Connexion à MongoDB
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.app_data

api_requests = APIRequests() 
flightprocessor = FlightProcessor()

def today_all_flights_append():
    flight_info = api_requests.get_flights_landed()

    if flight_info and 'data' in flight_info:
        all_flights = flight_info['data']

        if all_flights:
            try:
                all_flights_processed = flightprocessor.process_flight_AS_list(all_flights)

                # Insertion des vols dans MongoDB
                result = db.all_flight.insert_many(all_flights_processed)
                message = f"{len(all_flights_processed)} résultats de vols insérés dans la base de données."
                print(message)

                return {"Documents ajoutés": len(result.inserted_ids)}

            except FlightDataError as e:
                return {"error": e.args[0], "details": e.details}, 400
        else:
            return {"error": "Aucun vol trouvé.", "details": all_flights}, 404
    else:
        return {"error": "Aucun vol trouvé ou problème API AS", "details": flight_info}

today_all_flights_append()
