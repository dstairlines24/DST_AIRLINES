# Utiliser l'image de base Python
FROM python:3.9-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier le fichier requirements.txt pour installer les dépendances
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier les fichiers de l'application
COPY . .

# Exécuter le script d'initialisation de la base de données
RUN python init_db.py

# Exposer le port sur lequel l'application Flask sera exécutée
EXPOSE 5000

# Commande pour lancer l'application
CMD ["python", "app.py"]
