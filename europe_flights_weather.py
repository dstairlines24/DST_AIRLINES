from pymongo import MongoClient
from flask import jsonify
from datetime import datetime
from api_requests import APIRequests 
from functions import FlightProcessor, FlightDataError # Importer les classes FlightProcessor et FlightDataError

# Connexion à MongoDB
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.app_data

api_requests = APIRequests() 
flightprocessor = FlightProcessor() # Créer une instance de la classe FlightProcessor

def today_europe_flights_append():
	#Requête API pour récupérer les vols landed (aviationstack) => à exécuter tous les jours ; il faudra peut-être faire un distinct
	flight_info = api_requests.get_flights_landed()
	db.europe_flights_today.drop()

	#Filtrer les vols avec un départ et une arrivée en Europe
	if flight_info and 'data' in flight_info:
		europe_flights = [
		flight for flight in flight_info['data']
		if flight.get('departure', {}).get('timezone') and flight.get('arrival', {}).get('timezone') and
		flight['departure']['timezone'].startswith('Europe') and 
		flight['arrival']['timezone'].startswith('Europe')
		]

		if europe_flights:
			try:
				europe_flights_processed = flightprocessor.process_flight_AS_list(europe_flights)
				db.europe_flights_today.insert_many(europe_flights_processed)
				message = f"{len(europe_flights_processed)} résultats de vols insérés dans la base de données."
				print(message)

				#Ajout des vols du jour à la collection globale
				flights_today = list(db.europe_flights_today.find({}, {"_id": 0}))
				if flights_today:
					result = db.europe_flights.insert_many(flights_today)
					return jsonify({"Documents ajoutés" : len(result.inserted_ids)})
				else:
					return jsonify({"error": "Aucun document à ajouter."}), 404
				
			except FlightDataError as e:
				return jsonify({"error": e.args[0], "details": e.details}), 400
		else:
			return jsonify({"error": "Aucun vol trouvé en Europe.", "details": europe_flights}), 404
	else:
		return jsonify({"error": "Aucun vol trouvé ou problème API AS", "details": flight_info})


today_europe_flights_append()
