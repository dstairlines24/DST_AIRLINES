from pymongo import MongoClient
from werkzeug.security import generate_password_hash
import os
import bson

# Récupérer l'URI de MongoDB depuis la variable d'environnement
mongo_uri = os.getenv("MONGO_URI")
flask_admin_login = os.getenv("FLASK_ADMIN_LOGIN")
flask_admin_password = os.getenv("FLASK_ADMIN_PASSWORD")
flask_user_login = os.getenv("FLASK_USER_LOGIN")
flask_user_password = os.getenv("FLASK_USER_PASSWORD")

# Débogage : afficher l'URI et autres informations d'authentification
print(f"Connecting to MongoDB with URI: {mongo_uri}")
print(f"Admin login: {flask_admin_login}, User login: {flask_user_login}")

# Connexion à MongoDB
try:
    client = MongoClient(mongo_uri)
    print("Connexion à MongoDB réussie.")
except Exception as e:
    print("Erreur de connexion à MongoDB:", e)
    exit(1)

def init_db():
    db_credientials = client.app_credentials
    # Supprimer la collection des utilisateurs si elle existe déjà
    db_credientials.users.drop()

    # Créer des utilisateurs avec des mots de passe hachés
    flask_admin_password_h = generate_password_hash(flask_admin_password)
    flask_user_password_h = generate_password_hash(flask_user_password)

    db_credientials.users.insert_one({"username": flask_admin_login, "password": flask_admin_password_h, "role": "admin"})
    db_credientials.users.insert_one({"username": flask_user_login, "password": flask_user_password_h, "role": "user"})

    print("Base de données initialisée avec succès !")

def load_test_to_app_data(bson_file_path):
    # Charger le fichier .bson et insérer les documents dans la collection test_col
    db_app = client.app_data

    # Supprimer la collection si elle existe déjà pour éviter les doublons
    db_app.test_col.drop()

    try:
        # Lire le fichier .bson et insérer chaque document
        with open(bson_file_path, 'rb') as f:
            data = bson.decode_all(f.read())
            db_app.test_col.insert_many(data)
        print(f"Collection 'app_data.test_col' remplie avec succès à partir de {bson_file_path}")
    except Exception as e:
        print("Erreur lors du chargement du fichier .bson:", e)

def load_test_to_app_data_form(bson_file_path):
    # Charger le fichier .bson et insérer les documents dans la collection test_col
    db_app_form = client.app_data_form
    db_app = client.app_data

    # Supprimer la collection si elle existe déjà pour éviter les doublons
    db_app_form.test_col.drop()
    db_app.temp_col.drop()

    try:
        # Lire le fichier .bson et insérer chaque document
        with open(bson_file_path, 'rb') as f:
            data = bson.decode_all(f.read())
            db_app_form.test_col.insert_many(data)
            db_app.temp_col.insert_many(data)
        print(f"Collection 'app_data_form.test_col' remplie avec succès à partir de {bson_file_path}")
        print(f"Collection 'app_data.temp_col' remplie avec succès à partir de {bson_file_path}")
    except Exception as e:
        print("Erreur lors du chargement du fichier .bson:", e)


if __name__ == "__main__":
    init_db()
    # Spécifier le chemin vers le fichier .bson
    bson_file_path = "data_test/test_col.bson"
    load_test_to_app_data(bson_file_path)
    load_test_to_app_data_form(bson_file_path)
