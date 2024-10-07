from flask import Flask, jsonify, render_template
from pymongo import MongoClient

app = Flask(__name__)

# Connexion à MongoDB
# client = MongoClient("mongodb://dstairlines:dstairlines@localhost:27017/")
client = MongoClient(host="localhost", port=27017, username="dstairlines", password="dstairlines")
db = client.airport_data

@app.route('/airports', methods=['GET'])
def get_airports():
    # Récupérer les aéroports depuis MongoDB
    airports = list(db.airports.find({}, {"_id": 0}))  # Ne pas inclure l'_id
    return jsonify(airports)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)