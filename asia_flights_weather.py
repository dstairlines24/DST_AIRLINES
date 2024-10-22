from pymongo import MongoClient
from datetime import datetime
from api_requests import APIRequests 
from functions import FlightProcessor, FlightDataError

# Connexion à MongoDB
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.app_data

flightprocessor = FlightProcessor()

def today_asia_flights_append():
    # Requête API pour récupérer les vols landed (aviationstack)
    flight_info = flightprocessor.get_flights_landed()

    # Filtrer les vols avec un départ et une arrivée en Asie
    if flight_info and 'data' in flight_info:
        asia_flights = [
            flight for flight in flight_info['data']
            if flight.get('departure', {}).get('timezone') and flight.get('arrival', {}).get('timezone') and
               flight['departure']['timezone'].startswith('Asia') and flight['arrival']['timezone'].startswith('Asia')
        ]

        if asia_flights:
            successfully_processed_flights = []
            failed_flights = []

            for flight in asia_flights:
                try:
                    # Traite chaque vol individuellement
                    flight_document = flightprocessor.process_flight_AS(flight)

                    # Si le traitement réussit, insérer dans MongoDB
                    if flight_document:
                        db.asia_flights.insert_one(flight_document)
                        successfully_processed_flights.append(flight)
                        print(f"Vol {flight['flight']['iata']} traité et inséré.")
                
                except FlightDataError as e:
                    # Si une erreur survient, log l'erreur et continuer avec les autres vols
                    failed_flights.append({
                        "flight": flight,
                        "error": str(e),
                        "details": e.args
                    })
                    print(f"Erreur sur le vol {flight['flight']['iata']}: {str(e)}")

            # Résumé des opérations
            print(f"{len(successfully_processed_flights)} vols traités et insérés dans la base de données.")
            if failed_flights:
                print(f"{len(failed_flights)} vols ont échoué et n'ont pas été insérés.")

            return {
                "vols traités": len(successfully_processed_flights),
                "vols échoués": len(failed_flights),
                "details échecs": failed_flights
            }

        else:
            return {"error": "Aucun vol trouvé en Asie.", "details": asia_flights}, 404
    else:
        return {"error": "Aucun vol trouvé ou problème API AS", "details": flight_info}


today_asia_flights_append()
