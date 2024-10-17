from pymongo import MongoClient
from api_requests import APIRequests
import math

# Connexion à MongoDB
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.app_data

api_requests = APIRequests()

# Fonction pour récupérer les informations géographiques d'un aéroport
def get_airport_coordinates(iata_code):
    airport_info = api_requests.get_airport_LH(iata_code)
    if airport_info:
        latitude = airport_info['AirportResource']['Airports']['Airport']['Position']['Coordinate']['Latitude']
        longitude = airport_info['AirportResource']['Airports']['Airport']['Position']['Coordinate']['Longitude']
        return latitude, longitude
    return None, None

# Fonction pour calculer la distance orthodromique entre deux points (en km)
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Rayon moyen de la Terre en km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance

# Fonction pour interpoler une position sur un grand cercle
def interpolate_great_circle(lat1, lon1, lat2, lon2, fraction):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    d = haversine(math.degrees(lat1), math.degrees(lon1), math.degrees(lat2), math.degrees(lon2)) / 6371.0
    A = math.sin((1 - fraction) * d) / math.sin(d)
    B = math.sin(fraction * d) / math.sin(d)
    x = A * math.cos(lat1) * math.cos(lon1) + B * math.cos(lat2) * math.cos(lon2)
    y = A * math.cos(lat1) * math.sin(lon1) + B * math.cos(lat2) * math.sin(lon2)
    z = A * math.sin(lat1) + B * math.sin(lat2)
    new_lat = math.atan2(z, math.sqrt(x**2 + y**2))
    new_lon = math.atan2(y, x)
    return math.degrees(new_lat), math.degrees(new_lon)

# Fonction pour récupérer les informations météo pour une position donnée
def get_weather_data(lat, lon, time):
    meteo = api_requests.get_meteo(lat, lon, time)
    if meteo and 'currentConditions' in meteo:
        return {
            "temp": meteo['currentConditions'].get('temp'),
            "humidity": meteo['currentConditions'].get('humidity'),
            "precip": meteo['currentConditions'].get('precip'),
            "snow": meteo['currentConditions'].get('snow'),
            "snowdepth": meteo['currentConditions'].get('snowdepth'),
            "windspeed": meteo['currentConditions'].get('windspeed'),
            "pressure": meteo['currentConditions'].get('pressure'),
            "visibility": meteo['currentConditions'].get('visibility'),
            "cloudcover": meteo['currentConditions'].get('cloudcover'),
            "conditions": meteo['currentConditions'].get('conditions'),
            "icon": meteo['currentConditions'].get('icon')
        }
    return {}

# Fonction pour traiter un vol et obtenir les données à insérer
def process_flight(flight):
    # Vérification des données de départ et d'arrivée
    if not flight.get('departure') or not flight.get('arrival'):
        return None

    # Récupérer les informations de l'aéroport de départ
    dep_latitude, dep_longitude = get_airport_coordinates(flight['departure']['iata'])
    # Récupérer les informations de l'aéroport d'arrivée
    arr_latitude, arr_longitude = get_airport_coordinates(flight['arrival']['iata'])
    
    if dep_latitude and arr_latitude:
        # Calculer la distance totale entre l'aéroport de départ et d'arrivée
        total_distance = haversine(dep_latitude, dep_longitude, arr_latitude, arr_longitude)
        
        # Découper en segments de 100 km
        num_segments = int(total_distance // 100)  # Nombre de segments de 100 km
        segment_positions = {}

        # Calculer les positions intermédiaires tous les 100 km et récupérer la météo
        for i in range(1, num_segments + 1):
            fraction = (i * 100) / total_distance  # Fraction de la distance totale parcourue
            intermediate_lat, intermediate_lon = interpolate_great_circle(dep_latitude, dep_longitude, arr_latitude, arr_longitude, fraction)
            
            # Obtenir les données météo à la position intermédiaire
            weather_data = get_weather_data(intermediate_lat, intermediate_lon, flight['departure'].get('actual'))
            
            segment_positions[f"{i * 100}Km"] = {
                "latitude": intermediate_lat,
                "longitude": intermediate_lon,
                **weather_data
            }

        # Récupérer les informations de l'avion (si présentes)
        aircraft = flight.get('aircraft') or {}

        # Construire le document à insérer dans MongoDB
        return {
            'flight_date': flight.get('flight_date'),
            'flight_status': flight.get('flight_status'),
            'departure': {
                'airport': flight['departure'].get('airport'),
                'timezone': flight['departure'].get('timezone'),
                'latitude': dep_latitude,
                'longitude': dep_longitude,
                'iata': flight['departure'].get('iata'),
                'icao': flight['departure'].get('icao'),
                'terminal': flight['departure'].get('terminal'),
                'gate': flight['departure'].get('gate'),
                'delay': flight['departure'].get('delay'),
                'scheduled': flight['departure'].get('scheduled'),
                'estimated': flight['departure'].get('estimated'),
                'actual': flight['departure'].get('actual'),
                'estimated_runway': flight['departure'].get('estimated_runway'),
                'actual_runway': flight['departure'].get('actual_runway'),
                **get_weather_data(dep_latitude, dep_longitude, flight['departure'].get('actual'))
            },
            'arrival': {
                'airport': flight['arrival'].get('airport'),
                'timezone': flight['arrival'].get('timezone'),
                'latitude': arr_latitude,
                'longitude': arr_longitude,
                'iata': flight['arrival'].get('iata'),
                'icao': flight['arrival'].get('icao'),
                'terminal': flight['arrival'].get('terminal'),
                'gate': flight['arrival'].get('gate'),
                'baggage': flight['arrival'].get('baggage'),
                'delay': flight['arrival'].get('delay'),
                'scheduled': flight['arrival'].get('scheduled'),
                'estimated': flight['arrival'].get('estimated'),
                'actual': flight['arrival'].get('actual'),
                'estimated_runway': flight['arrival'].get('estimated_runway'),
                'actual_runway': flight['arrival'].get('actual_runway'),
                **get_weather_data(arr_latitude, arr_longitude, flight['arrival'].get('actual'))
            },
            'airline': {
                'name': flight['airline'].get('name'),
                'iata': flight['airline'].get('iata'),
                'icao': flight['airline'].get('icao')
            },
            'flight': {
                'number': flight['flight'].get('number'),
                'iata': flight['flight'].get('iata'),
                'icao': flight['flight'].get('icao'),
                'codeshared': flight.get('codeshared')
            },
            'aircraft': {
                'registration': aircraft.get('registration'),
                'iata': aircraft.get('iata'),
                'icao': aircraft.get('icao'),
                'icao24': aircraft.get('icao24')
            },
            'segments': segment_positions  # Ajout des segments de 100 km avec météo
        }
    return None

# Requête API pour récupérer les vols atterris (aviationstack)
flight_info = api_requests.get_flights_landed()

# Filtrer les vols avec un départ et une arrivée en Europe
if flight_info and 'data' in flight_info:
    europe_flights = [
        flight for flight in flight_info['data']
        if flight.get('departure', {}).get('timezone') and flight.get('arrival', {}).get('timezone') and
        flight['departure']['timezone'].startswith('Europe') and 
        flight['arrival']['timezone'].startswith('Europe')
    ]

    # Créer une liste pour stocker les vols avec les données géographiques à insérer
    flights_to_insert = []

    for flight in europe_flights:
        flight_document = process_flight(flight)
        if flight_document:
            flights_to_insert.append(flight_document)

    # Insérer les données dans la collection MongoDB (app_data.europe_flights_today)
    if flights_to_insert:
        db.europe_flights_today.drop()  # On supprime d'abord la collection pour réinsérer les nouveaux vols
        db.europe_flights_today.insert_many(flights_to_insert)
        print(f"{len(flights_to_insert)} vols insérés dans la collection europe_flights_today.")
    else:
        print("Aucun vol à insérer.")
