from pymongo import MongoClient
from werkzeug.security import generate_password_hash

# Connexion à MongoDB
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.app_data

def init_db():
    # Supprimer la collection des utilisateurs si elle existe déjà
    db.users.drop()

    # Créer des utilisateurs avec des mots de passe hachés
    admin_password = generate_password_hash("admin")
    user_password = generate_password_hash("admin")
    user2_password = generate_password_hash("dstairlines")

    db.users.insert_one({"username": "admin", "password": admin_password, "role": "admin"})
    db.users.insert_one({"username": "admin", "password": user_password, "role": "user"})

    # Compte pour tester
    db.users.insert_one({"username": "dstairlines", "password": user2_password, "role": "user"})

    print("Base de données initialisée avec succès !")

if __name__ == "__main__":
    init_db()
