from pymongo import MongoClient
import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
#from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

#=================================================
# 1. Connexion à MongoDB et Extraction des Données
#=================================================
# Connexion à MongoDB
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.app_data

# Récupération des collections
collections = ['all_flights', 'asia_flights', 'europe_flights']
data = []

# Concaténer les collections en un DataFrame
for collection_name in collections:
    collection = db[collection_name]
    data.extend(list(collection.find()))

# Création du DataFrame pandas et suppression des doublons
df = pd.DataFrame(data).drop_duplicates(subset=['_id'])

#================================================================
# 2. Création des colonnes pour les Features et la Variable Cible
#================================================================
# Création de la variable cible : 'delay_difference'
df['delay_difference'] = df['arrival'].apply(lambda x: x.get('delay', 0)) - df['departure'].apply(lambda x: x.get('delay', 0))

# Variables descriptives distance et météo : "conditions"
def extract_features(data):
    """
    Prend en entrée une ligne du df qui sera de la forme :
    data = {
    'departure': {'conditions': 'Clear'},
    'arrival': {'conditions': 'Rain'},
    'segments': {
        '100km': {'conditions': 'Cloudy'},
        '200km': {'conditions': 'Sunny'}
        }
    }
    """
    weather_conditions = {}
    # Estimation de la distance, ex: 300km si 2 segments
    distance_km = 100
    weather_conditions['distance_km'] = distance_km + 100*len(data['segments'])

    # Extraire les conditions météo
    weather_conditions['departure_conditions'] = data['departure'].get('conditions', np.nan)
    weather_conditions['arrival_conditions'] = data['arrival'].get('conditions', np.nan)

    if 'segments' in data:
        for segment_key, segment_value in data['segments'].items():
            weather_conditions[f'{segment_key}_conditions'] = segment_value.get('conditions', np.nan)
            distance_km = distance_km + 100

    return weather_conditions
    """
    Retourne un dictionnaire de la forme :
    {
    'distance_km': '300km',
    'departure_conditions': 'Clear',
    'arrival_conditions': 'Rain',
    '100km_conditions': 'Cloudy',
    '200km_conditions': 'Sunny'
    }
    """

# Extraire les variables descriptives
weather_data = df.apply(extract_features, axis=1) #axis=1 on applique la fonction à chaque ligne
"""
0    {'distance_km': '800km', 'departure_conditions': 'Clear', 'arrival_con...
1    {'distance_km': '400km', 'departure_conditions': 'Fog', 'arrival_condi...
2    {'distance_km': '700km', 'departure_conditions': 'Sunny', 'arrival_con...
"""
weather_df = pd.DataFrame(weather_data.tolist())
"""
  distance_km  departure_conditions  arrival_conditions  100km_conditions  200km_conditions
0       800km                 Clear              Rain             Cloudy             Sunny
1       400km                  Fog           Overcast                NaN               NaN
2       700km                Sunny               Fog               Clear              Rain
"""

# Concaténer avec les données existantes pour créer le dataset final
df_final = pd.concat([df, weather_df], axis=1)
"""
departure          arrival     segments                distance_km  departure_conditions  arrival_conditions  100km_conditions  200km_conditions
0 {'conditions': 'Clear'}  {'conditions': 'Rain'}  ...       800km                 Clear                Rain             Cloudy             Sunny
1 {'conditions': 'Fog'}    {'conditions': 'Overcast'}  ...   400km                   Fog            Overcast                NaN               NaN
"""

#=========================================================
# 3. Gestion des valeurs manquantes pour la variable cible
#=========================================================
# Supprimer les lignes où 'delay_difference' est manquant
df_final = df_final[df_final['delay_difference'].notna()]

#==================================================================
# 4. Suppression des vols >= 3300km car pas assez d'enregistrements
#==================================================================
#Si on ne les suprrime pas provoque le warning : UserWarning: Skipping features without any observed values
# Supprimer les lignes où '3300Km_conditions' a une valeur non nulle
df_final = df_final[df_final['3300Km_conditions'].isna()]

# Supprimer toutes les colonnes après '3300Km_conditions'
columns_to_keep = df_final.columns[:df_final.columns.get_loc('3300Km_conditions')]
df_final = df_final[columns_to_keep]

#===================================================
# 5. Séparation des Features et de la Variable Cible
#===================================================
# Filtrer les colonnes qui nous intéressent pour l'entraînement
features = [col for col in df_final.columns if 'conditions' in col] + ['distance_km']

X = df_final[features]  # Variables descriptives
"""
departure_conditions  arrival_conditions  100km_conditions  200km_conditions
0                Clear              Rain             Cloudy             Sunny
1                 Fog           Overcast                NaN               NaN
"""
y = df_final['delay_difference']  # Variable cible
"""
0    12.0
1    -5.0
2    18.0
Name: delay_difference, dtype: float64
"""

#==========================================================
# 6. Pipelines et comparaison des modèles avec GridSearchCV
#==========================================================
# Séparation des données en ensemble d'entraînement et de test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

# Définition des colonnes catégorielles et numériques sur X
categorical_features = [col for col in X.columns if 'conditions' in col]
numeric_features = [col for col in X.columns if col not in categorical_features]

# Pipeline pour les features numériques (imputation des valeurs manquantes et mise à l'échelle)
numeric_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='mean')),
    ('scaler', StandardScaler())
])

# Pipeline pour les features catégorielles (imputation et encodage One-Hot)
categorical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='most_frequent')),
    ('onehot', OneHotEncoder(handle_unknown='ignore'))
])

# Création du préprocesseur qui appliquera les transformations à chaque type de feature
preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, numeric_features),
        ('cat', categorical_transformer, categorical_features)
    ])

# Création du pipeline principal
pipeline = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('model', RandomForestRegressor())  # Modèle par défaut, sera changé dans GridSearchCV
])

# Définition des hyperparamètres pour le GridSearchCV
param_grid = [
    {
        'model': [LinearRegression()],
        # Pas de paramètres supplémentaires pour LinearRegression
    },
    {
        'model': [DecisionTreeRegressor()],
        'model__max_depth': [None, 10, 20, 30],
        'model__min_samples_split': [2, 5, 10],
    },
    {
        'model': [RandomForestRegressor()],
        'model__n_estimators': [100, 200],
        'model__max_depth': [None, 10, 20],
        'model__min_samples_split': [2, 5]
    }
]

# Utilisation de GridSearchCV pour optimiser les hyperparamètres et sélectionner le meilleur modèle
grid_search = GridSearchCV(pipeline, param_grid, cv=5, scoring='neg_mean_squared_error', n_jobs=-1)

# Entraînement du pipeline avec GridSearch
grid_search.fit(X_train, y_train)

# Meilleur modèle après la recherche d'hyperparamètres
best_model = grid_search.best_estimator_

# Prédictions sur l'ensemble de test
y_pred = best_model.predict(X_test)

# Calcul des métriques d'évaluation
mae = mean_absolute_error(y_test, y_pred)
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
r2 = r2_score(y_test, y_pred)

# Affichage des résultats
print(f"Best Model: {grid_search.best_params_}")
print(f"MAE (Mean Absolute Error): {mae:.2f}")
print(f"MSE (Mean Squared Error): {mse:.2f}")
print(f"RMSE (Root Mean Squared Error): {rmse:.2f}")
print(f"R² (Coefficient of Determination): {r2:.2f}")