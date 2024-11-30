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

# Copier le contenu du repertoire
COPY . /app/

# Copie les répertoires spécifiques
# COPY data_test /app/data_test
# COPY functions /app/functions
# COPY /app_form/scripts /app/scripts
# COPY /app_form/templates /app/templates
# COPY /app_form/static /app/static
# COPY /app_form/tests /app/tests

# Copie les fichiers spécifiques
# COPY init_db.py /app/init_db.py
# COPY /app_form/app.py /app/app.py

# Exposer le port sur lequel l'application Flask sera exécutée
EXPOSE 5001