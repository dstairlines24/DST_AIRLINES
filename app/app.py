from flask import Flask, request, jsonify, render_template, redirect, url_for, abort, session
from pymongo import MongoClient
from functools import wraps
from werkzeug.security import check_password_hash  # Pour vérifier les mots de passe
import os
import joblib
import pandas as pd
from functools import wraps
from flasgger import Swagger, swag_from


app = Flask(__name__)
# Utiliser une variable d'environnement pour stocker la clé API de manière sécurisée
app.config['API_KEY'] = os.getenv("API_KEY", "api_key_dstairlines_default")

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

# Décorateur pour vérifier la clé API
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Récupération de la clé API depuis les en-têtes
        api_key = request.headers.get('x-api-key')
        # api_key = request.headers.get('HTTP_X-API-KEY')
        print(f"Clé API reçue : {api_key}")  # Débogage
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

    #==========================================================
    # Appliquer les transformation avec la classe DataTransform
    #==========================================================
    from ml_data_transform import DataTransform
    datatransform = DataTransform(df)
    df = datatransform.apply_feat_transforms()
    
    #==========================================================
    # Séparation du Dataset
    #==========================================================
    # Filtrer les colonnes qui nous intéressent pour l'entraînement
    features = [col for col in df.columns if 'feat_' in col]

    # Créer un DataFrame pour les données de prédiction
    input_data = df[features]
    print(f"input_data : {input_data}")

    #==========================================================
    # Application du preprocessing (pipeline du modèle)
    #==========================================================
    processed_input = best_model.named_steps['preprocessor'].transform(input_data)
    print(f"processed_input : {processed_input}")

    # Transformation en DF
    processed_input_df = pd.DataFrame(processed_input, columns=input_data.columns)

    #==========================================================
    # Prédiction avec le modèle
    #==========================================================
    try:
        prediction = best_model.predict(processed_input_df)
        return prediction[0]
    except Exception as e:
        print(f"Erreur lors de la prédiction : {e}")
        raise ValueError("Erreur lors de la prédiction avec le modèle.")


# Route Flask pour les prédictions via POST
@app.route('/predict', methods=['POST'])
@require_api_key
@swag_from({
    'tags': ['Prediction'],
    'parameters': [
        {
            'name': 'flight_data',
            'in': 'body',
            'type': 'json',
            'required': True,
            'description': 'Données de vol pour la prédiction'
        }
    ],
    'responses': {
        200: {
            'description': 'Prédiction réussie',
            'schema': {
                'type': 'object',
                'properties': {
                    'prediction': {
                        'type': 'string'
                    }
                }
            }
        },
        400: {
            'description': 'Données de vol non fournies ou invalides'
        },
        401: {
            'description': 'Clé API manquante ou invalide'
        },
        500: {
            'description': 'Erreur lors de la prédiction'
        }
    }
}) 
def predict():
    try:
        # Vérification que les données sont envoyées en JSON
        flight_data = request.get_json()
        if not flight_data:
            return jsonify({"error": "Données de vol non fournies ou invalides"}), 400

        print(f"flight_data: {flight_data}")  # Débogage
        # Appel de la fonction de prédiction directe
        prediction = predict_from_data(flight_data)
        print(f"prediction : {prediction}")
        print(f"Prediction obtenue : {prediction}")  # Débogage
        return jsonify({"prediction": prediction}), 200

    except Exception as e:
        print(f"Erreur dans la prédiction: {str(e)}")  # Débogage
        return jsonify({"error": f"Erreur lors de la prédiction: {str(e)}"}), 500
    

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5002)

