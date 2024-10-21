from pymongo import MongoClient
from datetime import datetime
from api_requests import APIRequests 
from functions import FlightProcessor, FlightDataError # Importer les classes FlightProcessor et FlightDataError

# Connexion à MongoDB
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.app_data

flightprocessor = FlightProcessor() # Créer une instance de la classe FlightProcessor

def today_europe_flights_append():
	#Requête API pour récupérer les vols landed (aviationstack) => à exécuter tous les jours
	flight_info = flightprocessor.get_flights_landed()

	#Filtrer les vols avec un départ et une arrivée en Europe
	if flight_info and 'data' in flight_info:
		europe_flights = [
		flight for flight in flight_info['data']
		if flight.get('departure', {}).get('timezone') and flight.get('arrival', {}).get('timezone') and flight['departure']['timezone'].startswith('Europe') and 
		flight['arrival']['timezone'].startswith('Europe')
		]

		if europe_flights:
			try:
				europe_flights_processed = flightprocessor.process_flight_AS_list(europe_flights)
				message = f"{len(europe_flights_processed)} vols complétés avec les infos météo sur le trajet."
				print(message)

				#Ajout des vols du jour à la collection globale
				result = db.europe_flights.insert_many(europe_flights_processed)
				if result:
					print(f"Documents ajoutés : {len(result.inserted_ids)}")
					return {"Documents ajoutés" : len(result.inserted_ids)}
				else:
					return {"error": "Aucun document à ajouter."}, 404
				
			except FlightDataError as e:
				return {"error": e.args[0], "details": e.details}, 400
		else:
			return {"error": "Aucun vol trouvé en Europe.", "details": europe_flights}, 404
	else:
		return {"error": "Aucun vol trouvé ou problème API AS", "details": flight_info}


today_europe_flights_append()
