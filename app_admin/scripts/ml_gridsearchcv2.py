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
import os


#==========================================================
# Récupérer la collection final_flights dans MongoDB
#==========================================================
# Récupérer l'URI de MongoDB depuis la variable d'environnement
mongo_uri = os.getenv("MONGO_URI")

# Connexion à MongoDB
client = MongoClient(mongo_uri)
db = client.app_data

# Création du DataFrame pandas
df = pd.DataFrame(list(db['final_flights'].find()))

#==========================================================
# Appliquer les transformation avec la classe DataTransform
#==========================================================
from ml_data_transform import DataTransform
datatransform = DataTransform(df)
df = datatransform.remove_na(subset=['target_delay_difference']) # Supprimer les lignes où 'target_delay_difference' est manquant
df = datatransform.add_feat_infos_meteo()                        # Ajout des informations météo
df = datatransform.segment_to_col()                              # Transforme les segments en colonne
df = datatransform.add_feat_icon_score()                         # Ajout du score d'icône
df = datatransform.add_feat_distance_km()                        # Ajout de la distance du vol
df = datatransform.add_target_delay_diff()                       # Ajout de la variable cible 'target_delay_difference'

#==========================================================
# Séparation du Dataset
#==========================================================
# Filtrer les colonnes qui nous intéressent pour l'entraînement
features = [col for col in df.columns if 'feat_' in col]

X = df[features]  # Variables descriptives
y = df['target_delay_difference']  # Variable cible

#==========================================================
# Pipelines et comparaison des modèles avec GridSearchCV
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
# Affichage des fréquences de 'df'
#---------------------------------------
# # Compter le nombre de valeurs uniques et leur fréquence
# delay_counts = df['target_delay_difference'].value_counts()

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
# Affichage des fréquences de 'feat_total_icon_score'
#----------------------------------------------------------
# # Compter le nombre de valeurs uniques et leur fréquence
# delay_counts = df['feat_total_icon_score'].value_counts()

# # Afficher les fréquences
# print(delay_counts)

# # Optionnel : Visualiser les fréquences
# plt.figure(figsize=(10, 6))
# delay_counts.plot(kind='bar')
# plt.title('Fréquence des valeurs de feat_total_icon_score')
# plt.xlabel('Total icon Score')
# plt.ylabel('Count')
# plt.grid()
#----------------------------------------------------------

#------------------------------
# Affichage graphique en points
#------------------------------
# Créer une figure et un axe
plt.figure(figsize=(10, 6))

# Créer le nuage de points avec une échelle de couleur
scatter = plt.scatter(df['target_delay_difference'], 
                      df['feat_total_icon_score'], 
                      c=df['feat_distance_km'], 
                      cmap='viridis', 
                      alpha=0.7)

# Ajouter une barre de couleur
cbar = plt.colorbar(scatter)
cbar.set_label('Distance (km)')

# Ajouter les étiquettes et le titre
plt.title('Relation entre Delay Difference, Total icon Score et Distance')
plt.ylabel('Total icon Score')
plt.xlabel('Delay Difference')
#------------------------------

#---------------------------------
# Affichage 2 graphiques en points
#---------------------------------
# # Créer la figure et les sous-graphiques
# fig, axs = plt.subplots(2, 1, figsize=(10, 12), constrained_layout=True)

# # Premier graphique avec df
# scatter1 = axs[0].scatter(df['target_delay_difference'], 
#                           df['feat_total_icon_score'], 
#                           c=df['feat_distance_km'], 
#                           cmap='viridis', 
#                           alpha=0.7)

# # Barre de couleur pour le premier graphique
# cbar1 = fig.colorbar(scatter1, ax=axs[0])
# cbar1.set_label('Distance (km)')

# # Ajouter les étiquettes et le titre pour le premier graphique
# axs[0].set_title('Relation entre Delay Difference, Total icon Score et Distance (Toutes les données)')
# axs[0].set_ylabel('Total icon Score')
# axs[0].set_xlabel('Delay Difference')

# # Deuxième graphique avec X_train et y_train
# scatter2 = axs[1].scatter(y_train, 
#                           X_train['feat_total_icon_score'], 
#                           c=X_train['feat_distance_km'], 
#                           cmap='viridis', 
#                           alpha=0.7)

# # Barre de couleur pour le deuxième graphique
# cbar2 = fig.colorbar(scatter2, ax=axs[1])
# cbar2.set_label('Distance (km)')

# # Ajouter les étiquettes et le titre pour le deuxième graphique
# axs[1].set_title('Relation entre Delay Difference, Total icon Score et Distance (Données d’entraînement)')
# axs[1].set_ylabel('Total icon Score')
# axs[1].set_xlabel('Delay Difference')
#---------------------------------



# # Enregistrer le graphique dans un fichier
plt.savefig('output.png')  # Enregistrer le graphique sous forme de fichier
plt.show()
plt.close()  # Fermer le graphique pour libérer la mémoire

print("Graphique enregistré sous 'output.png'")