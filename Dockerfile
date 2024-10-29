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

# Copier tous les fichiers de l'application
# COPY . .

# Copie les répertoires spécifiques
# COPY data /app/data
COPY functions /app/functions
COPY scripts /app/scripts
COPY static /app/static
COPY templates /app/templates

# Copie les fichiers spécifiques
COPY app.py /app/app.py
COPY init_db.py /app/init_db.py

# Exécuter le script d'initialisation de la base de données
# RUN python init_db.py

# Exposer le port sur lequel l'application Flask sera exécutée
EXPOSE 5000

# Commande pour lancer l'application
# CMD ["python", "app.py"]
