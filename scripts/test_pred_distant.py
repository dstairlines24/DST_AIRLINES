import requests
from pymongo import MongoClient
import os

# Récupérer l'URI de MongoDB depuis la variable d'environnement
mongo_uri = os.getenv("MONGO_URI")

# Connexion à MongoDB
client = MongoClient(mongo_uri)
db = client.app_data

url = 'http://flask_app:5000/predict'

flight_data = db.final_flights.find_one({}, {"_id": 0})
print(flight_data)
print("\n\n")

response = requests.post(url, json=flight_data)

# Debug : Affiche la réponse brute du serveur
print("Statut de la réponse:", response.status_code)
print("Contenu brut de la réponse:", response.text)

# Tenter de décoder en JSON si le contenu est valide
try:
    prediction = response.json().get('prediction')
    print("Prédiction:", prediction)
except ValueError as e:
    print("Erreur lors du décodage JSON:", e)
