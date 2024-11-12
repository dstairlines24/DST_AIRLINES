from pymongo import MongoClient

# Ajouter le chemin du dossier parent pour pouvoir accéder à functions
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from functions.functions import FlightProcessor

# Récupérer l'URI de MongoDB depuis la variable d'environnement
mongo_uri = os.getenv("MONGO_URI")

# Connexion à MongoDB
client = MongoClient(mongo_uri)
db = client.app_data

flightprocessor = FlightProcessor()

def today_america_flights_append():
    # Requête API pour récupérer les vols "landed" (aviationstack)
    flight_info = flightprocessor.get_flights_landed()

    # Filtrer les vols avec un départ et une arrivée en Asie
    if flight_info and 'data' in flight_info:
        america_flights = [
            flight for flight in flight_info['data']
            if flight.get('departure', {}).get('timezone') and flight.get('arrival', {}).get('timezone') and
               flight['departure']['timezone'].startswith('America') and flight['arrival']['timezone'].startswith('America')
        ]

        if america_flights:
            # Traiter la liste des vols et insérer dans la collection MongoDB
            result = flightprocessor.process_flight_AS_list(america_flights, db.america_flights)

            # Résumé des opérations
            print(f"{result['vols traités']} vols traités et insérés dans la base de données.")
            if result["vols échoués"]:
                print(f"{result['vols échoués']} vols ont échoué et n'ont pas été insérés.")

            return result
        else:
            return {"error": "Aucun vol trouvé en Asie.", "details": america_flights}, 404
    else:
        return {"error": "Aucun vol trouvé ou problème API AS", "details": flight_info}

today_america_flights_append()
