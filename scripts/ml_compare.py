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
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib.pyplot as plt
import pandas as pd

#=================================================
# 1. Connexion à MongoDB et Extraction des Données
#=================================================
import os

# Récupérer l'URI de MongoDB depuis la variable d'environnement
mongo_uri = os.getenv("MONGO_URI")

# Connexion à MongoDB
client = MongoClient(mongo_uri)
db = client.app_data

# Création du DataFrame pandas et suppression des doublons
df = pd.DataFrame(list(db['final_flights'].find())).drop_duplicates(subset=['_id'])
# df = pd.DataFrame(list(db['final_flights'].find()))

#================================================================
# 2. Création des colonnes pour les Features et la Variable Cible
#================================================================
# Création de la variable cible : 'delay_difference'
df['delay_difference'] = df['arrival'].apply(lambda x: x.get('delay', 0)) - df['departure'].apply(lambda x: x.get('delay', 0))
df['delay_difference'] = df['delay_difference'].apply(lambda x: max(x, 0))  # Remplace les valeurs négatives par 0

# Variables descriptives distance et météo : "conditions"
def extract_features(data):
    """
    Prend en entrée une ligne du df qui sera de la forme :
    data = {
    'departure': ... {'conditions': 'Clear'}...,
    'arrival': ... {'conditions': 'Rain'}...,
    'segments': {
        '100km': ... {'conditions': 'Cloudy'}...,
        '200km': ... {'conditions': 'Sunny'}...
        }
    }
    """
    weather_conditions = {}
    # Estimation de la distance, ex: 300km si 2 segments
    distance_km = 100 + 100 * len(data.get('segments', {}))
    weather_conditions['feat_distance_km'] = distance_km + 100*len(data['segments'])

    # Définir un système de score pour les conditions
    conditions_scores = {
        'Clear': 0,                       # Conditions idéales pour le vol
        'Partially cloudy': 1,            # Conditions généralement favorables
        'Overcast': 3,                    # Peut entraîner des restrictions de visibilité
        'Rain': 5,                        # Impact sur la visibilité et les performances de l'avion
        'Snow': 6,                        # Peut entraîner des retards et des problèmes d'atterrissage
        'Fog': 8,                         # Très faible visibilité, conditions dangereuses
        'Wind': 7,                        # Vitesse du vent élevée, risque d'instabilité
        'Cloudy': 4,                      # Couverture nuageuse importante, peut affecter le vol
        'Partly cloudy (day)': 2,        # Conditions de vol généralement sûres pendant la journée
        'Partly cloudy (night)': 3,      # Conditions de vol généralement sûres la nuit, mais moins de visibilité
        'Clear (day)': 0,                # Conditions idéales pendant la journée
        'Clear (night)': 1                # Conditions favorables la nuit
    }


    # Extraire les conditions météo et calculer un score total
    departure_conditions = data['departure'].get('conditions', np.nan)
    arrival_conditions = data['arrival'].get('conditions', np.nan)
    departure_conditions_score = conditions_scores.get(departure_conditions, 0)
    arrival_conditions_score = conditions_scores.get(arrival_conditions, 0)

    segment_conditions = []
    if 'segments' in data:
        for segment_key, segment_value in data['segments'].items():
            segment_conditions = segment_value.get('conditions', np.nan)
    
    segment_conditions_score = sum(conditions_scores.get(condition, 0) for condition in segment_conditions)
    total_conditions_score = segment_conditions_score + departure_conditions_score + arrival_conditions_score
    weather_conditions['feat_total_conditions_score'] = total_conditions_score

    return weather_conditions
    """
    Retourne un dictionnaire de la forme :
    {
    'feat_distance_km': '800',
    'feat_total_conditions_score': '25'
    }
    """

# Extraire les variables descriptives
weather_data = df.apply(extract_features, axis=1) #axis=1 on applique la fonction à chaque ligne
"""
0    {'feat_distance_km': '800', 'feat_total_conditions_score': '25'} 
1    {'feat_distance_km': '400', 'feat_total_conditions_score': '12'}
2    {'feat_distance_km': '700', 'feat_total_conditions_score': '32'}
"""
weather_df = pd.DataFrame(weather_data.tolist())
"""
  feat_distance_km   total_conditions_score  
0            800                       25  
1            400                       12 
2            700                       32 
"""

# Concaténer avec les données existantes pour créer le dataset final
df_final = pd.concat([df, weather_df], axis=1)
"""
departure          arrival     segments               delay_difference feat_distance_km   total_conditions_score
0   .........................................                     12.0            800                       25
1   .........................................                     -5.0            400                       12
1   .........................................                     18.0            400                       32
"""

#=========================================================
# 3. Gestion des valeurs manquantes pour la variable cible
#=========================================================
# Supprimer les lignes où 'delay_difference' est manquant
df_final = df_final[df_final['delay_difference'].notna()]


#===================================================
# 4. Séparation des Features et de la Variable Cible
#===================================================
# Filtrer les colonnes qui nous intéressent pour l'entraînement
features = [col for col in df_final.columns if 'feat_' in col]

X = df_final[features]  # Variables descriptives
"""
feat_distance_km   total_conditions_score
           800                       25
           400                       12
           400                       32
"""
y = df_final['delay_difference']  # Variable cible
"""
0    12.0
1    -5.0
2    18.0
Name: delay_difference, dtype: float64
"""

#==========================================================
# 5. Pipelines et comparaison des modèles avec GridSearchCV
#==========================================================
# Séparation des données en ensemble d'entraînement et de test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

# Définition des colonnes catégorielles et numériques sur X
categorical_features = [col for col in X.columns if 'cat_' in col]
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



# Liste des modèles à évaluer
models = {
    'Linear Regression': LinearRegression(),
    'Decision Tree': DecisionTreeRegressor(max_depth=None, min_samples_split=2),  # Vous pouvez ajuster ces hyperparamètres
    'Random Forest': RandomForestRegressor(n_estimators=100, max_depth=None, min_samples_split=2)
}

# Initialiser une liste pour stocker les résultats
results = []

# Boucle sur chaque modèle
for model_name, model in models.items():
    # Créer un pipeline avec le préprocesseur et le modèle
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('model', model)
    ])
    
    # Entraîner le modèle
    pipeline.fit(X_train, y_train)
    
    # Prédire sur l'ensemble de test
    y_pred = pipeline.predict(X_test)
    
    # Calculer les métriques
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, y_pred)
    
    # Stocker les résultats
    results.append({
        'Model': model_name,
        'MAE': mae,
        'MSE': mse,
        'RMSE': rmse,
        'R²': r2
    })

# Convertir les résultats en DataFrame
results_df = pd.DataFrame(results)

# Afficher les résultats
print(results_df)

# Visualiser les résultats
results_df.set_index('Model')[['MAE', 'MSE', 'RMSE', 'R²']].plot(kind='bar', figsize=(12, 6))
plt.title('Model Performance Comparison')
plt.ylabel('Score')
plt.xticks(rotation=45)
plt.grid(axis='y')

# Enregistrer le graphique dans un fichier
plt.savefig('output.png')  # Enregistrer le graphique sous forme de fichier
plt.show()
plt.close()  # Fermer le graphique pour libérer la mémoire

print("Graphique enregistré sous 'output.png'")