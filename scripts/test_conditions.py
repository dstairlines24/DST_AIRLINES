from pymongo import MongoClient
import pandas as pd
import os

# Récupérer l'URI de MongoDB depuis la variable d'environnement
mongo_uri = os.getenv("MONGO_URI")

# Connexion à MongoDB
client = MongoClient(mongo_uri)
db = client.app_data

# Charger les documents de la collection dans un DataFrame pandas
df = pd.DataFrame(list(db['final_flights'].find()))

# Fonction récursive pour extraire les valeurs de 'conditions' de manière dynamique
def extract_conditions(data):
    conditions = []
    
    # Vérifier si 'data' est un dictionnaire
    if isinstance(data, dict):
        for key, value in data.items():
            if key == 'conditions':
                conditions.append(value)
            else:
                # Appeler récursivement pour explorer les sous-dictionnaires ou listes
                conditions.extend(extract_conditions(value))
                
    # Si 'data' est une liste, on applique la fonction à chaque élément
    elif isinstance(data, list):
        for item in data:
            conditions.extend(extract_conditions(item))
    
    return conditions

# Extraire les valeurs de 'conditions' pour chaque ligne du DataFrame
all_conditions = []
for index, row in df.iterrows():
    # Extraire les conditions depuis les colonnes 'departure', 'arrival', et 'segments'
    for col in ['departure', 'arrival', 'segments']:
        if col in row and row[col] is not None:
            all_conditions.extend(extract_conditions(row[col]))

# Obtenir les valeurs uniques de conditions
unique_conditions = set(all_conditions)

print("Conditions uniques dans les segments :", unique_conditions)
