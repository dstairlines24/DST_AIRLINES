import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from pymongo import MongoClient
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

# Récupérer l'URI de MongoDB depuis la variable d'environnement
mongo_uri = os.getenv("MONGO_URI")

# Connexion à MongoDB
client = MongoClient(mongo_uri)
db = client.app_data

# Création du DataFrame pandas
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

# Forcer la mise à 0 de 'delay' si il est NaN dans 'arrival' et 'departure'
df['arrival'] = df['arrival'].apply(lambda x: {**x, 'delay': x.get('delay') if pd.notna(x.get('delay')) else 0})
df['departure'] = df['departure'].apply(lambda x: {**x, 'delay': x.get('delay') if pd.notna(x.get('delay')) else 0})

# Calcul de la variable cible 'delay_difference' après forçage des NaN à 0 dans 'delay'
df['delay_difference'] = df['arrival'].apply(lambda x: x['delay']) - df['departure'].apply(lambda x: x['delay'])
df['delay_difference'] = df['delay_difference'].apply(lambda x: max(x, 0))

# Filtre les valeurs aberrantes
df = df[df['delay_difference'] < 20]

X = df.drop(columns=['_id', 'flight_date', 'flight_status', 'delay_difference', 'arrival', 'departure', 'segments', 'airline', 
                     'flight', 'aircraft', 'dep_iata', 'arr_iata', 'departure_scheduled'])
y = df['delay_difference']

# Division des données en ensembles d'entraînement et de test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

# Création du pipeline avec SimpleImputer et StandardScaler
preprocessing_pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='mean')),
    ('scaler', StandardScaler())
])

# Transformation des données
X_train = preprocessing_pipeline.fit_transform(X_train)
X_test = preprocessing_pipeline.transform(X_test)

# Définition des modèles et des hyperparamètres pour RandomizedSearchCV
models_and_parameters = {
    'GradientBoosting': {
        'model': GradientBoostingRegressor(),
        'params': {
            'model__n_estimators': np.arange(50, 301, 50),  # 50 à 300 avec un pas de 50
            'model__learning_rate': [0.01, 0.05, 0.1, 0.2],
            'model__max_depth': [3, 5, 7, 10],
            'model__min_samples_split': [2, 5, 10],
            'model__min_samples_leaf': [1, 2, 5]
        }
    },
    'RandomForest': {
        'model': RandomForestRegressor(),
        'params': {
            'model__n_estimators': np.arange(50, 301, 50),  # 50 à 300 avec un pas de 50
            'model__max_depth': [5, 10, 15, 20],
            'model__min_samples_split': [2, 5, 10],
            'model__min_samples_leaf': [1, 2, 5]
        }
    },
    'XGBoost': {
        'model': XGBRegressor(),
        'params': {
            'model__n_estimators': np.arange(50, 301, 50),  # 50 à 300 avec un pas de 50
            'model__learning_rate': [0.01, 0.05, 0.1, 0.2],
            'model__max_depth': [3, 5, 7, 10],
            'model__subsample': [0.6, 0.8, 1.0],  # Sous-échantillonnage pour contrôle du surapprentissage
            'model__colsample_bytree': [0.6, 0.8, 1.0]  # Contrôle de la quantité de caractéristiques utilisées
        }
    }
}

# Exécution de RandomizedSearchCV pour chaque modèle
best_models = {}
for model_name, mp in models_and_parameters.items():
    pipeline = Pipeline([
        ('preprocessing', preprocessing_pipeline),
        ('model', mp['model'])
    ])
    
    # Utiliser RandomizedSearchCV pour optimiser les hyperparamètres
    random_search = RandomizedSearchCV(
        pipeline,
        mp['params'],
        cv=3,
        scoring='neg_mean_absolute_error',
        n_iter=20,  # Nombre d'itérations pour RandomizedSearchCV, ajustable pour plus ou moins de tests
        n_jobs=-1,
        random_state=42
    )
    random_search.fit(X_train, y_train)
    
    # Stocker les meilleurs résultats pour chaque modèle
    best_models[model_name] = {
        'best_estimator': random_search.best_estimator_,
        'best_score': -random_search.best_score_,
        'best_params': random_search.best_params_
    }

# Affichage des résultats pour chaque modèle
for model_name, results in best_models.items():
    print(f"\nModel: {model_name}")
    print(f"Best MAE: {results['best_score']}")
    print(f"Best Parameters: {results['best_params']}")

# Évaluation sur l'ensemble de test avec le meilleur modèle
best_model_name = min(best_models, key=lambda x: best_models[x]['best_score'])
best_model = best_models[best_model_name]['best_estimator']
y_pred = best_model.predict(X_test)

mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
print(f"\nBest Model on Test Set: {best_model_name}")
print(f"Test MAE: {mae}")
print(f"Test RMSE: {rmse}")

# Graphique de la différence entre les prédictions et les valeurs réelles
plt.figure(figsize=(10, 6))
plt.scatter(y_test, y_pred, alpha=0.5, color='b', label="Prédictions vs Valeurs réelles")
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2, label="Ligne y = x")
plt.xlabel("Valeurs réelles de delay_difference")
plt.ylabel("Valeurs prédites de delay_difference")
plt.title(f"Différence entre les Prédictions et les Valeurs Réelles\nModèle : {best_model_name}")
plt.legend()
plt.savefig('output.png')  # Sauvegarde du graphique

# Graphique des importances des caractéristiques
feature_importances = best_model['model'].feature_importances_
feature_names = X.columns  # Noms des caractéristiques
sorted_idx = np.argsort(feature_importances)[::-1]  # Tri des caractéristiques par importance

plt.figure(figsize=(12, 10))  # Augmente la taille de la figure
plt.barh(range(len(feature_importances)), feature_importances[sorted_idx], align='center')
plt.yticks(range(len(feature_importances)), [feature_names[i] for i in sorted_idx], fontsize=10)  # Augmente la taille de police
plt.xlabel("Importance", fontsize=12)
plt.ylabel("Caractéristiques", fontsize=12)
plt.title(f"Importance des Caractéristiques - {best_model_name}", fontsize=14)
plt.gca().invert_yaxis()  # Inverser l'axe pour avoir les plus importantes en haut
plt.tight_layout()  # Améliore la mise en page
plt.savefig('feature_importances.png')  # Sauvegarde du graphique
plt.show()

