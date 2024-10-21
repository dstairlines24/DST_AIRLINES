from api_requests import APIRequests
import math
from datetime import datetime, timedelta


class FlightDataError(Exception):
    def __init__(self, message, details_1=None, details_2=None, details_3=None, details_4=None):
        super().__init__(message)
        self.details_1 = details_1
        self.details_2 = details_2
        self.details_3 = details_3
        self.details_4 = details_4

class FlightProcessor:
    def __init__(self):
        self.api_requests = APIRequests()

    # Fonction pour récupérer les coordonnées de l'aéroport via l'API LH
    def get_airport_coordinates(self, iata_code):
        airport_info = self.api_requests.get_airport_LH(iata_code)
        try:
            latitude = airport_info['AirportResource']['Airports']['Airport']['Position']['Coordinate']['Latitude']
            longitude = airport_info['AirportResource']['Airports']['Airport']['Position']['Coordinate']['Longitude']
            return latitude, longitude
        except KeyError:
            raise FlightDataError("Aéroport non reconnu par l'API LH", details_1=iata_code, details_2=airport_info)

    # Calcul de la distance entre deux points (distance orthodromique)
    @staticmethod
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371.0  # Rayon de la Terre en km
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    # Interpolation d'une position entre deux points pour suivre un grand cercle
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

    # Récupération des données météo à une position donnée
    def get_weather_data(self, lat, lon, time):
        try:
            return self.api_requests.get_meteo(lat, lon, time)['currentConditions']
        except Exception as e:
            print(f"Erreur lors de la récupération des données météo: {e}")
            return {}

    # Traitement d'un vol avec interpolation et récupération météo
    def process_flight_AS(self, flight):
        try:
            dep_latitude, dep_longitude = self.get_airport_coordinates(flight['departure']['iata'])
            arr_latitude, arr_longitude = self.get_airport_coordinates(flight['arrival']['iata'])
        except FlightDataError:
            return None  # Ignorer le vol si les aéroports ne sont pas valides

        # Calcul de la distance entre aéroports
        total_distance = self.haversine(dep_latitude, dep_longitude, arr_latitude, arr_longitude)
        num_segments = int(total_distance // 100)  # Segment de 100 km

        # Interpolation des positions et récupération des données météo
        segment_positions = {}
        for i in range(1, num_segments + 1):
            fraction = (i * 100) / total_distance
            lat, lon = self.interpolate_great_circle(dep_latitude, dep_longitude, arr_latitude, arr_longitude, fraction)
            time = datetime.fromisoformat(flight['departure']['scheduled']) + timedelta(minutes=10*i)
            weather_data = self.get_weather_data(lat, lon, time.isoformat())
            segment_positions[f"{i * 100}Km"] = {
                "latitude": lat,
                "longitude": lon,
                "time": time.isoformat(),
                **weather_data
            }

        # Construction du document final
        aircraft = flight.get('aircraft', {})
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
            'segments': segment_positions
        }

    # Traitement d'une liste de vols
    def process_flight_AS_list(self, flights_list):
        flights_to_insert = []
        for flight in flights_list:
            flight_document = self.process_flight_AS(flight)
            if flight_document:
                flights_to_insert.append(flight_document)
        return flights_to_insert
