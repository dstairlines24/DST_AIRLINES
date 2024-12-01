from pymongo import MongoClient
import os
from pymongo.errors import ServerSelectionTimeoutError

# Récupérer l'URI de MongoDB depuis la variable d'environnement
mongo_uri = "mongodb://root:root@mongodb:27017/app_data?authSource=admin"

# Débogage : afficher l'URI et autres informations d'authentification
print(f"Connecting to MongoDB with URI: {mongo_uri}")

# Connexion à MongoDB
try:
    client = MongoClient("mongodb://root:root@mongodb:27017/app_data?authSource=admin")
    client.admin.command("ping")
    print("Connexion à MongoDB réussie.")
except Exception as e:
    print("Erreur de connexion à MongoDB:", e)
    exit(1)

# Attendre que MongoDB soit prêt avant de tenter une connexion
# def wait_for_mongo():
#     print("Attente de la connexion à MongoDB...")
#     while True:
#         try:
#             client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)  # Timeout de 5 secondes
#             client.admin.command('ping')  # Tenter un simple ping pour tester la connexion
#             print("MongoDB est prêt.")
#             break
#         except ServerSelectionTimeoutError:
#             print("MongoDB n'est pas encore prêt, réessayer...")
#             time.sleep(5)  # Attendre 5 secondes avant de réessayer

# # Appeler cette fonction avant de continuer
# wait_for_mongo()


def init_db():
    db_credentials = client.app_credentials
    # Supprimer la collection des utilisateurs si elle existe déjà
    db_credentials.users.drop()

    # Créer des utilisateurs avec des mots de passe hachés
    flask_admin_password_h = generate_password_hash(flask_admin_password)
    flask_user_password_h = generate_password_hash(flask_user_password)

    db_credentials.users.insert_one({"username": flask_admin_login, "password": flask_admin_password_h, "role": "admin"})
    db_credentials.users.insert_one({"username": flask_user_login, "password": flask_user_password_h, "role": "user"})

    print("Base de données initialisée avec succès !")

def load_test_to_app_data(bson_file_path):
    # Charger le fichier .bson et insérer les documents dans la collection test_col
    db_app = client.app_data

    # Supprimer la collection si elle existe déjà pour éviter les doublons
    db_app.test_col.drop()

    try:
        # Lire le fichier .bson et insérer chaque document
        with open(bson_file_path, 'rb') as f:
            data = bson.decode_all(f.read())
            db_app.test_col.insert_many(data)
        print(f"Collection 'app_data.test_col' remplie avec succès à partir de {bson_file_path}")
    except Exception as e:
        print("Erreur lors du chargement du fichier .bson:", e)

def load_test_to_app_data_form(bson_file_path):
    # Charger le fichier .bson et insérer les documents dans la collection test_col
    db_app_form = client.app_data_form
    db_app = client.app_data

    # Supprimer la collection si elle existe déjà pour éviter les doublons
    db_app_form.test_col.drop()
    db_app.temp_col.drop()

    try:
        # Lire le fichier .bson et insérer chaque document
        with open(bson_file_path, 'rb') as f:
            data = bson.decode_all(f.read())
            db_app_form.test_col.insert_many(data)
            db_app.temp_col.insert_many(data)
        print(f"Collection 'app_data_form.test_col' remplie avec succès à partir de {bson_file_path}")
        print(f"Collection 'app_data.temp_col' remplie avec succès à partir de {bson_file_path}")
    except Exception as e:
        print("Erreur lors du chargement du fichier .bson:", e)

def concat_db():
    db = client.app_data

    # Récupération des collections
    collections = ['temp_col']
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

    # Récupération de la collection 'final_flights' existante s'il y a des enregistrements
    if db.final_flights.estimated_document_count() > 0:
        df_existing = pd.DataFrame(list(db.final_flights.find()))

        # Retirer les ID existants pour laisser MongoDB en générer de nouveaux
        df_existing = df_existing.drop(columns=['_id'], errors='ignore')

        # Vérification des données dans df_existing avant la concaténation
        print(f"\n\nNombre d'enregistrements existants dans final_flights (df_existing): {len(df_existing)}")

        # Concaténation des deux DataFrames
        df_combined = pd.concat([df_existing, df_new])
        print(f"\n\nNombre d'enregistrements après concat (df_combined): {len(df_combined)}")

        # Récupération du nombre de doublons dans 'dep_arr_scheduled'
        total_dup_count_combined = df_combined.duplicated(subset=['dep_arr_scheduled']).sum()
        dup_count_new_combined = df_combined['dep_arr_scheduled'].value_counts()
        dup_count_new_combined = dup_count_new_combined[dup_count_new_combined > 1]  # Filtrer pour n'afficher que les valeurs avec des doublons

        # Suppression des doublons basés sur 'dep_arr_scheduled'
        df_combined = df_combined.drop_duplicates(subset=['dep_arr_scheduled'])

        # Affichage
        print(f"Nombre de doublons total (df_combined): {total_dup_count_combined}")
        print(f"Nombre d'enregistrements après suppression des doublons (df_combined): {len(df_combined)}")
        print("Doublons supprimés (df_combined):")
        print(dup_count_new_combined)

    else:
        # Si 'final_flights' est vide, utiliser seulement les nouvelles données
        df_combined = df_new

    # Vérification des données dans df_combined après suppression des doublons
    # print("Données combinées après suppression des doublons:")
    # print(df_combined)
    print(f"\n\nNombre d'enregistrements après suppression des doublons (df_combined): {len(df_combined)}")


    # Suppression des colonnes temporaires avant insertion
    df_combined = df_combined.drop(columns=['dep_arr_scheduled'], errors='ignore')

    # Vider la collection 'final_flights' et insérer les données combinées sans doublons
    db.final_flights.delete_many({})  # Supprimer tous les documents existants dans 'final_flights'
    db.final_flights.insert_many(df_combined.to_dict('records'))  # Insérer les données sans les IDs

    # Vérification finale
    print(f"\nNombre d'enregistrements dans final_flights après insertion: {db.final_flights.estimated_document_count()}")
    print("Données combinées et insérées dans 'final_flights' avec succès.")

if __name__ == "__main__":
    init_db()
    # Spécifier le chemin vers le fichier .bson
    bson_file_path = "data_test/test_col.bson"
    load_test_to_app_data(bson_file_path)
    load_test_to_app_data_form(bson_file_path)
    concat_db()
