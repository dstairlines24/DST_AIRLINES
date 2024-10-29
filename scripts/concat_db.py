from pymongo import MongoClient
import pandas as pd

# Connexion à MongoDB
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.app_data

# Récupération des collections
collections = ['all_flights', 'asia_flights', 'europe_flights', 'america_flights', 'temp_db']
data = []

# Concaténer les collections en un DataFrame
for collection_name in collections:
    if collection_name in db.list_collection_names():  # Vérifier si la collection existe
        collection = db[collection_name]
        data.extend(list(collection.find({}, {"_id": 0})))  # Exclure le champ '_id'
    else:
        print(f"La collection '{collection_name}' n'existe pas dans la base de données.")  # Message d'erreur

# Création du DataFrame pandas MongoDB
df_new = pd.DataFrame(data)

# Récupération de la collection 'final_flights' existante s'il y a des enregistrements
if db.final_flights.estimated_document_count() > 0:
    df_existing = pd.DataFrame(list(db.final_flights.find()))

    # Retirer les ID existants pour laisser MongoDB en générer de nouveaux
    df_existing = df_existing.drop(columns=['_id'], errors='ignore')

    # Création de colonnes temporaires pour récupérer les attributs 
    df_existing['flight_iata'] = df_existing['flight'].apply(lambda x: x.get('iata') if isinstance(x, dict) else None)
    df_existing['departure_scheduled'] = df_existing['departure'].apply(lambda x: x.get('scheduled') if isinstance(x, dict) else None)
    
    # Concaténation et suppression des doublons basés sur 'flight_iata' et 'departure_scheduled'
    df_combined = pd.concat([df_existing, df_new]).drop_duplicates(subset=['flight_iata', 'departure_scheduled'])
else:
    # Si 'final_flights' est vide, utiliser seulement les nouvelles données
    df_combined = df_new

# Suppression des colonnes temporaires avant insertion
df_combined = df_combined.drop(columns=['flight_iata', 'departure_scheduled'], errors='ignore')


# Vider la collection 'final_flights' et insérer les données combinées sans doublons
db.final_flights.delete_many({})  # Supprimer tous les documents existants dans 'final_flights'
db.final_flights.insert_many(df_combined.to_dict('records'))  # Insérer les données sans les IDs

print("Données combinées et insérées dans 'final_flights' avec succès.")
