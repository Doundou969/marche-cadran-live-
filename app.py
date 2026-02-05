from flask import Flask, jsonify, request, render_template_string
import threading
import time
import uuid

app = Flask(__name__)
auction_lock = threading.Lock()

# =========================================================
# BASE DE DONNÉES (En mémoire pour l'exemple)
# =========================================================
lots = [
    {
        "id": "A1",
        "product": "Arachide de Boulel - Kaffrine",
        "quantity": "2 Tonnes",
        "start_price": 450,
        "current_price": 450,
        "min_price": 300,
        "time_left": 120,
        "active": False,
        "winner": None,
        "payment": None,
        "confirmed": False,
        "ndvi": 0.78  # Donnée Copernicus (Qualité de végétation)
    },
    {
        "id": "A2",
        "product": "Oignon des Niayes (Local)",
        "quantity": "5 Tonnes",
        "start_price": 600,
        "current_price": 600,
        "min_price": 400,
        "time_left": 150,
        "active": False,
        "winner": None,
        "payment": None,
        "confirmed": False,
        "ndvi": 0.82
    }
]

# =========================================================
# LOGIQUE DU CADRAN DÉGRESSIF
# =========================================================
def auction_timer(lot_id):
    while True:
        time.sleep(1)
        with auction_lock:
            lot = next((l for l in lots if l["id"] == lot_id), None)
            if not lot or not lot["active"] or lot["time_left"] <= 0:
                break
            
            lot["current_price"] -= 1
            lot["time_left"] -= 1

            if lot["current_price"] <= lot["min_price"]:
                lot["active"] = False
                lot["winner"] = "Lot retiré (Prix min)"
                break

# =========================================================
# ROUTES API & GESTION DES TRANSACTIONS
# =========================================================

@app.route('/lots')
def get_lots():
    return jsonify(lots)

@app.route('/start/<lot_id>', methods=['POST'])
def start_lot(lot_id):
    lot = next((l for l in lots if l["id"] == lot_id), None)
    if lot and not lot["active"] and not lot["winner"]:
        lot["active"] = True
        lot["time_left"] = 120
        threading.Thread(target=auction_timer, args=(lot_id,), daemon=True).start()
    return jsonify({"status": "ok"})

@app.route('/buy/<lot_id>', methods=['POST'])
def buy_lot(lot_id):
    data = request.json
    with auction_lock:
        lot = next((l for l in lots if l["id"] == lot_id), None)
        if lot and lot["active"]:
            lot["active"] = False
            lot["winner"] = data.get('buyer', 'Client Live')
            ref = f"REF-{uuid.uuid4().hex[:8].upper()}"
            lot["payment"] = {
                "method": data.get('method'),
                "amount": lot["current_price"],
                "reference": ref
            }
            return jsonify(lot["payment"])
    return jsonify({"error": "Lot expiré ou déjà vendu"}), 400

@app.route('/confirm/<lot_id>', methods=['POST'])
def confirm_lot(lot_id):
    lot = next((l for l in lots if l["id"] == lot_id), None)
    if lot and lot["payment"]:
        lot["confirmed"] = True
    return jsonify({"status": "Paiement validé"})

# =========================================================
# INTERFACE CLIENT (Paiements Mobiles)
# =========================================================
@app.route('/')
def client_view():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Marché Cadran - Sénégal 2026</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f4f6f8; margin: 0; padding: 10px; }
        h1 { text-align: center; color: #1b5e20; }
        .auction { background: white; padding: 20px; margin: 15px auto; max-width: 450px; border-radius: 15px; box-shadow: 0 8px 20px rgba(0,0,0,0.1); border-top: 5px solid #2e7d32; }
        .price { font-size: 3em; font-weight: bold; color: #d32f2f; margin: 10px 0; }
        .timer { font-size: 1.2em; color: #f57c00; font-weight: bold; }
        .copernicus { font-size: 0.8em; color: #2e7d32; background: #e8f5e9; padding: 5px; border-radius: 5px; }
        button { padding: 12px; font-size: 1em; border: none; border-radius: 8px; margin: 5px; cursor: pointer; width: 45%; font-weight: bold; }
        .wave { background: #1da1f2; color: white; }
        .orange { background: #ff6600; color: white; }
        .sold { color: #2e7d32; background: #e8f5e9; padding: 15px; border-radius: 10px; text-align: center; }
        .btn-pdf { background: #2e7d32; color: white; width: 100%; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>🟢 Marché au Cadran LIVE</h1>
    <div id="lots">Chargement...</div>

    <script>
        function refresh(){
            fetch('/lots').then(r => r.json()).then(data => {
                let html = "";
                data.forEach(lot => {
                    html += `<div class="auction">
                        <h3>${lot.product}</h3>
                        <div class="copernicus">🛰 Qualité Copernicus (NDVI): ${lot.ndvi}</div>
                        <p><strong>Quantité :</strong> ${lot.quantity}</p>
                        <div class="price">${lot.current_price} <small>FCFA/kg</small></div>
                        <div class="timer">⏱ ${lot.time_left} sec</div>
                        ${lot.winner ? `
                            <div class="sold">
                                🔨 VENDU À : ${lot.winner}<br>
                                <strong>Réf: ${lot.payment.reference}</strong><br>
                                ${lot.confirmed ? 
                                    `<p>✅ PAIEMENT REÇU</p><button class="btn-pdf" onclick="window.open('/receipt/${lot.id}')">📄 TÉLÉCHARGER LE REÇU</button>` : 
                                    "<p>⏳ En attente de validation...</p>"}
                            </div>` : `
                            <button class="wave" onclick="buy('${lot.id}','wave')">💙 WAVE</button>
                            <button class="orange" onclick="buy('${lot.id}','orange')">🟠 ORANGE</button>
                        `}
                    </div>`;
                });
                document.getElementById("lots").innerHTML = html;
            });
        }
        function buy(id, method){
            fetch('/buy/'+id, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({buyer: 'Client Mobile', method: method})
            }).then(r => r.json()).then(d => {
                alert("🛒 COMMANDE RÉSERVÉE\\n\\nPayez " + d.amount + " FCFA via " + method.toUpperCase() + "\\nRéférence: " + d.reference);
            });
        }
        setInterval(refresh, 1000);
    </script>
</body>
</html>
""")

# =========================================================
# DASHBOARD ADMIN (Validation Paiements)
# =========================================================
@app.route('/admin')
def admin_view():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Admin - Validation</title>
    <style>
        body { font-family: sans-serif; background: #263238; color: white; padding: 20px; }
        .card { background: #37474f; padding: 15px; margin: 10px; border-radius: 10px; border-left: 10px solid orange; }
        .confirmed { border-left-color: #4caf50; opacity: 0.6; }
        button { background: #4caf50; color: white; border: none; padding: 10px; cursor: pointer; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>🛠 Validation des Transferts (Wave/Orange)</h1>
    <div id="admin-list"></div>
    <script>
        function load(){
            fetch('/lots').then(r => r.json()).then(data => {
                let h = "";
                data.filter(l => l.winner && l.payment).forEach(lot => {
                    h += `<div class="card ${lot.confirmed ? 'confirmed' : ''}">
                        <h3>Lot: ${lot.product}</h3>
                        <p>Acheteur: ${lot.winner} | Réf: <strong>${lot.payment.reference}</strong></p>
                        <p>Montant: ${lot.payment.amount} FCFA (${lot.payment.method})</p>
                        ${lot.confirmed ? "✅ VALIDÉ" : `<button onclick="confirm('${lot.id}')">CONFIRMER RÉCEPTION ARGENT</button>`}
                    </div>`;
                });
                document.getElementById("admin-list").innerHTML = h || "Aucun paiement en attente.";
            });
        }
        function confirm(id){ fetch('/confirm/'+id, {method:'POST'}).then(load); }
        setInterval(load, 2000);
    </script>
</body>
</html>
""")

# =========================================================
# GÉNÉRATION DE REÇU (Simulation PDF/Print)
# =========================================================
@app.route('/receipt/<lot_id>')
def get_receipt(lot_id):
    lot = next((l for l in lots if l["id"] == lot_id), None)
    if not lot or not lot["confirmed"]: return "Accès refusé", 403
    return render_template_string("""
        <body style="font-family: sans-serif; text-align: center; padding: 50px; border: 5px solid #2e7d32;">
            <h1 style="color: #2e7d32;">REÇU DE VENTE - Marché au Cadran</h1>
            <hr>
            <h2>PRODUIT : {{ lot.product }}</h2>
            <p><strong>RÉFÉRENCE DE PAIEMENT :</strong> {{ lot.payment.reference }}</p>
            <p><strong>QUANTITÉ :</strong> {{ lot.quantity }}</p>
            <p><strong>MONTANT PAYÉ :</strong> {{ lot.payment.amount }} FCFA/kg</p>
            <p><strong>MÉTHODE :</strong> {{ lot.payment.method | upper }}</p>
            <br>
            <div style="background: #e8f5e9; padding: 20px;">
                <strong>CERTIFICATION COPERNICUS (NDVI): {{ lot.ndvi }}</strong><br>
                Ce produit respecte les standards de qualité environnementale 2026.
            </div>
            <p>Date: {{ date }}</p>
            <button onclick="window.print()">Imprimer le Reçu</button>
        </body>
    """, lot=lot, date=time.strftime('%d/%m/%Y %H:%M'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
