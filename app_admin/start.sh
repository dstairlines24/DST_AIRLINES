#!/bin/bash

# Initialiser la bdd
python init_db.py

# Démarrer Jupyter Notebook en arrière-plan
jupyter notebook --no-browser --allow-root --NotebookApp.token='' &

# CRON JOB
chmod +x cronpipe.sh
# Ajouter le cron job dans le crontab de l'utilisateur
# Cela vérifie d'abord si la tâche existe déjà pour éviter les doublons
(crontab -l 2>/dev/null | grep -v "cronpipe.sh"; echo "0 8 * * * cronpipe.sh") | crontab -

# Lancer cron
service cron start

# Lancer l'app
python app.py