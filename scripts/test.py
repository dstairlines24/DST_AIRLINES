import pandas as pd
import numpy as np
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

# Calcul de la variable cible 'delay_difference'
df['delay_difference'] = df['arrival'].apply(lambda x: x.get('delay', 0)) - df['departure'].apply(lambda x: x.get('delay', 0))
df['delay_difference'] = df['delay_difference'].apply(lambda x: max(x, 0))

# Supprimer les lignes où 'delay_difference' est null
df = df.dropna(subset=['delay_difference'])

X = df.drop(columns=['_id', 'flight_date', 'flight_status', 'delay_difference', 'arrival', 'departure', 'segments', 'airline', 'flight', 'aircraft', 'dep_iata', 'arr_iata', 'departure_scheduled'])
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

# Définition des modèles et des hyperparamètres pour GridSearchCV
models_and_parameters = {
    'GradientBoosting': {
        'model': GradientBoostingRegressor(),
        'params': {
            'model__n_estimators': [50, 100, 150],
            'model__learning_rate': [0.05, 0.1, 0.2],
            'model__max_depth': [3, 5, 7]
        }
    },
    'RandomForest': {
        'model': RandomForestRegressor(),
        'params': {
            'model__n_estimators': [50, 100, 150],
            'model__max_depth': [5, 10, 15]
        }
    },
    'XGBoost': {
        'model': XGBRegressor(),
        'params': {
            'model__n_estimators': [50, 100, 150],
            'model__learning_rate': [0.05, 0.1, 0.2],
            'model__max_depth': [3, 5, 7]
        }
    }
}

# Exécution de GridSearchCV pour chaque modèle
best_models = {}
for model_name, mp in models_and_parameters.items():
    pipeline = Pipeline([
        ('preprocessing', preprocessing_pipeline),
        ('model', mp['model'])
    ])
    grid_search = GridSearchCV(pipeline, mp['params'], cv=3, scoring='neg_mean_absolute_error', n_jobs=-1)
    grid_search.fit(X_train, y_train)
    best_models[model_name] = {
        'best_estimator': grid_search.best_estimator_,
        'best_score': -grid_search.best_score_,  # Négatif car sklearn utilise -MAE pour maximiser
        'best_params': grid_search.best_params_
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

