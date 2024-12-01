import pytest
from app import app, db_credentials, predict_from_data
from flask import session
from werkzeug.security import generate_password_hash
import os
from pymongo import MongoClient


@pytest.fixture
def client():
    with app.test_client() as client:
        with app.app_context():
            # Ajouter des données de test pour les utilisateurs
            db_credentials.users.insert_one({
                "username": "testuser",
                "password": generate_password_hash("testpassword"),
                "role": "user"
            })
        yield client
        # Nettoyer après les tests
        db_credentials.users.delete_many({})

def test_login_success(client):
    """Test de connexion réussie avec un utilisateur valide"""
    response = client.post('/login', data={'username': 'testuser', 'password': 'testpassword'})
    assert response.status_code == 302  # Redirection vers la page d'accueil
    assert session['username'] == 'testuser'

def test_login_failure(client):
    """Test de connexion échouée avec des identifiants incorrects"""
    response = client.post('/login', data={'username': 'testuser', 'password': 'wrongpassword'})
    assert response.status_code == 401  # Identifiants incorrects
    assert b"Identifiant ou mot de passe incorrect" in response.data

def test_logout(client):
    """Test de déconnexion"""
    with client.session_transaction() as sess:
        sess['username'] = 'testuser'
        sess['role'] = 'user'
    response = client.get('/logout')
    assert response.status_code == 302  # Redirection vers la page de connexion
    assert 'username' not in session

def test_index(client):
    """Test de la page d'accueil"""
    response = client.get('/')
    assert response.status_code == 200

def test_predict_success(client, monkeypatch):
    """Test de prédiction réussie avec des données valides"""

    # def mock_predict_from_data(flight_data):
    #     return "prediction_success"

    # monkeypatch.setattr('app.predict_from_data', mock_predict_from_data)

    # Ajout d'une clé API valide
    # client.environ_base['HTTP_X-API-KEY'] = app.config['API_KEY']

    # Récupérer l'URI de MongoDB depuis la variable d'environnement
    mongo_uri = os.getenv("MONGO_URI")

    # Connexion à MongoDB
    clientMongo = MongoClient(mongo_uri)
    db = clientMongo.app_data_form

    flight_data = list(db['test_col'].find({}, {"_id": 0}))
    # --------------------------------------------------------------

    print(f"Contenu de flight_data : \n{flight_data}\n") # Deboggage
    print("\n\n")

    headers = {
        'x-api-key': app.config['API_KEY']
    }

    response = client.post('/predict', json=flight_data, headers=headers)
    assert response.status_code == 200
    assert response.json['prediction'] == 'prediction_success'

def test_predict_missing_data(client):
    """Test de prédiction avec des données manquantes"""
    print(f"app.config['API_KEY']: {app.config['API_KEY']}")  # Deboggage
    # client.environ_base['HTTP_X-API-KEY'] = app.config['API_KEY']
    # print(f"En-têtes envoyés: {client.environ_base}")  # Deboggage

    headers = {
        'x-api-key': app.config['API_KEY']
    }

    response = client.post('/predict', json={}, headers=headers)
    assert response.status_code == 400
    assert response.json['error'] == 'Données de vol non fournies ou invalides'
    # error_message = response.json.get('error')  # Utiliser .json pour décoder la réponse JSON
    # assert error_message == 'Données de vol non fournies ou invalides'

def test_predict_missing_api_key(client):
    """Test de prédiction avec une clé API manquante"""
    response = client.post('/predict', json={'feat_1': 0.5, 'feat_2': 0.8})
    assert response.status_code == 401
    error_message = response.json.get('error')  # Utiliser .json pour décoder la réponse JSON
    assert error_message == 'Clé API manquante ou invalide'

def test_predict_internal_error(client, monkeypatch):
    """Test de prédiction échouée avec une erreur interne"""

    def mock_predict_from_data(flight_data):
        raise ValueError("Erreur de prédiction")

    monkeypatch.setattr('app.predict_from_data', mock_predict_from_data)
    client.environ_base['HTTP_X-API-KEY'] = app.config['API_KEY']

    response = client.post('/predict', json={'feat_1': 0.5, 'feat_2': 0.8})
    assert response.status_code == 500
    assert "Erreur lors de la prédiction" in response.get_data(as_text=True)
