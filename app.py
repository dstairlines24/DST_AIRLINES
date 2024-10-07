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

@app.route('/submit_flight_info', methods=['POST'])
def submit_flight_info():
    # Récupérer les données du formulaire
    flight_number = request.form['flight_number']
    flight_date = request.form['flight_date']
    flight_time = request.form['flight_time']
    departure_airport = request.form['departure_airport']
    arrival_airport = request.form['arrival_airport']

    # Traitement ou affichage des données récupérées
    print(f"Vol : {flight_number}")
    print(f"Date : {flight_date}")
    print(f"Heure : {flight_time}")
    print(f"Aéroport de départ : {departure_airport}")
    print(f"Aéroport d'arrivée : {arrival_airport}")

    # Retourner une réponse à l'utilisateur
    return f"""
        <h3>Informations du vol soumises :</h3>
        <p><strong>N° de vol :</strong> {flight_number}</p>
        <p><strong>Date :</strong> {flight_date}</p>
        <p><strong>Heure :</strong> {flight_time}</p>
        <p><strong>Aéroport de départ :</strong> {departure_airport}</p>
        <p><strong>Aéroport d'arrivée :</strong> {arrival_airport}</p>
        <br>
        <a href="/">Retour à la carte</a>
    """

if __name__ == "__main__":
    app.run(debug=True)