from pymongo import MongoClient
from datetime import datetime
from api_requests import APIRequests 
from functions import FlightProcessor, FlightDataError # Importer les classes FlightProcessor et FlightDataError

# Connexion à MongoDB
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.app_data

api_requests = APIRequests() 
flightprocessor = FlightProcessor() # Créer une instance de la classe FlightProcessor

def today_australia_flights_append():
	# Requête API pour récupérer les vols landed (aviationstack) => à exécuter tous les jours
	flight_info = api_requests.get_flights_landed()

	# Filtrer les vols avec un départ et une arrivée en Australie
	if flight_info and 'data' in flight_info:
		australia_flights = [
		flight for flight in flight_info['data']
		if flight.get('departure', {}).get('timezone') and flight.get('arrival', {}).get('timezone') and
		flight['departure']['timezone'].startswith('Australia') and 
		flight['arrival']['timezone'].startswith('Australia')
		]

		if australia_flights:
			try:
				# Traiter les données des vols
				australia_flights_processed = flightprocessor.process_flight_AS_list(australia_flights)
				
				# Insertion des vols directement dans la collection "australia_flight"
				result = db.australia_flight.insert_many(australia_flights_processed)
				message = f"{len(australia_flights_processed)} résultats de vols insérés dans la base de données."
				print(message)

				return {"Documents ajoutés" : len(result.inserted_ids)}

			except FlightDataError as e:
				return {"error": e.args[0], "details": e.details}, 400
		else:
			return {"error": "Aucun vol trouvé en Australie.", "details": australia_flights}, 404
	else:
		return {"error": "Aucun vol trouvé ou problème API AS", "details": flight_info}

# Exécuter la fonction
today_australia_flights_append()