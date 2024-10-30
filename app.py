from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, stream_with_context, abort, session
from pymongo import MongoClient
from datetime import datetime
from functools import wraps
from werkzeug.security import check_password_hash  # Pour vérifier les mots de passe
from functions.api_requests import APIRequests
from functions.functions import FlightProcessor, FlightDataError
import subprocess
import os

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
                print(f"{flight_infos_processed['vols échoués']} vols ont échoué et n'ont pas été insérés.")

            return redirect(url_for('display_positions'))
        
        else:
            return jsonify({"error": "Aucun vol trouvé pour cette date."}), 404
    else:
        return jsonify({"error": "Aucun vol trouvé ou problème API AS", "details":flight_info})


@app.route('/map')
@check_role('user')
def display_positions():
    # Récupérer le vol depuis MongoDB
    flight_data = db.form_flight_infos.find_one({}, {"_id": 0})  # Ne pas inclure l'_id dans la réponse

    if flight_data:
        return render_template('map.html', flight_data=flight_data)
    else:
        return jsonify({"error": "Aucune donnée de vol trouvée dans la base de données."}), 404


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
            print(f"Erreur lors du traitement du vol {flight_infos_simulated.get('flight', {}).get('iata')}: {e}")

    return redirect(url_for('index'))

@app.route('/flights')
@check_role('user')
def display_flights_list():
    # Récupérer les données de la collection MongoDB
    flights = list(db.form_flights_list.find())

    return render_template('flights.html', flights=flights)

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

    return Response(stream_with_context(generate()), mimetype='text/plain')

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

