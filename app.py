from flask import Flask, jsonify, request, render_template_string
import threading
import time

app = Flask(__name__)

# Lock pour éviter que deux acheteurs ne cliquent sur la même milliseconde
auction_lock = threading.Lock()

# =========================
# DONNÉES ENRICHIES (Copernicus)
# =========================
lots = {
    "lot1": {
        "product": "Arachide Grade A – Diourbel",
        "quantity": "500 kg",
        "start_price": 350,
        "current_price": 350,
        "min_price": 250,
        "time_left": 180,
        "active": False,
        "winner": None,
        "ndvi": 0.72,  # Indice de végétation (Sentinel-2)
        "humidity": "12%" # Humidité du sol (Sentinel-1)
    },
    "lot2": {
        "product": "Mil local – Kaolack",
        "quantity": "1 tonne",
        "start_price": 220,
        "current_price": 220,
        "min_price": 160,
        "time_left": 200,
        "active": False,
        "winner": None,
        "ndvi": 0.61,
        "humidity": "15%"
    }
}

# =========================
# LOGIQUE DU CADRAN
# =========================
def auction_timer(lot_id):
    while True:
        time.sleep(1)
        with auction_lock:
            # Si le lot n'est plus actif ou temps épuisé, on sort
            if not lots[lot_id]["active"] or lots[lot_id]["time_left"] <= 0:
                break
            
            # Baisse du prix
            lots[lot_id]["current_price"] -= 1
            lots[lot_id]["time_left"] -= 1

            # Arrêt si prix minimum atteint
            if lots[lot_id]["current_price"] <= lots[lot_id]["min_price"]:
                lots[lot_id]["active"] = False
                lots[lot_id]["winner"] = "Non vendu (Prix min atteint)"
                break

# =========================
# FRONT-END
# =========================
@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <title>Marché au Cadran Agricole</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #eceff1; color: #333; }
        .container { max-width: 800px; margin: auto; padding: 20px; }
        .card { background: white; padding: 20px; margin-bottom: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #2e7d32; }
        .price { font-size: 3em; color: #d32f2f; font-weight: bold; margin: 10px 0; }
        .meta { display: flex; gap: 15px; margin-bottom: 15px; font-size: 0.9em; color: #666; }
        .badge { background: #e8f5e9; color: #2e7d32; padding: 5px 10px; border-radius: 5px; font-weight: bold; }
        button { background: #2e7d32; color: white; border: none; padding: 15px 30px; font-size: 1.2em; border-radius: 8px; cursor: pointer; width: 100%; }
        button:disabled { background: #ccc; }
        .winner { background: #fff3e0; padding: 10px; border-radius: 5px; color: #ef6c00; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌾 Marché Agricole Live</h1>
        <p>Prix dégressifs en temps réel certifiés par Copernicus</p>
        <div id="lots"></div>
    </div>

    <script>
        function loadLots(){
            fetch("/api/lots")
            .then(r => r.json())
            .then(data => {
                let html = "";
                for(let id in data){
                    let l = data[id];
                    let isWinner = l.winner !== null;
                    html += `
                    <div class="card">
                        <h2>${l.product}</h2>
                        <div class="meta">
                            <span class="badge">🛰 NDVI: ${l.ndvi}</span>
                            <span class="badge">💧 Humidité: ${l.humidity}</span>
                            <span>📦 ${l.quantity}</span>
                        </div>
                        <div class="price">${l.current_price} <small>FCFA/kg</small></div>
                        <p>⏱ Temps restant: ${l.time_left}s</p>
                        ${isWinner ? `<div class="winner">🏆 Vendeur : ${l.winner}</div>` 
                                   : `<button onclick="bid('${id}')">💰 ACHETER MAINTENANT</button>`}
                    </div>`;
                }
                document.getElementById("lots").innerHTML = html;
            })
        }

        function bid(id){
            fetch("/api/bid/"+id, {method:"POST"})
            .then(r => r.json())
            .then(res => { if(res.error) alert(res.error); });
        }

        setInterval(loadLots, 1000);
        loadLots();
    </script>
</body>
</html>
""")

# =========================
# API RÉCURSIVE
# =========================
@app.route("/api/lots")
def get_lots():
    return jsonify(lots)

@app.route("/api/start/<lot_id>", methods=["POST"])
def start_lot(lot_id):
    if lot_id in lots and not lots[lot_id]["active"]:
        lots[lot_id]["active"] = True
        lots[lot_id]["winner"] = None
        lots[lot_id]["current_price"] = lots[lot_id]["start_price"]
        threading.Thread(target=auction_timer, args=(lot_id,), daemon=True).start()
        return jsonify({"status": "started"})
    return jsonify({"error": "lot non trouvé ou déjà actif"}), 404

@app.route("/api/bid/<lot_id>", methods=["POST"])
def bid(lot_id):
    with auction_lock:
        if lot_id in lots and lots[lot_id]["active"]:
            # On stoppe l'enchère immédiatement au premier clic
            lots[lot_id]["active"] = False
            bidder = request.remote_addr
            lots[lot_id]["winner"] = f"Acheteur {bidder}"
            return jsonify({"status": "gagné", "price": lots[lot_id]["current_price"]})
    return jsonify({"error": "Lot déjà vendu ou expiré"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
