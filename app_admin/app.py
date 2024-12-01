from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, stream_with_context, abort, session, send_file
from pymongo import MongoClient
from functools import wraps
from werkzeug.security import check_password_hash  # Pour vérifier les mots de passe
from functions.api_requests import APIRequests
from functions.functions import FlightProcessor
import subprocess
import os
from functools import wraps
from flasgger import Swagger, swag_from


app = Flask(__name__)

# Ajoutez une clé secrète pour la session
app.secret_key = os.getenv("FLASK_SECRET_KEY", "secret_key_dstairlines_default")

# Configure flasgger
swagger = Swagger(app)		
					  
# Récupérer l'URI de MongoDB depuis la variable d'environnement
mongo_uri = os.getenv("MONGO_URI")

# Connexion à MongoDB
client = MongoClient(mongo_uri)
db = client.app_data
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
    'tags': ['Authentication'],
    'parameters': [
        {
            'name': 'username',
            'in': 'formData',
            'type': 'string',
            'required': True,
            'description': 'Nom d\'utilisateur'
        },
        {
            'name': 'password',
            'in': 'formData',
            'type': 'string',
            'required': True,
            'description': 'Mot de passe'
        }
    ],
    'responses': {
        200: {
            'description': 'Page de connexion'
        },
        401: {
            'description': 'Identifiant ou mot de passe incorrect'
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
    'tags': ['Authentication'],
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
@swag_from({
    'tags': ['General'],
    'responses': {
        200: {
            'description': 'Page d\'accueil'
        }
    }
}) 
def index():
    return render_template('index.html')

    

@app.route("/get_data/<db_name>/<col_name>")
@check_role('admin')
@swag_from({
    'tags': ['Database'],
    'parameters': [
        {
            'name': 'db_name',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'Nom de la base de données'
        },
        {
            'name': 'col_name',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'Nom de la collection'
        }
    ],
    'responses': {
        200: {
            'description': 'Données de la collection'
        },
        403: {
            'description': 'Accès interdit'
        },
        404: {
            'description': 'Base de données ou collection introuvable'
        }
    }
})
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
@swag_from({
    'tags': ['Scripts'],
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
            'description': 'Sortie du script'
        },
        400: {
            'description': 'Extension de script invalide'
        },
        404: {
            'description': 'Script introuvable'
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


@app.route('/run_script_graph/<script_name>', methods=['GET', 'POST'])
@check_role('admin')
@swag_from({
    'tags': ['Scripts'],
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
            'description': 'Sortie du script avec graphique'
        },
        400: {
            'description': 'Extension de script invalide'
        },
        404: {
            'description': 'Script introuvable'
        }
    }
}) 
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

    response_content = f"<html><body><pre>{output}</pre>"
    
    #Si la sortie contient un graphique
    if os.path.exists('output.png'):
        # Construire la réponse HTML avec l'image intégrée
        response_content += '<br><img src="/display_image" alt="Graphique généré" />'
        response_content += "</body></html>"

        # Suppression de l'image du graphique
        # os.remove('output.png')

    # Retourne le contenu HTML complet
    return Response(response_content, mimetype='text/html')

@app.route('/display_image')
@swag_from({
    'tags': ['Images'],
    'responses': {
        200: {
            'description': 'Image affichée'
        }
    }
})
def display_image():
    """Route pour afficher l'image générée."""
    response = send_file('output.png', mimetype='image/png')
    os.remove('output.png')  # Supprimer l'image après l'envoi
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

