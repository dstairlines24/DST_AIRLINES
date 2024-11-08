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
from functools import wraps



app = Flask(__name__)
# Utiliser une variable d'environnement pour stocker la clé API de manière sécurisée
app.config['API_KEY'] = os.getenv("API_KEY", "api_key_dstairlines_default")

# Ajoutez une clé secrète pour la session
app.secret_key = os.getenv("FLASK_SECRET_KEY", "secret_key_dstairlines_default")

# Récupérer l'URI de MongoDB depuis la variable d'environnement
mongo_uri = os.getenv("MONGO_URI")

# Connexion à MongoDB
client = MongoClient(mongo_uri)
db = client.app_data
db_credentials = client.app_credentials

api_requests = APIRequests()  # Créer une instance de la classe APIRequests
flightprocessor = FlightProcessor() # Créer une instance de la classe FlightProcessor

# Décorateur pour vérifier la clé API
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Récupération de la clé API depuis les en-têtes
        api_key = request.headers.get('x-api-key')
        if not api_key or api_key != app.config['API_KEY']:
            return jsonify({"error": "Clé API manquante ou invalide"}), 401
        return f(*args, **kwargs)
    return decorated_function

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
        user = db_credentials.users.find_one({"username": username})
        
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
def index():
    return render_template('index.html')

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
    try:
        prediction = best_model.predict(processed_input_df)
        return prediction[0]
    except Exception as e:
        print(f"Erreur lors de la prédiction : {e}")
        raise ValueError("Erreur lors de la prédiction avec le modèle.")


# Route Flask pour les prédictions via POST
@app.route('/predict', methods=['POST'])
@require_api_key
def predict():
    try:
        # Vérification que les données sont envoyées en JSON
        flight_data = request.get_json()
        if not flight_data:
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
    # Interdire l'accès à la BDD des credentials
    if db_name == "app_credentials":
        return jsonify({"error": "Accès interdit."}), 403
    
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
    response_content = f"<html><body><pre>{output}</pre>"
    if os.path.exists('output.png') and os.path.exists('feature_importances.png'):
        response_content += '<br><img src="/display_image/output" alt="Graphique Prédictions vs Réel" />'
        response_content += '<br><img src="/display_image/importance" alt="Graphique Importance des caractéristiques" />'
    response_content += "</body></html>"

    # Suppression de l'image du graphique
    # os.remove('output.png')
    # Retourne le contenu HTML complet
    return Response(response_content, mimetype='text/html')

@app.route('/display_image/<image_type>')
def display_image(image_type):
    image_file = 'output.png' if image_type == 'output' else 'feature_importances.png'
    response = send_file(image_file, mimetype='image/png')
    os.remove(image_file)
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

