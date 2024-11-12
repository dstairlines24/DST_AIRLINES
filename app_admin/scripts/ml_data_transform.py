import pandas as pd
import numpy as np



class DataTransform:
    def __init__(self, df: pd.DataFrame):
        # Initialisation avec le DataFrame de base
        self.df = df
            
    #=================================================
    # Définition des fontions
    #=================================================
    # Fonction pour supprimer les lignes des valeurs NA pour un colonne spécifiée en argument
    def remove_na(self, subset=None):
        self.df = self.df.dropna(subset=subset)
        return self.df
        
    # Fonction pour transformer les segments en colonne
    def segment_to_col(self):
        
        # Extraire chaque segment (100Km, 200Km, etc.) comme une colonne contenant le dictionnaire complet
        segments_df = pd.DataFrame(self.df['segments'].tolist())
        
        # Fusionner le DataFrame des segments avec le DataFrame principal
        self.df = self.df.drop(columns=['segments']).join(segments_df)

        return self.df

    # Fonction pour ajouter la colonne delay_diff
    def add_target_delay_diff(self):
        # Création de la variable cible : 'delay_difference'
        self.df['target_delay_difference'] = self.df['arrival'].apply(lambda x: x.get('delay', 0)) - self.df['departure'].apply(lambda x: x.get('delay', 0))
        self.df['target_delay_difference'] = self.df['target_delay_difference'].apply(lambda x: max(x, 0))  # Remplace les valeurs négatives par 0
        return self.df
        

    # Fonction pour ajouter la colonne feat_distance_km
    def add_feat_distance_km(self):
        def count_non_empty(row):
            # Compter les colonnes 'segments' non vides pour cette ligne
            non_empty_count = 0
            # Parcourir toutes les colonnes de segments (100Km, 200Km, etc.)
            for col in self.df.columns:
                if col.endswith('Km'):  # Vérifier si la colonne est un segment (100Km, 200Km, etc.)
                    segment = row[col]
                    # Si la colonne n'est pas vide (non NaN, non None, et non un dictionnaire vide)
                    if pd.notna(segment) and segment != {}:
                        non_empty_count += 1
                        
            distance_km = 50 + 100 *non_empty_count
            return distance_km
        
        # Appliquer la fonction 'count_non_empty' à chaque ligne du DataFrame
        self.df['feat_distance_km'] = self.df.apply(count_non_empty, axis=1)
        
        return self.df
        

    # Fonction pour ajouter la colonne feat_total_icon_score
    def add_feat_icon_score(self):
        # Définir un système de score pour les icon
        icon_scores = {
            'clear-day': 1,
            'clear-night': 1,
            'cloudy': 2,
            'fog': 8,
            'hail': 9,
            'partly-cloudy-day': 2,
            'partly-cloudy-night': 2,
            'rain': 6,
            'rain-snow': 7,
            'rain-snow-showers-day': 6,
            'rain-snow-showers-night': 6,
            'showers-day': 5,
            'showers-night': 5,
            'sleet': 8,
            'snow': 9,
            'snow-showers-day': 7,
            'snow-showers-night': 7,
            'thunder': 10,
            'thunder-rain': 10,
            'thunder-showers-day': 9,
            'thunder-showers-night': 9,
            'wind': 7
        }
        
        # Fonction pour effectuer le calcul du score pour chaque ligne
        def sum_values(row):
            total_icon_score = 0
            
            # Extraire les icon météo, calculer le score et l'ajouter à total_icon_score pour le departure
            departure_icon = self.df['departure'].get('icon', np.nan)
            departure_icon_score = icon_scores.get(departure_icon, 0)
            total_icon_score += departure_icon_score
            
            # Extraire les icon météo, calculer le score et l'ajouter à total_icon_score pour le arrival
            arrival_icon = self.df['arrival'].get('icon', np.nan)
            arrival_icon_score = icon_scores.get(arrival_icon, 0)
            total_icon_score += arrival_icon_score
            
            # Parcourir chaque colonne de segment (100Km, 200Km, etc.)
            for col in self.df.columns:
                if col.endswith("Km"):  # Vérifier si la colonne est un segment (100Km, 200Km, etc.)
                    segment = row[col]
                    # Si le segment est un dictionnaire on ajoute le icon_score au total_icon_score
                    if isinstance(segment, dict):
                        segment_icon = segment.get('icon', np.nan)
                        segment_icon_score = icon_scores.get(segment_icon, 0)
                        total_icon_score += segment_icon_score
            
            return total_icon_score
        
        # Appliquer la fonction à chaque ligne du DataFrame
        self.df['feat_total_icon_score'] = self.df.apply(sum_values, axis=1)
        
        return self.df

    # Fonction pour ajouter les autres infos météo
    def add_feat_infos_meteo(self):
        # Extraction des informations météo
        weather_features = ['cloudcover', 'humidity', 'precip', 'pressure', 'snow', 'snowdepth', 'temp', 'visibility', 'windspeed']
        
        # Variables météo départ et arrivée
        for col in weather_features:
            self.df[f'feat_dep_{col}'] = self.df['departure'].apply(lambda x: x.get(col, np.nan))
            self.df[f'feat_arr_{col}'] = self.df['arrival'].apply(lambda x: x.get(col, np.nan))
        
        for col in weather_features:
            segment_values = self.df['segments'].apply(
                lambda segments: [seg.get(col, np.nan) for seg in segments.values() if seg.get(col) is not None]
            )
            self.df[f'feat_seg_mean_{col}'] = segment_values.apply(lambda x: np.nanmean(x) if len(x) > 0 else np.nan)
            self.df[f'feat_seg_std_{col}'] = segment_values.apply(lambda x: np.nanstd(x) if len(x) > 0 else np.nan)
            self.df[f'feat_seg_max_{col}'] = segment_values.apply(lambda x: np.nanmax(x) if len(x) > 0 else np.nan)
            self.df[f'feat_seg_min_{col}'] = segment_values.apply(lambda x: np.nanmin(x) if len(x) > 0 else np.nan)
        
        return self.df