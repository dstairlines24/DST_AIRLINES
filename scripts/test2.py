import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pymongo import MongoClient
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

# Connexion à MongoDB et chargement des données
mongo_user = "dstairlines"
mongo_password = "dstairlines"
mongo_host = "localhost" 
mongo_port = 27017
database_name = "app_data" 
mongo_uri = f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/{database_name}?authSource=admin"
client = MongoClient(mongo_uri)
db = client[database_name]
df = pd.DataFrame(list(db['final_flights'].find()))

# Calcul de la distance totale pour chaque vol
df['total_distance'] = df['segments'].apply(lambda segments: len(segments) * 100 + 50)

# Extraction des informations météo
weather_features = ['cloudcover', 'humidity', 'precip', 'pressure', 'snow', 'snowdepth', 'temp', 'visibility', 'windspeed']

# Variables météo départ et arrivée
for col in weather_features:
    df[f'departure_{col}'] = df['departure'].apply(lambda x: x.get(col, np.nan))
    df[f'arrival_{col}'] = df['arrival'].apply(lambda x: x.get(col, np.nan))

for col in weather_features:
    # Collecter les valeurs de chaque segment pour une variable donnée
    segment_values = df['segments'].apply(
        lambda segments: [seg.get(col, np.nan) for seg in segments.values() if seg.get(col) is not None]
    )
    
    # Calcul des agrégats seulement si la liste de valeurs n'est pas vide
    # Moyenne
    df[f'segment_mean_{col}'] = segment_values.apply(lambda x: np.nanmean(x) if len(x) > 0 else np.nan)
    # Écart-type
    df[f'segment_std_{col}'] = segment_values.apply(lambda x: np.nanstd(x) if len(x) > 0 else np.nan)
    # Maximum
    df[f'segment_max_{col}'] = segment_values.apply(lambda x: np.nanmax(x) if len(x) > 0 else np.nan)
    # Minimum
    df[f'segment_min_{col}'] = segment_values.apply(lambda x: np.nanmin(x) if len(x) > 0 else np.nan)

# Forcer la mise à 0 de 'delay' si il est NaN dans 'arrival' et 'departure'
df['arrival'] = df['arrival'].apply(lambda x: {**x, 'delay': x.get('delay') if pd.notna(x.get('delay')) else 0})
df['departure'] = df['departure'].apply(lambda x: {**x, 'delay': x.get('delay') if pd.notna(x.get('delay')) else 0})

# Calcul de la variable cible 'delay_difference' après forçage des NaN à 0 dans 'delay'
df['delay_difference'] = df['arrival'].apply(lambda x: x['delay']) - df['departure'].apply(lambda x: x['delay'])
df['delay_difference'] = df['delay_difference'].apply(lambda x: max(x, 0))

# Afficher les premières lignes pour vérifier
print(df[['total_distance']].head(20))

