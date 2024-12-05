import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from pymongo import MongoClient
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
    segment_values = df['segments'].apply(
        lambda segments: [seg.get(col, np.nan) for seg in segments.values() if seg.get(col) is not None]
    )
    df[f'segment_mean_{col}'] = segment_values.apply(lambda x: np.nanmean(x) if len(x) > 0 else np.nan)
    df[f'segment_std_{col}'] = segment_values.apply(lambda x: np.nanstd(x) if len(x) > 0 else np.nan)
    df[f'segment_max_{col}'] = segment_values.apply(lambda x: np.nanmax(x) if len(x) > 0 else np.nan)
    df[f'segment_min_{col}'] = segment_values.apply(lambda x: np.nanmin(x) if len(x) > 0 else np.nan)

# Forcer la mise à 0 de 'delay' si il est NaN dans 'arrival' et 'departure'
df['arrival'] = df['arrival'].apply(lambda x: {**x, 'delay': x.get('delay') if pd.notna(x.get('delay')) else 0})
df['departure'] = df['departure'].apply(lambda x: {**x, 'delay': x.get('delay') if pd.notna(x.get('delay')) else 0})

# Calcul de la variable cible 'delay_difference' après forçage des NaN à 0 dans 'delay'
df['delay_difference'] = df['arrival'].apply(lambda x: x['delay']) - df['departure'].apply(lambda x: x['delay'])
df['delay_difference'] = df['delay_difference'].apply(lambda x: max(x, 0))

X = df.drop(columns=['_id', 'flight_date', 'flight_status', 'delay_difference', 'arrival', 'departure', 'segments', 'airline', 
                     'flight', 'aircraft', 'dep_iata', 'arr_iata', 'departure_scheduled'])
y = np.log1p(df['delay_difference'])  # Applique une transformation logarithmique

# Division des données en ensembles d'entraînement et de test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

# Pipeline de prétraitement
preprocessing_pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='mean')),
    ('scaler', StandardScaler())
])

X_train = preprocessing_pipeline.fit_transform(X_train)
X_test = preprocessing_pipeline.transform(X_test)

# Définition des hyperparamètres pour XGBoost
xgb_params = {
    'model__n_estimators': np.arange(300, 601, 50),  # Affiné autour des valeurs testées
    'model__learning_rate': [0.01, 0.02, 0.03, 0.05],  # Valeurs faibles pour un apprentissage plus progressif
    'model__max_depth': [6, 8, 10],  # Restriction de la profondeur pour éviter la complexité excessive
    'model__subsample': [0.6, 0.7, 0.8, 0.9],
    'model__colsample_bytree': [0.7, 0.8, 0.9, 1.0],
    'model__gamma': [0, 0.1, 0.2, 0.3],  # Plus de valeurs fines autour des valeurs faibles
    'model__alpha': [0, 0.1, 0.5, 1],  # Régularisation L1
    'model__lambda': [1, 1.5, 2, 3]  # Régularisation L2
}

# Pipeline avec XGBoost
xgb_pipeline = Pipeline([
    ('preprocessing', preprocessing_pipeline),
    ('model', XGBRegressor(objective='reg:squarederror', random_state=42))
])

# Optimisation des hyperparamètres avec RandomizedSearchCV
random_search_xgb = RandomizedSearchCV(
    xgb_pipeline,
    xgb_params,
    cv=5,  # Garde une validation croisée modérée
    scoring='neg_mean_absolute_error',
    n_iter=50,  # Limite à 50 itérations pour réduire les temps de calcul
    n_jobs=-1,
    random_state=42
)

# Entraînement du modèle avec early stopping
random_search_xgb.fit(X_train, y_train)

# Meilleurs hyperparamètres et score
best_model_xgb = random_search_xgb.best_estimator_
best_score_xgb = -random_search_xgb.best_score_
best_params_xgb = random_search_xgb.best_params_

print(f"\nBest MAE (train): {best_score_xgb}")
print(f"Best Parameters: {best_params_xgb}")

# Évaluation sur l'ensemble de test
y_pred = np.expm1(best_model_xgb.predict(X_test))  # Enlève la transformation logarithmique

mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
print(f"\nTest MAE: {mae}")
print(f"Test RMSE: {rmse}")

print("\nNombre de lignes total:", df.shape[0])
print("Nombre de lignes dans train:", X_train.shape[0])
print("Nombre de lignes dans test:", X_test.shape[0])

# Graphique de la différence entre les prédictions et les valeurs réelles
plt.figure(figsize=(10, 6))
plt.scatter(y_test, y_pred, alpha=0.5, color='b', label="Prédictions vs Valeurs réelles")
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2, label="Ligne y = x")
plt.xlabel("Valeurs réelles de delay_difference")
plt.ylabel("Valeurs prédites de delay_difference")
plt.title("Différence entre les Prédictions et les Valeurs Réelles\nModèle : XGBoost")
plt.legend()
plt.savefig('output.png')

# Graphique des importances des caractéristiques
feature_importances = best_model_xgb['model'].feature_importances_
feature_names = X.columns
sorted_idx = np.argsort(feature_importances)[::-1]

plt.figure(figsize=(12, 10))
plt.barh(range(len(feature_importances)), feature_importances[sorted_idx], align='center')
plt.yticks(range(len(feature_importances)), [feature_names[i] for i in sorted_idx], fontsize=10)
plt.xlabel("Importance", fontsize=12)
plt.ylabel("Caractéristiques", fontsize=12)
plt.title("Importance des Caractéristiques - XGBoost", fontsize=14)
plt.gca().invert_yaxis()
plt.tight_layout()
plt.savefig('feature_importances.png')
plt.show()
