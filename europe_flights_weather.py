from pymongo import MongoClient
from datetime import datetime
from api_requests import APIRequests 

# Connexion à MongoDB
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.app_data

api_requests = APIRequests() 

#Requête API pour récupérer les vols landed (aviationstack) => à exécuter tous les jours ; il faudra peut-être faire un distinct
flight_info = api_requests.get_flights_landed()
#Filtrer les vols avec un départ et une arrivée en Europe

if flight_info and 'data' in flight_info:
	europe_flights = [
	flight for flight in flight_info['data']
	if flight.get('departure', {}).get('timezone') and flight.get('arrival', {}).get('timezone') and
	flight['departure']['timezone'].startswith('Europe') and 
	flight['arrival']['timezone'].startswith('Europe')
	]	

	db.europe_flights_today.drop()
	if europe_flights:
		#Insertion de la réponse dans MongoDB, dans la collection : "europe_flights_today"
		db.europe_flights_today.insert_many(europe_flights)
		message = f"{len(europe_flights)} résultats de vols insérés dans la collection europe_flights_today."
		print(message)

		# Mise à jour des données pour les vols du jour		
		for flight in db.europe_flights_today.find():
			airport_dep = api_requests.get_airport_LH(flight['departure']['iata'])
			airport_arr = api_requests.get_airport_LH(flight['arrival']['iata'])
			
			if airport_dep and airport_arr:
				# Recherche des Latitude, Longitude pour mettre à jour les conditions météo
				latitude=airport_dep['AirportResource']['Airports']['Airport']['Position']['Coordinate']['Latitude']
				longitude=airport_dep['AirportResource']['Airports']['Airport']['Position']['Coordinate']['Longitude']
				dateheure=flight['departure']['actual']
				meteo=api_requests.get_meteo(latitude,longitude,dateheure)

				# Mise à jour des données pour l'aéroport de départ		
				db.europe_flights_today.update_many(
					{ "departure.iata": flight['departure']['iata'] },
					{ 
						"$set": { 
							"departure.latitude": airport_dep['AirportResource']['Airports']['Airport']['Position']['Coordinate']['Latitude'], 
							"departure.longitude": airport_dep['AirportResource']['Airports']['Airport']['Position']['Coordinate']['Longitude'],
							"departure.temp":meteo['currentConditions']['temp'],
							"departure.humidity":meteo['currentConditions']['humidity'],
							"departure.precip":meteo['currentConditions']['precip'],
							"departure.snow":meteo['currentConditions']['snow'],
							"departure.snowdepth":meteo['currentConditions']['snowdepth'],
							"departure.windspeed":meteo['currentConditions']['windspeed'],
							"departure.pressure":meteo['currentConditions']['pressure'],
							"departure.visibility":meteo['currentConditions']['visibility'],
							"departure.cloudcover":meteo['currentConditions']['cloudcover'],
							"departure.conditions":meteo['currentConditions']['conditions'],
							"departure.icon":meteo['currentConditions']['icon']					
						} 
					}
				)
				
				# Mise à jour des données pour l'aéroport de départ	
				latitude=airport_arr['AirportResource']['Airports']['Airport']['Position']['Coordinate']['Latitude']
				longitude=airport_arr['AirportResource']['Airports']['Airport']['Position']['Coordinate']['Longitude']
				dateheure=flight['arrival']['actual']
				meteo=api_requests.get_meteo(latitude,longitude,dateheure)

				db.europe_flights_today.update_many(
					{ "arrival.iata": flight['arrival']['iata'] },
					{ 
						"$set": { 
							"arrival.latitude": airport_arr['AirportResource']['Airports']['Airport']['Position']['Coordinate']['Latitude'], 
							"arrival.longitude": airport_arr['AirportResource']['Airports']['Airport']['Position']['Coordinate']['Longitude'],
							"arrival.temp":meteo['currentConditions']['temp'],
							"arrival.humidity":meteo['currentConditions']['humidity'],
							"arrival.precip":meteo['currentConditions']['precip'],
							"arrival.snow":meteo['currentConditions']['snow'],
							"arrival.snowdepth":meteo['currentConditions']['snowdepth'],
							"arrival.windspeed":meteo['currentConditions']['windspeed'],
							"arrival.pressure":meteo['currentConditions']['pressure'],
							"arrival.visibility":meteo['currentConditions']['visibility'],
							"arrival.cloudcover":meteo['currentConditions']['cloudcover'],
							"arrival.conditions":meteo['currentConditions']['conditions'],
							"arrival.icon":meteo['currentConditions']['icon']						
						} 
					}
				)
				
		# Ajout des vols du jour à la collection globale
		flights_today = list(db.europe_flights_today.find())

		# Préparer une liste de nouveaux documents sans le champ _id pour ne pas générer de doublons d'identifiants avec la collection europe_flights
		new_flights = []
		for flight in flights_today:
			# Créer une copie du document sans le champ _id
			flight_copy = flight.copy()  # Copie le document
			flight_copy.pop('_id', None)  # Supprime le champ _id
			new_flights.append(flight_copy)

		# Insérer les nouveaux documents dans la collection db.europe_flights : de nvx identifiants seront générés automatiquement
		if new_flights:
			result = db.europe_flights.insert_many(new_flights)
			print(f"Documents ajoutés : {len(result.inserted_ids)}")
		else:
			print("Aucun document à ajouter.")
			