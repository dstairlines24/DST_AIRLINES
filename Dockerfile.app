# Utiliser l'image de base Python
FROM python:3.9-slim

# Définir le répertoire de travail
WORKDIR /app

# Met à jour pip
RUN pip install --upgrade pip

# Copier le fichier requirements.txt pour installer les dépendances
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir --timeout=100 -r requirements.txt

# Copie les répertoires spécifiques
COPY data_test /app/data_test
COPY functions /app/functions
COPY scripts /app/scripts
COPY templates /app/templates

# Copie les fichiers spécifiques
COPY init_db.py /app/init_db.py
COPY app.py /app/app.py

# Exposer le port sur lequel l'application Flask sera exécutée
EXPOSE 5000

# ---- Ne fonctionne pas car init_db à besoin de se connecter à Mongo qui ne sera pas encore lancé :
# Exécuter le script d'initialisation de la base de données
# RUN python init_db.py

# Commande pour lancer l'application
# CMD ["python", "app.py"]
