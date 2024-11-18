# Utiliser l'image de base Python
FROM python:3.9-slim

# Définir le répertoire de travail
WORKDIR /app

# Met à jour pip
RUN pip install --upgrade pip

# Copier le fichier requirements.txt pour installer les dépendances
COPY /app/requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir --timeout=100 -r requirements.txt

# Copie les fichiers spécifiques
# COPY /model /app/model
COPY /app/templates /app/templates
COPY /app/app.py /app/app.py
# Copier le fichier de classe DataTransform qui se situe dans app_admin
COPY /app_admin/scripts/ml_data_transform.py /app/ml_data_transform.py

# Exposer le port sur lequel l'application Flask sera exécutée
EXPOSE 5002

# ---- Ne fonctionne pas car init_db à besoin de se connecter à Mongo qui ne sera pas encore lancé :
# Exécuter le script d'initialisation de la base de données
# RUN python init_db.py

# Commande pour lancer l'application
# CMD ["python", "app.py"]
