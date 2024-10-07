from flask import Flask, jsonify, render_template
from pymongo import MongoClient

app = Flask(__name__)

# Connexion à MongoDB
# client = MongoClient("mongodb://dstairlines:dstairlines@localhost:27017/")
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.airport_data

@app.route('/airports', methods=['GET'])
def get_airports():
    # Récupérer les aéroports depuis MongoDB
    airports = list(db.airports.find({}, {"_id": 0}))  # Ne pas inclure l'_id
    return jsonify(airports)

@app.route('/')
def index():
    return render_template('index.html')

# Route pour soumettre le N° de vol
@app.route('/submit_flight_number', methods=['POST'])
def submit_flight_number():
    flight_number = request.form['flight_number']

    # Traitement du N° de vol (par exemple, recherche des infos du vol via une API)
    print(f"N° de vol soumis : {flight_number}")

    # Retourner une réponse simple ou rediriger vers une autre page avec les détails
    return f"""
        <h3>Informations du vol soumises :</h3>
        <p><strong>N° de vol :</strong> {flight_number}</p>
        <br>
        <a href="/">Retour</a>
    """

# Route pour soumettre les autres informations du vol
@app.route('/submit_flight_details', methods=['POST'])
def submit_flight_details():
    flight_date = request.form['flight_date']
    flight_time = request.form.get('flight_time', 'Non spécifié')
    departure_airport = request.form['departure_airport']
    arrival_airport = request.form['arrival_airport']
    action = request.form['action']  # Détecter quel bouton a été cliqué

    # Si l'utilisateur a cliqué sur "Afficher la liste des vols"
    if action == 'list_flights':
        print(f"Afficher les vols pour le {flight_date} entre {departure_airport} et {arrival_airport}.")
        # Logique pour afficher la liste des vols
        return f"""
            <h3>Liste des vols disponibles :</h3>
            <p>Recherche de vols pour le {flight_date} entre {departure_airport} et {arrival_airport}.</p>
            <br>
            <a href="/">Retour</a>
        """
    
    # Si l'utilisateur a cliqué sur "Simuler mon itinéraire"
    elif action == 'simulate_itinerary':
        print(f"Simulation d'itinéraire pour le {flight_date} entre {departure_airport} et {arrival_airport}.")
        # Logique pour simuler l'itinéraire
        return f"""
            <h3>Simulation de votre itinéraire :</h3>
            <p>Itinéraire simulé pour le vol du {flight_date} ({flight_time}) de {departure_airport} à {arrival_airport}.</p>
            <br>
            <a href="/">Retour</a>
        """

if __name__ == "__main__":
    app.run(debug=True)