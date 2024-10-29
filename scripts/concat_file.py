import os
from pymongo import MongoClient
import pandas as pd
import json
from bson import json_util
from bson.objectid import ObjectId

# Connexion à MongoDB
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.app_data

# Chemin vers le répertoire de sauvegarde
backup_dir = 'backup/app_data'

# Vérification des fichiers .bson dans le répertoire
bson_files = [f for f in os.listdir(backup_dir) if f.endswith('.bson')]

if not bson_files:
    print("Erreur : Aucun fichier .bson trouvé dans le répertoire 'backup/app_data'.")
else:
    # Charger le contenu de la première collection .bson trouvée
    bson_file_path = os.path.join(backup_dir, bson_files[0])

    # Charger les données depuis le fichier .bson
    # Utilisation de la commande mongoimport pour importer dans une collection temporaire
    os.system(f"mongoimport --uri mongodb://dstairlines:dstairlines@localhost:27017/app_data --collection temp_db --file {bson_file_path} --jsonArray")

    # Récupérer les données de la collection importée dans un DataFrame
    data = list(db.temp_db.find({}, {"_id": 0})) # Exclure le champ '_id'
    df_new = pd.DataFrame(data)

    # Supprimer la collection temporaire
    db.temp_db.drop()

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
