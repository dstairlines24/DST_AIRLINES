#!/bin/bash

# Initialiser la bdd
python init_db.py

# Démarrer Jupyter Notebook en arrière-plan
jupyter notebook --no-browser --allow-root --NotebookApp.token='' &

# Lancer les app
python app_flask.py &
python app_dash.py &

