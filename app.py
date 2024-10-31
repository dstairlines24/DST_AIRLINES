from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, stream_with_context, abort, session, flash, get_flashed_messages, send_file
from pymongo import MongoClient
from datetime import datetime
from functools import wraps
from werkzeug.security import check_password_hash  # Pour vérifier les mots de passe
from functions.api_requests import APIRequests
from functions.functions import FlightProcessor, FlightDataError
import subprocess
import os
import joblib
import pandas as pd
import numpy as np


app = Flask(__name__)

# Ajoutez une clé secrète pour la session
app.secret_key = os.getenv("FLASK_SECRET_KEY", "votre_cle_secrete_par_defaut")

# Récupérer l'URI de MongoDB depuis la variable d'environnement
mongo_uri = os.getenv("MONGO_URI")

# Connexion à MongoDB
client = MongoClient(mongo_uri)
db = client.app_data

api_requests = APIRequests()  # Créer une instance de la classe APIRequests
flightprocessor = FlightProcessor() # Créer une instance de la classe FlightProcessor

# Middleware pour vérifier le rôle de l'utilisateur
def check_role(required_role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'role' not in session:
                return redirect(url_for('login'))
            if session['role'] != required_role and session['role'] != 'admin':
                abort(403)  # Accès refusé si le rôle ne correspond pas
            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Récupérer l'utilisateur de la base de données
        user = db.users.find_one({"username": username})
        
        # Vérifier les identifiants et le mot de passe
        if user and check_password_hash(user['password'], password):  # Le mot de passe doit être hashé et stocké
            session['username'] = username
            session['role'] = user['role']  # Stockez le rôle dans la session ('user' ou 'admin')
            return redirect(url_for('index'))
        else:
            return "Identifiant ou mot de passe incorrect", 401
    return render_template('login.html')  # Page de connexion

@app.route('/logout')
def logout():
    session.clear()  # Effacer la session
    return redirect(url_for('login'))

@app.route('/')
@check_role('user')
def index():
    return render_template('index.html')

@app.route('/submit_flight_number', methods=['POST'])
@check_role('user')
def submit_flight_number():
    print("Form data:", request.form)
    #Récupération informations entrées par l'utilisateur
    flight_number = request.form['flight_number']
    flight_date = request.form['flight_date']

    #Supprimer la collection si existante
    db.form_flight_infos.drop()

    #Requête API pour informations du vol (aviationstack)
    flight_info = api_requests.get_flight_infos_AS(flight_number)

    #Récupération du vol à la date spécifiée
    if flight_info and 'data' in flight_info:
        # Filtrer les vols pour ne garder que celui à la date spécifiée (cas où il y a plusieurs vols avec le même n°)
        flight_infos_filtered = [flight for flight in flight_info['data'] if flight['flight_date'] == flight_date]

        if flight_infos_filtered:
            flight_infos_processed = flightprocessor.process_flight_AS_list(flight_infos_filtered, db.form_flight_infos)

            # Résumé des opérations
            print(f"{flight_infos_processed['vols traités']} vols traités et insérés dans la base de données.")
            if flight_infos_processed["vols échoués"]:
                failed_flight = flight_infos_processed["details échecs"][0]
                flight_info = failed_flight["flight"].get("flight", {}).get("iata", "Inconnu")
                error_message = failed_flight["error"]
                flash(f"Erreur pour le vol {flight_info} : {error_message}", "error")
                return redirect(url_for('index')) 

            return redirect(url_for('display_positions'))
        else:
            return jsonify({"error": "Aucun vol trouvé pour cette date."}), 404
    else:
        return jsonify({"error": "Aucun vol trouvé ou problème API AS", "details":flight_info})


@app.route('/submit_flight_details', methods=['POST'])
@check_role('user')
def submit_flight_details():
    flight_date = request.form['flight_date']
    flight_time = request.form.get('flight_time', 'Non spécifié')
    departure_airport = request.form['departure_airport']
    arrival_airport = request.form['arrival_airport']
    action = request.form['action']

    #Si l'utilisateur clique sur "afficher la liste des vols"
    if action == 'list_flights':
        #Supprimer la collection si existante
        db.form_flights_list.drop()
        # Utiliser la classe API pour obtenir les informations sur les vols
        flights_list = api_requests.get_flights_list_LH(departure_airport, arrival_airport, flight_date)

        if flights_list and 'FlightInformation' in flights_list and 'Flights' in flights_list['FlightInformation']:
            flights_list_l = flights_list['FlightInformation']['Flights']['Flight']
            db.form_flights_list.insert_many(flights_list_l)
            message = f"{len(flights_list_l)} résultats de vols insérés dans la base de données."
            print(message)

            # Rediriger vers la route pour afficher les résultats
            return redirect(url_for('display_flights_list'))
        else:
            return jsonify({"error": "Aucun vol trouvé ou problème avec l'API LH.", "details":flights_list})

    #Si l'utilisateur clique sur "simuler mon itinéraire"
    elif action == 'simulate_itinerary':
        print(f"Simulation d'itinéraire pour le {flight_date} entre {departure_airport} et {arrival_airport}.")
        # Si aucune heure n'est fournie, on utilise une heure par défaut (00:00:00)
        if flight_time:
            # Combiner la date et l'heure
            combined_datetime_str = f"{flight_date}T{flight_time}:00"  # Ex: "2024-10-18T14:30:00"
        else:
            # Si pas d'heure, on utilise minuit comme heure par défaut
            combined_datetime_str = f"{flight_date}T00:00:00"  # Ex: "2024-10-18T00:00:00"

        # Convertir en objet datetime et formater au format souhaité
        formatted_datetime = datetime.fromisoformat(combined_datetime_str).strftime("%Y-%m-%dT%H:%M:%S")

        flight_infos_simulated = {
            'flight_date': flight_date,
            'flight_status': '',
            'departure': {
                'airport': departure_airport,
                'timezone': '',
                'iata': departure_airport,
                'icao': '',
                'terminal': '',
                'gate': '',
                'delay': '',
                'scheduled': formatted_datetime,
                'estimated': formatted_datetime,
                'actual': formatted_datetime,
                'estimated_runway': formatted_datetime,
                'actual_runway': formatted_datetime
            },
            'arrival': {
                'airport': arrival_airport,
                'timezone': '',
                'iata': arrival_airport,
                'icao': '',
                'terminal': '',
                'gate': '',
                'delay': '',
                'scheduled': formatted_datetime,
                'estimated':formatted_datetime,
                'actual': formatted_datetime,
                'estimated_runway': formatted_datetime,
                'actual_runway': formatted_datetime
            },
            'airline': {
                'name': '',
                'iata': '',
                'icao': ''
            },
            'flight': {
                'number': '',
                'iata': '',
                'icao': '',
                'codeshared': ''
            },
            'aircraft': {
                'registration': '',
                'iata': '',
                'icao': '',
                'icao24': ''
            }
        }

        db.form_flight_infos.drop()
        try:
            flight_infos_processed = flightprocessor.process_flight_AS(flight_infos_simulated)
            if flight_infos_processed:
                # Insérer le vol traité dans la collection MongoDB
                db.form_flight_infos.insert_one(flight_infos_processed)

                print(f"Vol {flight_infos_processed['flight']['iata']} traité et inséré.")
                return redirect(url_for('display_positions'))
            
        except FlightDataError as e:
            error_message = f"Erreur lors du traitement du vol : {e}"
            print(error_message)
            flash(error_message, 'error')  # Envoie le message d'erreur sur la page html
            return redirect(url_for('index')) 

    return redirect(url_for('index'))

@app.route('/map')
@check_role('user')
def display_positions():
    # Récupérer le vol depuis MongoDB
    flight_data = db.form_flight_infos.find_one({}, {"_id": 0})  # Ne pas inclure l'_id dans la réponse

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

            print(f"retard_pred = {formatted_retard}")
            
            return render_template('map.html', flight_data=flight_data, retard_pred=formatted_retard)
        except Exception as e:
            error_message = f"Erreur lors de la prédiction: {str(e)}"
            flash(error_message, 'error')  # Envoie le message d'erreur sur la page html       
            return jsonify({"error": f"Erreur lors de la prédiction: {str(e)}"}), 500    
        
    else:
        error_message = "Aucune donnée de vol trouvée dans la base de données."
        flash(error_message, 'error')  # Envoie le message d'erreur sur la page html
        return jsonify({"error": "Aucune donnée de vol trouvée dans la base de données."}), 404

@app.route('/flights')
@check_role('user')
def display_flights_list():
    # Récupérer les données de la collection MongoDB
    flights = list(db.form_flights_list.find())

    return render_template('flights.html', flights=flights)

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
    
    # Extraction de la première entrée dans la liste "data" de `flight_data`
    flight_info = flight_data

    #--------------------------
    # Mise en forme des données
    #--------------------------
    print(f"flight_info : {flight_info}")
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
    print(f"input_data : {input_data}")

    # Application du pipeline de prétraitement
    processed_input = best_model.named_steps['preprocessor'].transform(input_data)
    print(f"processed_input : {processed_input}")

    # Transformation en DF
    processed_input_df = pd.DataFrame(processed_input, columns=input_data.columns)

    # Prédiction avec le modèle
    prediction = best_model.predict(processed_input_df)
    return prediction[0]


# Route Flask pour les prédictions via POST
@app.route('/predict', methods=['POST'])
@check_role('user')
def predict():
    try:
        # Vérification que les données sont envoyées en JSON
        flight_data = request.get_json()
        if not flight_data or "data" not in flight_data or not flight_data["data"]:
            return jsonify({"error": "Données de vol non fournies ou invalides"}), 400

        # Appel de la fonction de prédiction directe
        prediction = predict_from_data(flight_data)
        print(f"prediction : {prediction}")
        return jsonify({"prediction": prediction}), 200

    except Exception as e:
        return jsonify({"error": f"Erreur lors de la prédiction: {str(e)}"}), 500




@app.route("/get_data/<db_name>/<col_name>")
@check_role('admin')
def get_data(db_name, col_name):
    # Vérifier si la base de données existe
    if db_name in client.list_database_names():
        # Accéder à la base de données
        db_show = client[db_name]

        # Vérifier si la collection existe
        if col_name in db_show.list_collection_names():
            # Accéder à la collection
            collection = db_show[col_name]

            # Récupérer tous les documents dans la collection
            documents = list(collection.find({}, {"_id": 0}))  # On exclut l'ID MongoDB (_id)

            # Vérifier s'il y a des documents à afficher
            if documents:
                return jsonify({"data": documents}), 200  # Retourner les documents en format JSON
            else:
                return jsonify({"error": "Aucun document trouvé dans la collection."}), 404
        else:
            return jsonify({"error": "Collection introuvable."}), 404
    else:
        return jsonify({"error": "Base de données introuvable."}), 404
    
# Sous-répertoire où les fichiers sont situés
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), 'scripts')

@app.route('/run_script/<script_name>', methods=['GET', 'POST'])
@check_role('admin')
def run_script(script_name):
    # Vérifie que le fichier a une extension .py pour limiter l'exécution aux scripts Python
    if not script_name.endswith('.py'):
        return jsonify({'status': 'error', 'error': 'Invalid script extension'}), 400

    # Chemin complet du script à exécuter
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    
    # Vérifie si le fichier existe dans le sous-répertoire
    if not os.path.isfile(script_path):
        return jsonify({'status': 'error', 'error': 'Script not found'}), 404

    # Créez un générateur pour streamer la sortie en temps réel
    def generate():
        # Exécutez le script en utilisant subprocess et capturez stdout ligne par ligne
        process = subprocess.Popen(['python3', '-u', script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        # Itérez sur la sortie ligne par ligne
        for line in iter(process.stdout.readline, ''):
            yield line  # Envoyer la sortie en direct au client
            
        process.stdout.close()
        process.wait()  # Attendez que le processus se termine

    # Exécuter le script
    response = Response(stream_with_context(generate()), mimetype='text/plain')

    return response


@app.route('/run_script_graph/<script_name>', methods=['GET', 'POST'])
@check_role('admin')
def run_script_graph(script_name):
    # Vérifie que le fichier a une extension .py pour limiter l'exécution aux scripts Python
    if not script_name.endswith('.py'):
        return jsonify({'status': 'error', 'error': 'Invalid script extension'}), 400

    # Chemin complet du script à exécuter
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    
    # Vérifie si le fichier existe dans le sous-répertoire
    if not os.path.isfile(script_path):
        return jsonify({'status': 'error', 'error': 'Script not found'}), 404
    
    # Exécutez le script en utilisant subprocess et capturez stdout ligne par ligne
    process = subprocess.Popen(['python3', '-u', script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
    # Exécute le script et capture la sortie dans une variable pour l'inclure dans la réponse HTML
    output = ""

    # Lire la sortie du processus et la stocker dans `output`
    for line in iter(process.stdout.readline, ''):
        output += line  # Ajouter chaque ligne à la chaîne
    process.stdout.close()
    process.wait()  # Attend la fin du processus

    #Si la sortie contient un graphique
    if os.path.exists('output.png'):
        # Construire la réponse HTML avec l'image intégrée
        response_content = f"<html><body><pre>{output}</pre>"
        response_content += '<br><img src="/display_image" alt="Graphique généré" />'
        response_content += "</body></html>"

        # Suppression de l'image du graphique
        # os.remove('output.png')

    # Retourne le contenu HTML complet
    return Response(response_content, mimetype='text/html')

@app.route('/display_image')
def display_image():
    """Route pour afficher l'image générée."""
    response = send_file('output.png', mimetype='image/png')
    os.remove('output.png')  # Supprimer l'image après l'envoi
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

