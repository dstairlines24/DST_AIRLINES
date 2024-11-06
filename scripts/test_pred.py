from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, stream_with_context, abort, session, flash, get_flashed_messages, send_file
from pymongo import MongoClient
from datetime import datetime
from functools import wraps
from werkzeug.security import check_password_hash  # Pour vérifier les mots de passe
import subprocess
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
    # Charger le modèle ML sauvegardé
    if not os.path.exists('model'):
        os.makedirs('model')

    model_path = 'model/best_model.pkl'

    if os.path.exists(model_path):
        best_model = joblib.load(model_path)
    else:
        raise ValueError("Modèle non trouvé. Veuillez vérifier le fichier 'best_model.pkl'.")
    
    flight_info = flight_data

    #--------------------------
    # Mise en forme des données
    #--------------------------
    print(f"\nContenu de flight_info : \n {flight_info}\n")
    # Extraction des features pertinentes
    weather_conditions = {}

    # Distance estimée en fonction du nombre de segments
    distance_km = 100 + 100 * len(flight_info.get('segments', {}))
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
    departure_conditions = flight_info['departure'].get('conditions', np.nan)
    arrival_conditions = flight_info['arrival'].get('conditions', np.nan)
    departure_conditions_score = conditions_scores.get(departure_conditions, 0)
    arrival_conditions_score = conditions_scores.get(arrival_conditions, 0)

    segment_conditions = []
    if 'segments' in flight_info:
        for segment_key, segment_value in flight_info['segments'].items():
            segment_conditions = segment_value.get('conditions', np.nan)
    
    segment_conditions_score = sum(conditions_scores.get(condition, 0) for condition in segment_conditions)
    total_conditions_score = segment_conditions_score + departure_conditions_score + arrival_conditions_score
    weather_conditions['feat_total_conditions_score'] = total_conditions_score
    #--------------------------

    # Créer un DataFrame pour les données de prédiction
    input_data = pd.DataFrame([weather_conditions])
    print(f"\nContenu de input_data : \n{input_data}\n")

    # Application du pipeline de prétraitement
    processed_input = best_model.named_steps['preprocessor'].transform(input_data)
    print(f"\nContenu de processed_input : \n{processed_input}\n")
    print(f"Type de processed_input : {type(processed_input)}\n")

    processed_input_df = pd.DataFrame(processed_input, columns=input_data.columns)
    print(f"\nContenu de processed_input_df : \n{processed_input_df}\n")
    print(f"Type de processed_input_df : {type(processed_input_df)}\n")

    # Prédiction avec le modèle
    prediction = best_model.predict(processed_input_df)
    
    return prediction[0]

# --------------------------------------------------------------
# Choisir une collection où récupérer un exemple de vol à tester
# --------------------------------------------------------------
flight_data = db.test_col.find_one({}, {"_id": 0})
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
        print("==================================================")
        print(f"---> retard_pred = {formatted_retard}")
        print("==================================================")
    except Exception as e:
        error_message = f"Erreur lors de la prédiction: {str(e)}"
        print(error_message)   

else:
    error_message = "Aucune donnée de vol trouvée dans la base de données."
    print(error_message)

print('\n\n')
print(flight_data)