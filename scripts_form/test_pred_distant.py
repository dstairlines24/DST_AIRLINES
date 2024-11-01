import requests
from pymongo import MongoClient
import os

# Utiliser une variable d'environnement pour stocker la clé API de manière sécurisée
api_key = os.getenv("API_KEY")

# Récupérer l'URI de MongoDB depuis la variable d'environnement
mongo_uri = os.getenv("MONGO_URI")

# Connexion à MongoDB
client = MongoClient(mongo_uri)
db = client.app_data_form

url = 'http://flask_app:5000/predict'

# --------------------------------------------------------------
# Choisir une collection où récupérer un exemple de vol à tester
# --------------------------------------------------------------
flight_data = db.test_col.find_one({}, {"_id": 0})
# --------------------------------------------------------------

print(f"Contenu de flight_data : \n{flight_data}\n")
print("\n\n")

headers = {
    'x-api-key': api_key
}

response = requests.post(url, json=flight_data, headers=headers)

# Debug : Affiche la réponse brute du serveur
print("------Statut de la réponse:", response.status_code)
print("------Contenu brut de la réponse:", response.text)

# Tenter de décoder en JSON si le contenu est valide
try:
    prediction = response.json().get('prediction')
    print("--------------------\n---->prediction = ", prediction)
except ValueError as e:
    print("Erreur lors du décodage JSON:", e)
