from pymongo import MongoClient
from datetime import datetime
from api_requests import APIRequests 
from functions import FlightProcessor, FlightDataError # Importer les classes FlightProcessor et FlightDataError

# Connexion à MongoDB
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.app_data

api_requests = APIRequests() 
flightprocessor = FlightProcessor() # Créer une instance de la classe FlightProcessor

def today_america_flights_append():
	#Requête API pour récupérer les vols landed (aviationstack) => à exécuter tous les jours ; il faudra peut-être faire un distinct
	flight_info = api_requests.get_flights_landed()

	#Filtrer les vols avec un départ et une arrivée en Europe
	if flight_info and 'data' in flight_info:
		america_flights = [
		flight for flight in flight_info['data']
		if flight.get('departure', {}).get('timezone') and flight.get('arrival', {}).get('timezone') and
		flight['departure']['timezone'].startswith('Australia') and 
		flight['arrival']['timezone'].startswith('Australia')
		]

		if america_flights:
			try:
				america_flights_processed = flightprocessor.process_flight_AS_list(america_flights)
				db.america_flights_today.insert_many(america_flights_processed)
				message = f"{len(america_flights_processed)} résultats de vols insérés dans la base de données."
				print(message)

				#Ajout des vols du jour à la collection globale
				flights_today = list(db.america_flights_today.find({}, {"_id": 0}))
				if flights_today:
					result = db.america_flights.insert_many(flights_today)
					return {"Documents ajoutés" : len(result.inserted_ids)}
				else:
					return {"error": "Aucun document à ajouter."}, 404
				
			except FlightDataError as e:
				return {"error": e.args[0], "details": e.details}, 400
		else:
			return {"error": "Aucun vol trouvé en Amerique.", "details": america_flights}, 404
	else:
		return {"error": "Aucun vol trouvé ou problème API AS", "details": flight_info}


today_america_flights_append()
