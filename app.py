from flask import Flask, request, jsonify, render_template, redirect, url_for
from pymongo import MongoClient
from api_requests import APIRequests  # Importer la classe API

app = Flask(__name__)

# Connexion à MongoDB
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.app_data

api_requests = APIRequests()  # Créer une instance de la classe APIRequests

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit_flight_number', methods=['POST'])
def submit_flight_number():
    flight_number = request.form['flight_number']
    print(f"N° de vol soumis : {flight_number}")
    #Supprimer la collection si existante
    db.flight_infos_results.drop()
    flight_info = api_requests.get_flight_infos_AS(flight_number)
    if flight_info and 'data' in flight_info:
        db.flight_infos_results.insert_many(flight_info['data'])
        message = f"{len(flight_info['data'])} résultats de vols insérés dans la base de données."
        print(message)

        #---------Requête airports sur LHOpenAPI
        airport_dep = get_airport_LH(flight_info['data'][0]['departure']['iata'])
        airport_arr = get_airport_LH(flight_info['data'][0]['arrival']['iata'])
        #Insertion des Latitude,Longitude dans notre collection
        db.flight_infos_results.updateOne(
            {"_id":ObjectId("56d5f7eb604eb380b0d8d9c8")},
            {$push: {"scores" :  {"exam": "quizz" , "score": 100.0}}}
        )

        # Extraire les infos des aéroports de départ et d'arrivée
        flight_data = flight_info['data'][0]  # On prend le premier vol trouvé
        departure_airport = flight_data['departure']
        arrival_airport = flight_data['arrival']
        
        # Créer un objet avec les informations à retourner
        airports_data = {
            "departure": {
                "airport_name": departure_airport['airport'],
                "airport_iata": departure_airport['iata'],
                "latitude": departure_airport['Latitude'],
                "longitude": departure_airport['Longitude']
            },
            "arrival": {
                "airport_name": arrival_airport['name'],
                "airport_iata": arrival_airport['iata'],
                "latitude": arrival_airport['Latitude'],
                "longitude": arrival_airport['Longitude']
            }
        }
        # Retourner les informations des aéroports sous forme de JSON
        return jsonify(airports_data)


    else:
        return jsonify({"error": "Aucun vol trouvé ou problème avec l'API.", "status_code": flight_info.status_code}), 404

@app.route('/submit_flight_details', methods=['POST'])
def submit_flight_details():
    flight_date = request.form['flight_date']
    flight_time = request.form.get('flight_time', 'Non spécifié')
    departure_airport = request.form['departure_airport']
    arrival_airport = request.form['arrival_airport']
    action = request.form['action']

    if action == 'list_flights':
        #Supprimer la collection si existante
        db.flights_list_results.drop()
        # Utiliser la classe API pour obtenir les informations sur les vols
        flights_list = api_requests.get_flights_list_LH(departure_airport, arrival_airport, flight_date)

        if flights_list and 'FlightInformation' in flights_list and 'Flights' in flights_list['FlightInformation']:
            flights_list_l = flights_list['FlightInformation']['Flights']['Flight']
            db.flights_list_results.insert_many(flights_list_l)
            message = f"{len(flights_list_l)} résultats de vols insérés dans la base de données."
            print(message)

            # Rediriger vers la route pour afficher les résultats
            return redirect(url_for('display_flights_list'))
        
        else:
            return jsonify({"error": "Aucun vol trouvé ou problème avec l'API.", "status_code": flights_list.status_code}), 404

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
def display_flights_list():
    # Récupérer les données de la collection MongoDB
    flights = list(db.flights_list_results.find())

    return render_template('flights.html', flights=flights)

if __name__ == "__main__":
    app.run(debug=True)
