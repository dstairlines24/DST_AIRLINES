from flask import Flask, request, jsonify, render_template, redirect, url_for
from pymongo import MongoClient
from datetime import datetime
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
    print("Form data:", request.form)
    #Récupération informations entrées par l'utilisateur
    flight_number = request.form['flight_number']
    flight_date = request.form['flight_date']

    #Supprimer la collection si existante
    db.flight_infos_results.drop()

    #Requête API pour informations du vol (aviationstack)
    flight_info = api_requests.get_flight_infos_AS(flight_number)
    #Récupération du vol à la date spécifiée
    if flight_info and 'data' in flight_info:
        # Filtrer les vols pour ne garder que celui à la date spécifiée (cas où il y a plusieurs vols avec le même n°)
        filtered_flights = [flight for flight in flight_info['data'] if flight['flight_date'] == flight_date]

        if filtered_flights:
            #Insertion de la réponse dans MongoDB, dans la collection : "flight_infos_results"
            db.flight_infos_results.insert_many(filtered_flights)
            message = f"{len(filtered_flights)} résultats de vols insérés dans la base de données."
            print(message)

            #Requête API pour airports (LHOpenAPI)
            airport_dep = api_requests.get_airport_LH(filtered_flights[0]['departure']['iata'])
            airport_arr = api_requests.get_airport_LH(filtered_flights[0]['arrival']['iata'])
            # print("Données de l'aéroport de départ :", airport_dep)
            # print("Données de l'aéroport d'arrivée :", airport_arr)

            if airport_dep and airport_dep:
                #Insertion des Latitude,Longitude dans notre collection
                db.flight_infos_results.update_many(
                { "departure.iata": filtered_flights[0]['departure']['iata'] },
                { 
                    "$set": { 
                        "departure.latitude": airport_dep['AirportResource']['Airports']['Airport']['Position']['Coordinate']['Latitude'], 
                        "departure.longitude": airport_dep['AirportResource']['Airports']['Airport']['Position']['Coordinate']['Longitude']
                    } 
                }
                )
                db.flight_infos_results.update_many(
                { "departure.iata": filtered_flights[0]['departure']['iata'] },
                { 
                    "$set": { 
                        "arrival.latitude": airport_arr['AirportResource']['Airports']['Airport']['Position']['Coordinate']['Latitude'], 
                        "arrival.longitude": airport_arr['AirportResource']['Airports']['Airport']['Position']['Coordinate']['Longitude']
                    } 
                }
                )

                # Rediriger vers la route pour afficher la carte avec les positions
                return redirect(url_for('display_positions'))

            else:
                return jsonify({"error": "Aucun aeroport trouvé sur l'API LH."}), 404
        else:
            return jsonify({"error": "Aucun vol trouvé pour cette date."}), 404
    else:
        return jsonify({"error": "Aucun vol trouvé ou problème avec l'API.", "status_code": flight_info.status_code}), 404

@app.route('/map')
def display_positions():
    # Récupérer le vol depuis MongoDB
    flight_data = db.flight_infos_results.find_one({}, {"_id": 0})  # Ne pas inclure l'_id dans la réponse

    if flight_data:
        return render_template('map.html', flight_data=flight_data)
    else:
        return jsonify({"error": "Aucune donnée de vol trouvée dans la base de données."}), 404


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
