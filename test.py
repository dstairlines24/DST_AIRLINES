from pymongo import MongoClient
from datetime import datetime
from api_requests import APIRequests 
from functions import FlightProcessor, FlightDataError # Importer les classes FlightProcessor et FlightDataError

# Connexion à MongoDB
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.app_data

api_requests = APIRequests() 
flightprocessor = FlightProcessor() # Créer une instance de la classe FlightProcessor

def today_flights_append():
    # Requête API pour récupérer les vols "landed" (aviationstack) => à exécuter tous les jours
    flight_info = api_requests.get_flights_landed()

    # Traiter tous les vols retournés par l'API sans filtrage
    if flight_info and 'data' in flight_info:
        flights = flight_info['data']  # Prendre tous les vols retournés
        
        if flights:
            try:
                flights_processed = []  # Pour stocker les vols traités

                # Traiter chaque vol individuellement et sauvegarder immédiatement après traitement
                for flight in flights:
                    try:
                        # Traiter chaque vol
                        processed_flight = flightprocessor.process_flight_AS(flight)
                        
                        if processed_flight:
                            # Sauvegarder le vol dans la collection "flights"
                            db.flights.insert_one(processed_flight)
                            flights_processed.append(processed_flight)
                            print(f"Vol {flight['flight']['iata']} traité et inséré dans MongoDB.")
                    
                    except FlightDataError as e:
                        if "Limite de requêtes API météo atteinte" in str(e):
                            print(f"Limite des requêtes météo atteinte. Arrêt du traitement : {e}")
                            break  # Arrête le traitement si la limite de requêtes est atteinte
                        else:
                            print(f"Erreur lors du traitement du vol {flight['flight']['iata']} : {e}")
                            continue  # Passe au vol suivant si une autre erreur est rencontrée
                
                message = f"{len(flights_processed)} résultats de vols insérés dans la base de données."
                print(message)
                
                return {"Documents ajoutés": len(flights_processed)}

            except Exception as e:
                return {"error": "Erreur inattendue lors du traitement des vols", "details": str(e)}, 500
        else:
            return {"error": "Aucun vol trouvé.", "details": flights}, 404
    else:
        return {"error": "Aucun vol trouvé ou problème avec l'API AviationStack", "details": flight_info}, 502

# Exécuter la fonction
today_flights_append()
