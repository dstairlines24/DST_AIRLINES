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
df = datatransform.apply_feat_transforms()
df = datatransform.apply_target_transforms()

#==========================================================
# Séparation du Dataset
#==========================================================
# Filtrer les colonnes qui nous intéressent pour l'entraînement
features = [col for col in df.columns if 'feat_' in col]

X = df[features]  # Variables descriptives
y = df['target_delay_difference']  # Variable cible

#==========================================================
# Pipelines et comparaison des métrics des modèles
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