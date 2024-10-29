from pymongo import MongoClient

# Ajouter le chemin du dossier parent pour pouvoir accéder à functions
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from functions.functions import FlightProcessor

# Connexion à MongoDB
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.app_data

flightprocessor = FlightProcessor() # Créer une instance de la classe FlightProcessor

def today_europe_flights_append():
	   # Requête API pour récupérer les vols "landed" (aviationstack)
    flight_info = flightprocessor.get_flights_landed()

    # Filtrer les vols avec un départ et une arrivée en Europe
    if flight_info and 'data' in flight_info:
        europe_flights = [
            flight for flight in flight_info['data']
            if flight.get('departure', {}).get('timezone') and flight.get('arrival', {}).get('timezone') and
               flight['departure']['timezone'].startswith('Europe') and flight['arrival']['timezone'].startswith('Europe')
        ]

        if europe_flights:
            # Traiter la liste des vols et insérer dans la collection MongoDB
            result = flightprocessor.process_flight_AS_list(europe_flights, db.europe_flights)

            # Résumé des opérations
            print(f"{result['vols traités']} vols traités et insérés dans la base de données.")
            if result["vols échoués"]:
                print(f"{result['vols échoués']} vols ont échoué et n'ont pas été insérés.")

            return result
        else:
            return {"error": "Aucun vol trouvé en Europe.", "details": europe_flights}, 404
    else:
        return {"error": "Aucun vol trouvé ou problème API AS", "details": flight_info}


today_europe_flights_append()
