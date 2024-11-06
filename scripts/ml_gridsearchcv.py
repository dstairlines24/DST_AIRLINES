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
import joblib
import matplotlib.pyplot as plt

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
    {
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
    weather_conditions['feat_distance_km'] = distance_km

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
  feat_distance_km   feat_total_conditions_score  
0            800                       25  
1            400                       12 
2            700                       32 
"""

# Concaténer avec les données existantes pour créer le dataset final
df_final = pd.concat([df, weather_df], axis=1)
"""
departure          arrival     segments               delay_difference feat_distance_km   feat_total_conditions_score
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
feat_distance_km   feat_total_conditions_score
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

# Sauvegarde du modèle dans un fichier .pkl
if not os.path.exists('model'):
    os.makedirs('model')

joblib.dump(best_model, 'model/best_model.pkl')
print("\nmodel/best_model.pkl enregistré")
print("\n\n")

#---------------------------------------
# Affichage des fréquences de 'df_final'
#---------------------------------------
# # Compter le nombre de valeurs uniques et leur fréquence
# delay_counts = df_final['delay_difference'].value_counts()

# # Afficher les fréquences
# print(delay_counts)

# # Optionnel : Visualiser les fréquences
# plt.figure(figsize=(10, 6))
# delay_counts.plot(kind='bar')
# plt.title('Fréquence des valeurs de delay_difference')
# plt.xlabel('Delay Difference')
# plt.ylabel('Count')
# plt.grid()
#---------------------------------------

#----------------------------------------------------------
# Affichage des fréquences de 'feat_total_conditions_score'
#----------------------------------------------------------
# # Compter le nombre de valeurs uniques et leur fréquence
# delay_counts = df_final['feat_total_conditions_score'].value_counts()

# # Afficher les fréquences
# print(delay_counts)

# # Optionnel : Visualiser les fréquences
# plt.figure(figsize=(10, 6))
# delay_counts.plot(kind='bar')
# plt.title('Fréquence des valeurs de feat_total_conditions_score')
# plt.xlabel('Total Conditions Score')
# plt.ylabel('Count')
# plt.grid()
#----------------------------------------------------------

#------------------------------
# Affichage graphique en points
#------------------------------
# Créer une figure et un axe
plt.figure(figsize=(10, 6))

# Créer le nuage de points avec une échelle de couleur
scatter = plt.scatter(df_final['delay_difference'], 
                      df_final['feat_total_conditions_score'], 
                      c=df_final['feat_distance_km'], 
                      cmap='viridis', 
                      alpha=0.7)

# Ajouter une barre de couleur
cbar = plt.colorbar(scatter)
cbar.set_label('Distance (km)')

# Ajouter les étiquettes et le titre
plt.title('Relation entre Delay Difference, Total Conditions Score et Distance')
plt.ylabel('Total Conditions Score')
plt.xlabel('Delay Difference')
#------------------------------

#---------------------------------
# Affichage 2 graphiques en points
#---------------------------------
# # Créer la figure et les sous-graphiques
# fig, axs = plt.subplots(2, 1, figsize=(10, 12), constrained_layout=True)

# # Premier graphique avec df_final
# scatter1 = axs[0].scatter(df_final['delay_difference'], 
#                           df_final['feat_total_conditions_score'], 
#                           c=df_final['feat_distance_km'], 
#                           cmap='viridis', 
#                           alpha=0.7)

# # Barre de couleur pour le premier graphique
# cbar1 = fig.colorbar(scatter1, ax=axs[0])
# cbar1.set_label('Distance (km)')

# # Ajouter les étiquettes et le titre pour le premier graphique
# axs[0].set_title('Relation entre Delay Difference, Total Conditions Score et Distance (Toutes les données)')
# axs[0].set_ylabel('Total Conditions Score')
# axs[0].set_xlabel('Delay Difference')

# # Deuxième graphique avec X_train et y_train
# scatter2 = axs[1].scatter(y_train, 
#                           X_train['feat_total_conditions_score'], 
#                           c=X_train['feat_distance_km'], 
#                           cmap='viridis', 
#                           alpha=0.7)

# # Barre de couleur pour le deuxième graphique
# cbar2 = fig.colorbar(scatter2, ax=axs[1])
# cbar2.set_label('Distance (km)')

# # Ajouter les étiquettes et le titre pour le deuxième graphique
# axs[1].set_title('Relation entre Delay Difference, Total Conditions Score et Distance (Données d’entraînement)')
# axs[1].set_ylabel('Total Conditions Score')
# axs[1].set_xlabel('Delay Difference')
#---------------------------------



# # Enregistrer le graphique dans un fichier
plt.savefig('output.png')  # Enregistrer le graphique sous forme de fichier
plt.show()
plt.close()  # Fermer le graphique pour libérer la mémoire

print("Graphique enregistré sous 'output.png'")