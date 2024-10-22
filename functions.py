from flask import jsonify
from api_requests import APIRequests
import math
from datetime import datetime, timedelta

class FlightDataError(Exception):
    def __init__(self, message, detail_1=None, detail_2=None, detail_3=None, detail_4=None):
        super().__init__(message)
        self.detail_1 = detail_1
        self.detail_2 = detail_2
        self.detail_3 = detail_3
        self.detail_4 = detail_4

class FlightProcessor:
    def __init__(self):
        self.api_requests = APIRequests()

    # Fonction pour récupérer les vols du jour
    def get_flights_landed(self):
        flights_info=self.api_requests.get_flights_landed()
        if flights_info:
            return flights_info
        raise FlightDataError("Problème lié à l'api avionstack")

    # Fonction pour récupérer les informations géographiques d'un aéroport
    def get_airport_coordinates(self, iata_code):
        airport_info = self.api_requests.get_airport_LH(iata_code)
        if airport_info:
            latitude = airport_info['AirportResource']['Airports']['Airport']['Position']['Coordinate']['Latitude']
            longitude = airport_info['AirportResource']['Airports']['Airport']['Position']['Coordinate']['Longitude']
            return latitude, longitude
        raise FlightDataError("Problème à l'API aiport_LH", detail_1=iata_code, detail_2=airport_info)

    # Fonction pour calculer la distance orthodromique entre deux points (en km)
    @staticmethod
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
    @staticmethod
    def interpolate_great_circle(lat1, lon1, lat2, lon2, fraction):
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        d = FlightProcessor.haversine(math.degrees(lat1), math.degrees(lon1), math.degrees(lat2), math.degrees(lon2)) / 6371.0
        A = math.sin((1 - fraction) * d) / math.sin(d)
        B = math.sin(fraction * d) / math.sin(d)
        x = A * math.cos(lat1) * math.cos(lon1) + B * math.cos(lat2) * math.cos(lon2)
        y = A * math.cos(lat1) * math.sin(lon1) + B * math.cos(lat2) * math.sin(lon2)
        z = A * math.sin(lat1) + B * math.sin(lat2)
        new_lat = math.atan2(z, math.sqrt(x**2 + y**2))
        new_lon = math.atan2(y, x)
        return math.degrees(new_lat), math.degrees(new_lon)

    # Fonction pour récupérer les informations météo pour une position donnée
    def get_weather_data(self, lat, lon, time):
        meteo = self.api_requests.get_meteo(lat, lon, time)
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
        raise FlightDataError("Problème à l'API météo", detail_1=lat, detail_2=lon, detail_3=meteo)

    # Fonction pour traiter un vol et obtenir les données à insérer sur un seul enregistrement
    def process_flight_AS(self, flight):
        # Vérification des données de départ et d'arrivée
        if not flight.get('departure') or not flight.get('arrival'):
            raise FlightDataError("Problème avec l'objet passé dans process_flight_AS", detail_1=flight)

        # Récupérer les informations de l'aéroport de départ
        dep_latitude, dep_longitude = self.get_airport_coordinates(flight['departure']['iata'])
        # Récupérer les informations de l'aéroport d'arrivée
        arr_latitude, arr_longitude = self.get_airport_coordinates(flight['arrival']['iata'])
        
        if dep_latitude and arr_latitude:
            # Calculer la distance totale entre l'aéroport de départ et d'arrivée
            total_distance = self.haversine(dep_latitude, dep_longitude, arr_latitude, arr_longitude)
            
            # Découper en segments de 100 km
            num_segments = int(total_distance // 100)  # Nombre de segments de 100 km
            segment_positions = {}

            # Calculer les positions intermédiaires tous les 100 km et récupérer la météo
            for i in range(1, num_segments + 1):
                fraction = (i * 100) / total_distance  # Fraction de la distance totale parcourue
                intermediate_lat, intermediate_lon = self.interpolate_great_circle(dep_latitude, dep_longitude, arr_latitude, arr_longitude, fraction)
                
                #Calcul de 'time' correspondant à date et heure à chaque segment
                formatted_datetime = datetime.fromisoformat(flight['departure'].get('scheduled')).strftime("%Y-%m-%dT%H:%M:%S")
                datetime_obj = datetime.strptime(formatted_datetime, "%Y-%m-%dT%H:%M:%S")
                updated_datetime = datetime_obj + timedelta(minutes=10*i)
                formatted_updated_datetime = updated_datetime.strftime("%Y-%m-%dT%H:%M:%S")

                # Obtenir les données météo à la position intermédiaire
                weather_data = self.get_weather_data(intermediate_lat, intermediate_lon, formatted_updated_datetime)

                segment_positions[f"{i * 100}Km"] = {
                    "latitude": intermediate_lat,
                    "longitude": intermediate_lon,
                    "time": formatted_updated_datetime,
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
                    **self.get_weather_data(dep_latitude, dep_longitude, flight['departure'].get('scheduled'))
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
                    **self.get_weather_data(arr_latitude, arr_longitude, flight['arrival'].get('scheduled'))
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
        raise FlightDataError("Problème avec la fonction get_airport_coordinates", detail_1=dep_latitude, detail_2=dep_longitude, detail_3=arr_latitude, detail_4=arr_longitude)
    
    # Fonction pour traiter des vols et obtenir les données à insérer pour une liste de vols
    def process_flight_AS_list(self, flights_list):
        flights_to_insert = []
        for flight in flights_list:
            flight_document = self.process_flight_AS(flight)
            if flight_document:
                flights_to_insert.append(flight_document)
        return flights_to_insert
