from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, stream_with_context, abort, session, flash
from pymongo import MongoClient
from datetime import datetime
from functools import wraps
from werkzeug.security import check_password_hash  # Pour vérifier les mots de passe
from functions.api_requests import APIRequests
from functions.functions import FlightProcessor, FlightDataError
from flasgger import Swagger, swag_from

import subprocess
import os

import requests



app = Flask(__name__)
																			   

# Ajoutez une clé secrète pour la session
app.secret_key = os.getenv("FLASK_SECRET_KEY", "votre_cle_secrete_par_defaut2")

# Configure flasgger
swagger = Swagger(app)

# Récupérer l'URI de MongoDB depuis la variable d'environnement
mongo_uri = os.getenv("MONGO_URI")

# Connexion à MongoDB
client = MongoClient(mongo_uri)
db = client.app_data_form
db_credentials = client.app_credentials

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
@swag_from({
    'responses': {
        200: {
            'description': 'Page de connexion'
        }
    }
})
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
@swag_from({
    'responses': {
        302: {
            'description': 'Redirection vers la page de connexion'
        }
    }
})		
def logout():
    session.clear()  # Effacer la session
    return redirect(url_for('login'))

@app.route('/')
@check_role('user')
@swag_from({
    'responses': {
        200: {
            'description': 'Page d\'accueil'
        }
    }
})			
def index():
    return render_template('index.html')

@app.route('/submit_flight_number', methods=['POST'])
@check_role('user')
@swag_from({
    'parameters': [
        {
            'name': 'flight_number',
            'in': 'formData',
            'type': 'string',
            'required': True,
            'description': 'Numéro de vol à soumettre'
        }
    ],
    'responses': {
        200: {
            'description': 'Détails du vol soumis'
        },
        404: {
            'description': 'Aucun vol trouvé ou problème API AS'
        }
    }
})			
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
@swag_from({
    'parameters': [
        {
            'name': 'flight_details',
            'in': 'formData',
            'type': 'string',
            'required': True,
            'description': 'Détails du vol à soumettre'
        }
    ],
    'responses': {
        302: {
            'description': 'Redirection vers la page d\'accueil'
        }
    }
})			
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
@swag_from({
    'responses': {
        200: {
            'description': 'Carte des positions de vol'
        },
        404: {
            'description': 'Aucune donnée de vol trouvée dans la base de données.'
        }
    }
})
def display_positions():
    # Récupérer le vol depuis MongoDB
    # flight_data = db.form_flight_infos.find_one({}, {"_id": 0})  # Ne pas inclure l'_id dans la réponse
    flight_data = list(db['form_flight_infos'].find({}, {"_id": 0}))  # Ne pas inclure l'_id dans la réponse
    
    # Récupérer la clé API pour envoyer la requête
    api_key = os.getenv("API_KEY")
    url = 'http://flask_app:5002/predict'
    headers = {
    'x-api-key': api_key
    }

    if flight_data:
        try:
            # Prédiction du retard sur le vol
            response = requests.post(url, json=flight_data, headers=headers)

            # Debug : Affiche la réponse brute du serveur
            print("Statut de la réponse:", response.status_code)
            print("Contenu brut de la réponse:", response.text)

            # Tenter de décoder en JSON si le contenu est valide
            try:
                retard_pred = response.json().get('prediction')
                print("Prédiction:", retard_pred)
            except ValueError as e:
                print("Erreur lors du décodage JSON:", e)

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
@swag_from({
    'responses': {
        200: {
            'description': 'Liste des vols disponibles'
        }
    }
})			
def display_flights_list():
    # Récupérer les données de la collection MongoDB
    flights = list(db.form_flights_list.find())

    return render_template('flights.html', flights=flights)

# Sous-répertoire où les fichiers sont situés
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), 'scripts')

@app.route('/run_script/<script_name>', methods=['GET', 'POST'])
@check_role('admin')
@swag_from({
    'parameters': [
        {
            'name': 'script_name',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'Nom du script à exécuter'
        }
    ],
    'responses': {
        200: {
            'description': 'Résultat de l\'exécution du script'
        }
    }
})			
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5001)

