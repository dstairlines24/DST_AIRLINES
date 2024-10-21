from pymongo import MongoClient
from api_requests import APIRequests
from functions import FlightProcessor

# Connexion à MongoDB
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.app_data

api_requests = APIRequests()
flightprocessor = FlightProcessor()

def today_all_flights_append():
    try:
        # Requête API pour récupérer les vols "landed"
        flight_info = api_requests.get_flights_landed()

        if flight_info and 'data' in flight_info:
            all_flights = flight_info['data']

            if all_flights:
                # Traiter les vols
                all_flights_processed = flightprocessor.process_flight_AS_list(all_flights)

                if all_flights_processed:
                    # Insertion des vols dans MongoDB
                    result = db.all_flight.insert_many(all_flights_processed)
                    print(f"{len(result.inserted_ids)} vols insérés dans la base de données.")
                    return {"Documents ajoutés": len(result.inserted_ids)}
                else:
                    print("Aucun vol valide à insérer.")
                    return {"error": "Aucun vol valide à insérer."}
            else:
                print("Aucun vol trouvé.")
                return {"error": "Aucun vol trouvé."}
        else:
            print("Problème avec l'API AviationStack.")
            return {"error": "Problème avec l'API AviationStack."}

    except Exception as e:
        print(f"Erreur lors de l'insertion des vols : {e}")
        return {"error": str(e)}

# Exécuter la fonction
today_all_flights_append()
