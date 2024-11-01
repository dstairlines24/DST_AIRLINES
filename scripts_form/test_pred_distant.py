import requests
from pymongo import MongoClient
import os

# Récupérer la clé API pour envoyer la requête
api_key = os.getenv("API_KEY")

url = 'http://flask_app:5000/predict'

# Récupérer l'URI de MongoDB depuis la variable d'environnement
mongo_uri = os.getenv("MONGO_URI")

# Connexion à MongoDB
client = MongoClient(mongo_uri)
db = client.app_data_form

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
    retard_pred = response.json().get('prediction')
    # Convertir le retard en secondes
    total_seconds = int(retard_pred * 60)  # Convertir en secondes

    # Calculer les heures, minutes et secondes
    hours = total_seconds // 3600
    remaining_seconds = total_seconds % 3600
    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60

    # Formater l'affichage
    formatted_retard = f"{hours} heures {minutes} minutes {seconds} secondes"

    print("==================================================")
    print("---> prediction = ", formatted_retard)
    print("==================================================")
except ValueError as e:
    print("Erreur lors du décodage JSON:", e)
