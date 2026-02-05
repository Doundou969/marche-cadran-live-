from flask import Flask, jsonify, request, render_template_string
import threading
import time

app = Flask(__name__)

# Lock pour garantir qu'un seul acheteur gagne (concurrence)
auction_lock = threading.Lock()

# =========================================================
# BASE DE DONNÉES TEMPORAIRE (Mémoire vive)
# =========================================================
lots = {
    "lot_init_01": {
        "product": "Arachide Grade A – Diourbel",
        "quantity": "500 kg",
        "start_price": 350,
        "current_price": 350,
        "min_price": 250,
        "time_left": 180,
        "active": False,
        "winner": None,
        "ndvi": 0.75,  # Indice de végétation Copernicus
        "humidity": "12%"
    }
}

# =========================================================
# LOGIQUE DU COMPTE À REBOURS (CADRAN)
# =========================================================
def auction_timer(lot_id):
    while True:
        time.sleep(1)
        with auction_lock:
            # Vérifier si le lot est toujours actif
            if not lots[lot_id]["active"] or lots[lot_id]["time_left"] <= 0:
                break
            
            # Dégressivité
            lots[lot_id]["current_price"] -= 1
            lots[lot_id]["time_left"] -= 1

            # Arrêt si prix plancher atteint
            if lots[lot_id]["current_price"] <= lots[lot_id]["min_price"]:
                lots[lot_id]["active"] = False
                lots[lot_id]["winner"] = "Non vendu (Prix minimum atteint)"
                break

# =========================================================
# ROUTES API
# =========================================================
@app.route("/api/lots")
def get_lots():
    return jsonify(lots)

@app.route("/api/add_lot", methods=["POST"])
def add_lot():
    data = request.json
    lot_id = data['id']
    lots[lot_id] = {
        "product": data['product'],
        "quantity": data['quantity'],
        "start_price": data['start_price'],
        "current_price": data['start_price'],
        "min_price": data['min_price'],
        "time_left": 180,
        "active": False,
        "winner": None,
        "ndvi": data['ndvi'],
        "humidity": "14%"
    }
    return jsonify({"status": "success"})

@app.route("/api/start/<lot_id>", methods=["POST"])
def start_lot(lot_id):
    if lot_id in lots and not lots[lot_id]["active"]:
        lots[lot_id]["active"] = True
        lots[lot_id]["winner"] = None
        lots[lot_id]["current_price"] = lots[lot_id]["start_price"]
        lots[lot_id]["time_left"] = 180
        threading.Thread(target=auction_timer, args=(lot_id,), daemon=True).start()
        return jsonify({"status": "started"})
    return jsonify({"error": "Impossible de lancer"}), 400

@app.route("/api/bid/<lot_id>", methods=["POST"])
def bid(lot_id):
    with auction_lock:
        if lot_id in lots and lots[lot_id]["active"]:
            lots[lot_id]["active"] = False
            bidder = request.remote_addr
            lots[lot_id]["winner"] = f"Acheteur ({bidder})"
            return jsonify({"status": "gagné"})
    return jsonify({"error": "Lot expiré ou déjà vendu"}), 400

# =========================================================
# INTERFACE CLIENT (ACHETEURS)
# =========================================================
@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Marché Agricole Cadran</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }
        .header { background: #2e7d32; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .card { background: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-top: 8px solid #2e7d32; }
        .price { font-size: 2.5em; color: #d32f2f; font-weight: bold; margin: 15px 0; }
        .badge { background: #e8f5e9; color: #1b5e20; padding: 5px 10px; border-radius: 5px; font-size: 0.8em; font-weight: bold; margin-right: 5px; }
        .winner-box { background: #fff3e0; border: 1px solid #ffe0b2; padding: 10px; border-radius: 8px; color: #e65100; font-weight: bold; }
        button { background: #2e7d32; color: white; border: none; width: 100%; padding: 15px; border-radius: 8px; font-size: 1.1em; cursor: pointer; transition: 0.3s; }
        button:hover { background: #1b5e20; }
        button:disabled { background: #ccc; cursor: not-allowed; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🌾 Marché Agricole en Direct</h1>
        <p>Données de végétation certifiées par <strong>Copernicus Sentinel-2</strong></p>
    </div>
    <div id="lots-container" class="grid"></div>

    <script>
        function updateUI() {
            fetch('/api/lots')
            .then(r => r.json())
            .then(data => {
                let html = "";
                for(let id in data) {
                    let l = data[id];
                    html += `
                    <div class="card">
                        <h3>${l.product}</h3>
                        <div>
                            <span class="badge">🛰 NDVI: ${l.ndvi}</span>
                            <span class="badge">📦 ${l.quantity}</span>
                        </div>
                        <div class="price">${l.current_price} <small>FCFA/kg</small></div>
                        <p>⏱ Temps restant: <strong>${l.time_left}s</strong></p>
                        ${l.winner ? `<div class="winner-box">🏆 Vendu à : ${l.winner}</div>` 
                                   : `<button onclick="bid('${id}')" ${!l.active ? 'disabled' : ''}>${l.active ? 'ACHETER MAINTENANT' : 'EN ATTENTE'}</button>`}
                    </div>`;
                }
                document.getElementById('lots-container').innerHTML = html;
            });
        }
        function bid(id) { fetch('/api/bid/'+id, {method:'POST'}); }
        setInterval(updateUI, 1000);
        updateUI();
    </script>
</body>
</html>
""")

# =========================================================
# DASHBOARD ADMIN (GESTION)
# =========================================================
@app.route("/admin")
def admin():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Console Admin</title>
    <style>
        body { font-family: sans-serif; background: #1a1a1b; color: white; padding: 30px; }
        .container { max-width: 1000px; margin: auto; display: grid; grid-template-columns: 1fr 1.5fr; gap: 30px; }
        .box { background: #2b2d2e; padding: 20px; border-radius: 10px; }
        input { width: 90%; padding: 10px; margin: 10px 0; background: #444; border: none; color: white; border-radius: 5px; }
        .btn-add { background: #4caf50; border: none; color: white; padding: 10px; width: 95%; cursor: pointer; }
        .lot-row { background: #3c3f41; padding: 15px; margin-bottom: 10px; border-radius: 5px; display: flex; justify-content: space-between; }
        .btn-go { background: #ffa000; border: none; padding: 5px 15px; border-radius: 3px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>🚀 Administration du Cadran</h1>
    <div class="container">
        <div class="box">
            <h2>➕ Ajouter un Lot</h2>
            <input type="text" id="p" placeholder="Produit">
            <input type="text" id="q" placeholder="Quantité">
            <input type="number" id="sp" placeholder="Prix départ">
            <input type="number" id="mp" placeholder="Prix plancher">
            <input type="number" id="n" step="0.01" placeholder="Indice NDVI Copernicus">
            <button class="btn-add" onclick="saveLot()">AJOUTER AU STOCK</button>
        </div>
        <div class="box">
            <h2>📦 Stock actuel</h2>
            <div id="admin-list"></div>
        </div>
    </div>
    <script>
        function saveLot() {
            const payload = {
                id: "L"+Date.now(),
                product: document.getElementById('p').value,
                quantity: document.getElementById('q').value,
                start_price: parseInt(document.getElementById('sp').value),
                min_price: parseInt(document.getElementById('mp').value),
                ndvi: parseFloat(document.getElementById('n').value)
            };
            fetch('/api/add_lot', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(() => { location.reload(); });
        }
        function start(id) { fetch('/api/start/'+id, {method:'POST'}); }
        function load() {
            fetch('/api/lots').then(r => r.json()).then(data => {
                let h = "";
                for(let id in data) {
                    h += `<div class="lot-row">
                        <span>${data[id].product} (${data[id].current_price} F)</span>
                        <button class="btn-go" onclick="start('${id}')">LANCER</button>
                    </div>`;
                }
                document.getElementById('admin-list').innerHTML = h;
            });
        }
        setInterval(load, 2000);
        load();
    </script>
</body>
</html>
""")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
