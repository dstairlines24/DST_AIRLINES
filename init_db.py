from pymongo import MongoClient
from werkzeug.security import generate_password_hash
import os

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
    db = client.app_credentials
    print("Connexion à MongoDB réussie.")
except Exception as e:
    print("Erreur de connexion à MongoDB:", e)
    exit(1)

def init_db():
    # Supprimer la collection des utilisateurs si elle existe déjà
    db.users.drop()

    # Créer des utilisateurs avec des mots de passe hachés
    flask_admin_password_h = generate_password_hash(flask_admin_password)
    flask_user_password_h = generate_password_hash(flask_user_password)

    db.users.insert_one({"username": flask_admin_login, "password": flask_admin_password_h, "role": "admin"})
    db.users.insert_one({"username": flask_user_login, "password": flask_user_password_h, "role": "user"})

    print("Base de données initialisée avec succès !")

if __name__ == "__main__":
    init_db()
