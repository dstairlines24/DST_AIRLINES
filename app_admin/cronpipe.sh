#!/bin/bash

python3 ~/scripts/all_flights.py
python3 ~/scripts/concat_db.py
python3 ~/scripts/ml_gridsearchcv2.py