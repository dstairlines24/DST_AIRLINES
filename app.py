from flask import Flask, request, jsonify, render_template, redirect, url_for
from pymongo import MongoClient
from api_requests import APIRequests  # Importer la classe API

app = Flask(__name__)

# Connexion à MongoDB
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.airport_data

api_requests = APIRequests()  # Créer une instance de la classe APIRequests

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit_flight_number', methods=['POST'])
def submit_flight_number():
    flight_number = request.form['flight_number']
    print(f"N° de vol soumis : {flight_number}")
    return f"""
        <h3>Informations du vol soumises :</h3>
        <p><strong>N° de vol :</strong> {flight_number}</p>
        <br>
        <a href="/">Retour</a>
    """

@app.route('/submit_flight_details', methods=['POST'])
def submit_flight_details():
    flight_date = request.form['flight_date']
    flight_time = request.form.get('flight_time', 'Non spécifié')
    departure_airport = request.form['departure_airport']
    arrival_airport = request.form['arrival_airport']
    action = request.form['action']

    if action == 'list_flights':
        #Supprimer la collection si existante
        db.flight_search_results.drop()
        # Utiliser la classe API pour obtenir les informations sur les vols
        flight_data = api_requests.get_flight_information(departure_airport, arrival_airport, flight_date)

        if flight_data and 'FlightInformation' in flight_data and 'Flights' in flight_data['FlightInformation']:
            flights = flight_data['FlightInformation']['Flights']['Flight']
            db.flight_search_results.insert_many(flights)
            message = f"{len(flights)} résultats de vols insérés dans la base de données."
            print(message)

            # Rediriger vers la route pour afficher les résultats
            return redirect(url_for('display_flights'))
        
        else:
            return jsonify({"error": "Aucun vol trouvé ou problème avec l'API.", "status_code": response.status_code}), 404

    elif action == 'simulate_itinerary':
        print(f"Simulation d'itinéraire pour le {flight_date} entre {departure_airport} et {arrival_airport}.")
        return f"""
            <h3>Simulation de votre itinéraire :</h3>
            <p>Itinéraire simulé pour le vol du {flight_date} ({flight_time}) de {departure_airport} à {arrival_airport}.</p>
            <br>
            <a href="/">Retour</a>
        """
    
    return redirect(url_for('index'))

@app.route('/flights')
def display_flights():
    # Récupérer les données de la collection MongoDB
    flights = list(db.flight_search_results.find())

    return render_template('flights.html', flights=flights)

if __name__ == "__main__":
    app.run(debug=True)
