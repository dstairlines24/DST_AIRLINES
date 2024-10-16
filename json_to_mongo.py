import json
from pymongo import MongoClient

# Connexion à MongoDB (utilisation de l'authentification définie dans docker-compose.yml)
client = MongoClient("mongodb://dstairlines:dstairlines@localhost:27017/")
# client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")

#------------------------Insertion données Aviationstack
# Sélectionner la base de données et la collection
db = client.airport_data
collection = db.airports

# Charger les données JSON depuis le fichier
with open('data/json_files/aviationstack_airports.json') as json_file:
    data = json.load(json_file)
    airports = data['data']  # Extraire la liste des aéroports depuis le JSON

try:
    # Insérer les données dans la collection MongoDB
    if airports:
        result = collection.insert_many(airports, ordered=False)  # ordered=False pour ignorer les doublons
        print(f"{len(result.inserted_ids)} aéroports insérés avec succès dans la base de données.")
    else:
        print("Aucune donnée à insérer.")
except Exception as e:
    print(f"Erreur lors de l'insertion des données : {e}")

#------------------------Insertion données LH
# Sélectionner la base de données et la collection
db = client.airport_data_LH
collection = db.airports

# Charger les données JSON depuis le fichier
with open('data/json_files/LHOpenAPI_airport.json') as json_file:
    data = json.load(json_file)
    airports = data['data']  # Extraire la liste des aéroports depuis le JSON

try:
    # Insérer les données dans la collection MongoDB
    if airports:
        result = collection.insert_many(airports, ordered=False)  # ordered=False pour ignorer les doublons
        print(f"{len(result.inserted_ids)} aéroports insérés avec succès dans la base de données.")
    else:
        print("Aucune donnée à insérer.")
except Exception as e:
    print(f"Erreur lors de l'insertion des données : {e}")