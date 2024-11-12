from pymongo import MongoClient
import os
import bson

# ================================
# Le ficher à importer doit être : 
# data_test/temp_col.bson
# ================================

# Récupérer l'URI de MongoDB depuis la variable d'environnement
mongo_uri = os.getenv("MONGO_URI")

# Débogage : afficher l'URI et autres informations d'authentification
print(f"Connecting to MongoDB with URI: {mongo_uri}")

# Connexion à MongoDB
try:
    client = MongoClient(mongo_uri)
    print("Connexion à MongoDB réussie.")
except Exception as e:
    print("Erreur de connexion à MongoDB:", e)
    exit(1)

def load_temp_to_temp_col(bson_file_path):
    # Charger le fichier .bson et insérer les documents dans la collection temp_col
    db_app = client.app_data

    # Supprimer la collection si elle existe déjà pour éviter les doublons
    db_app.temp_col.drop()

    try:
        # Lire le fichier .bson et insérer chaque document
        with open(bson_file_path, 'rb') as f:
            data = bson.decode_all(f.read())
            db_app.temp_col.insert_many(data)
        print(f"Collection 'app_data.temp_col' remplie avec succès à partir de {bson_file_path}")
    except Exception as e:
        print("Erreur lors du chargement du fichier .bson:", e)

if __name__ == "__main__":
    # Spécifier le chemin vers le fichier .bson
    bson_file_path = "data_test/temp_col.bson"
    load_temp_to_temp_col(bson_file_path)
