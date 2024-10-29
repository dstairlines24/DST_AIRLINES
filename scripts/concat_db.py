from pymongo import MongoClient
import pandas as pd

# Connexion à MongoDB
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.app_data

# Récupération des collections
collections = ['all_flights', 'asia_flights', 'europe_flights', 'america_flights', 'temp_db']
data = []

# Concaténer les collections en un DataFrame
for collection_name in collections:
    if collection_name in db.list_collection_names():  # Vérifier si la collection existe
        collection = db[collection_name]
        data.extend(list(collection.find({}, {"_id": 0})))  # Exclure le champ '_id'
        # Vérifier le contenu de chaque collection ajoutée
        # print(f"Données récupérées de la collection '{collection_name}':")
        # print(list(collection.find({}, {"_id": 0})))
    else:
        print(f"La collection '{collection_name}' n'existe pas dans la base de données.")  # Message d'erreur

# Création du DataFrame pandas MongoDB
df_new = pd.DataFrame(data)

# Création de colonnes temporaires pour récupérer les attributs 
df_new['dep_iata'] = df_new['departure'].apply(lambda x: x.get('iata') if isinstance(x, dict) else None)
df_new['arr_iata'] = df_new['arrival'].apply(lambda x: x.get('iata') if isinstance(x, dict) else None)
df_new['departure_scheduled'] = df_new['departure'].apply(lambda x: x.get('scheduled') if isinstance(x, dict) else None)
#Cette colonne servira à tester les doublons
df_new['dep_arr_scheduled'] = df_new.apply(
    lambda row: f"{row['dep_iata']}_{row['arr_iata']}_{row['departure_scheduled']}", axis=1
)

# print("Données récupérées dans df_new:")
# print(df_new)
print(f"\n\nNombre d'enregistrements dans les collections (df_new): {len(df_new)}")

# Affichage du nombre de doublons dans 'dep_arr_scheduled'
dup_count = df_new['dep_arr_scheduled'].value_counts()
dup_count = dup_count[dup_count > 1]  # Filtrer pour n'afficher que les valeurs avec des doublons
print("Nombre de doublons dans 'df_new' :")
print(dup_count)

# Récupération de la collection 'final_flights' existante s'il y a des enregistrements
if db.final_flights.estimated_document_count() > 0:
    df_existing = pd.DataFrame(list(db.final_flights.find()))

    # Retirer les ID existants pour laisser MongoDB en générer de nouveaux
    df_existing = df_existing.drop(columns=['_id'], errors='ignore')

    # Création de colonnes temporaires pour récupérer les attributs 
    df_existing['dep_iata'] = df_existing['departure'].apply(lambda x: x.get('iata') if isinstance(x, dict) else None)
    df_existing['arr_iata'] = df_existing['arrival'].apply(lambda x: x.get('iata') if isinstance(x, dict) else None)
    df_existing['departure_scheduled'] = df_existing['departure'].apply(lambda x: x.get('scheduled') if isinstance(x, dict) else None)
    
    #Cette colonne servira à tester les doublons
    df_existing['dep_arr_scheduled'] = df_existing.apply(
        lambda row: f"{row['dep_iata']}_{row['arr_iata']}_{row['departure_scheduled']}", axis=1
    )

    # Vérification des données dans df_existing avant la concaténation
    # print("Données existantes dans final_flights:")
    # print(df_existing)
    print(f"\n\nNombre d'enregistrements existants dans final_flights (df_existing): {len(df_existing)}")

    # Affichage du nombre de doublons dans 'dep_arr_scheduled'
    dup_count2 = df_existing['dep_arr_scheduled'].value_counts()
    dup_count2 = dup_count2[dup_count2 > 1]  # Filtrer pour n'afficher que les valeurs avec des doublons
    print("Nombre de doublons dans 'df_existing' :")
    print(dup_count2)

    # Concaténation des deux DataFrames
    df_combined = pd.concat([df_existing, df_new])
    print(f"\n\nNombre d'enregistrements après concat (df_combined): {len(df_combined)}")

    # Affichage du nombre de doublons dans 'dep_arr_scheduled' dans df_combined avant suppression des doublons
    dup_count_combined = df_combined['dep_arr_scheduled'].value_counts()
    dup_count_combined = dup_count_combined[dup_count_combined > 1]  # Filtrer pour n'afficher que les valeurs avec des doublons
    print("Nombre de doublons dans 'df_combined' avant suppression :")
    print(dup_count_combined)

    # Suppression des doublons basés sur 'dep_arr_scheduled'
    df_combined = df_combined.drop_duplicates(subset=['dep_arr_scheduled'])
else:
    # Si 'final_flights' est vide, utiliser seulement les nouvelles données
    df_combined = df_new

# Vérification des données dans df_combined après suppression des doublons
# print("Données combinées après suppression des doublons:")
# print(df_combined)
print(f"\n\nNombre d'enregistrements après concat et suppression des doublons (df_combined): {len(df_combined)}")


# Suppression des colonnes temporaires avant insertion
df_combined = df_combined.drop(columns=['dep_arr_scheduled'], errors='ignore')

# Vider la collection 'final_flights' et insérer les données combinées sans doublons
db.final_flights.delete_many({})  # Supprimer tous les documents existants dans 'final_flights'
db.final_flights.insert_many(df_combined.to_dict('records'))  # Insérer les données sans les IDs

# Vérification finale
print(f"\nNombre d'enregistrements dans final_flights après insertion: {db.final_flights.estimated_document_count()}")
print("Données combinées et insérées dans 'final_flights' avec succès.")