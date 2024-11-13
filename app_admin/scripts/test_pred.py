from pymongo import MongoClient
import os
import joblib
import pandas as pd
import numpy as np


# Récupérer l'URI de MongoDB depuis la variable d'environnement
mongo_uri = os.getenv("MONGO_URI")

# Connexion à MongoDB
client = MongoClient(mongo_uri)
db = client.app_data


# Fonction de prédiction pour un appel direct
def predict_from_data(flight_data):
    #==========================================================
    # Récupérer le modèle sauvegardé et Créer le df
    #==========================================================
    model_path = 'model/best_model.pkl'

    if os.path.exists(model_path):
        best_model = joblib.load(model_path)
    else:
        raise ValueError("Modèle non trouvé. Veuillez vérifier le fichier 'best_model.pkl'.")


    # Création du DataFrame pandas
    # df = pd.DataFrame(list(flight_data))
    df = pd.DataFrame(flight_data)
    print("---------------------------------------------------------------------------------------")
    print(f"\nContenu de df : \n{df}\n")
    
    #==========================================================
    # Appliquer les transformation avec la classe DataTransform
    #==========================================================
    from ml_data_transform import DataTransform
    datatransform = DataTransform(df)
    df = datatransform.apply_feat_transforms()
    print("---------------------------------------------------------------------------------------")
    print(f"\nContenu de df après DataTransform: \n{df}\n")
    
    #==========================================================
    # Séparation du Dataset
    #==========================================================
    # Filtrer les colonnes qui nous intéressent pour l'entraînement
    features = [col for col in df.columns if 'feat_' in col]

    # Créer un DataFrame pour les données de prédiction
    input_data = df[features]
    print("---------------------------------------------------------------------------------------")
    print(f"\nContenu de input_data : \n{input_data}\n")

    #==========================================================
    # Application du preprocessing (pipeline du modèle)
    #==========================================================
    processed_input = best_model.named_steps['preprocessor'].transform(input_data)
    print("---------------------------------------------------------------------------------------")
    print(f"\nContenu de processed_input : \n{processed_input}\n")
    print(f"Type de processed_input : {type(processed_input)}\n")

    # Transformation en DF
    processed_input_df = pd.DataFrame(processed_input, columns=input_data.columns)
    print("---------------------------------------------------------------------------------------")
    print(f"\nContenu de processed_input_df : \n{processed_input_df}\n")
    print(f"Type de processed_input_df : {type(processed_input_df)}\n")

    #==========================================================
    # Prédiction avec le modèle
    #==========================================================
    try:
        prediction = best_model.predict(processed_input_df)
        return prediction[0]
    except Exception as e:
        print(f"Erreur lors de la prédiction : {e}")
        raise ValueError("Erreur lors de la prédiction avec le modèle.")


# --------------------------------------------------------------
# Choisir une collection où récupérer un exemple de vol à tester
# --------------------------------------------------------------
# flight_data = db.test_col.find_one({}, {"_id": 0})
# flight_data = db['test_col'].find()
# flight_data = list(db['test_col'].find())
flight_data = list(db['test_col'].find({}, {"_id": 0}))

# print("---------------------------------------------------------------------------------------")
# print(f"Contenu de flight_data : \n{flight_data}\n")
# --------------------------------------------------------------

if flight_data:
    try:
        # Prédiction du retard sur le vol
        retard_pred = predict_from_data(flight_data)
        # Convertir le retard en secondes
        total_seconds = int(retard_pred * 60)  # Convertir en secondes

        # Calculer les heures, minutes et secondes
        hours = total_seconds // 3600
        remaining_seconds = total_seconds % 3600
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60

        # Formater l'affichage
        formatted_retard = f"{hours} heures {minutes} minutes {seconds} secondes"

        print("\n\n")
        print("==================================================================================================")
        print(f"---> retard_pred = {formatted_retard}")
        print("==================================================================================================")
    except Exception as e:
        error_message = f"Erreur lors de la prédiction: {str(e)}"
        print("\n\n")
        print("==================================================================================================")
        print(error_message)   
        print("==================================================================================================")

else:
    error_message = "Aucune donnée de vol trouvée dans la base de données."
    print(error_message)
