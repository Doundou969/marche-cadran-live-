from flask import Flask, jsonify, request, render_template_string
import threading
import time
import uuid

app = Flask(__name__)

# =====================
# DONNÉES : MULTI-LOTS
# =====================
lots = [
    {
        "id": "LOT1",
        "product": "Arachide 1er qualité – Diourbel",
        "quantity": "500 kg",
        "start_price": 350,
        "current_price": 350,
        "min_price": 250,
        "time_left": 300,
        "active": False,
        "winner": None,
        "winner_price": None,
        "payment": None
    },
    {
        "id": "LOT2",
        "product": "Arachide – Bambey",
        "quantity": "1 tonne",
        "start_price": 340,
        "current_price": 340,
        "min_price": 240,
        "time_left": 300,
        "active": False,
        "winner": None,
        "winner_price": None,
        "payment": None
    }
]

# =====================
# TIMER PAR LOT
# =====================
def start_timer(lot):
    while lot["active"] and lot["time_left"] > 0:
        time.sleep(1)
        lot["time_left"] -= 1
        if lot["current_price"] > lot["min_price"]:
            lot["current_price"] -= 1

    if lot["active"]:
        lot["active"] = False
        lot["winner"] = "Aucun acheteur"

# =====================
# ROUTES API
# =====================
@app.route('/lots')
def get_lots():
    return jsonify(lots)

@app.route('/start/<lot_id>', methods=['POST'])
def start_lot(lot_id):
    for lot in lots:
        if lot["id"] == lot_id:
            lot["active"] = True
            lot["current_price"] = lot["start_price"]
            lot["time_left"] = 300
            lot["winner"] = None
            lot["payment"] = None
            threading.Thread(target=start_timer, args=(lot,), daemon=True).start()
            return jsonify({"status": "started"})
    return jsonify({"error": "Lot not found"}), 404

@app.route('/buy/<lot_id>', methods=['POST'])
def buy_lot(lot_id):
    data = request.json
    buyer = data.get("buyer")
    method = data.get("method")  # wave / orange

    for lot in lots:
        if lot["id"] == lot_id and lot["active"]:
            ref = "MC-" + str(uuid.uuid4())[:8].upper()
            lot["active"] = False
            lot["winner"] = buyer
            lot["winner_price"] = lot["current_price"]
            lot["payment"] = {
                "method": method,
                "reference": ref,
                "status": "pending"
            }
            return jsonify({
                "status": "pending_payment",
                "reference": ref,
                "amount": lot["winner_price"],
                "method": method
            })

    return jsonify({"error": "Lot inactive"}), 400

# =====================
# FRONTEND (HTML INLINE)
# =====================
@app.route('/')
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Marché au Cadran Live</title>
<meta name="viewport" content="width=device-width">
<style>
body { font-family: Arial; background:#f4f6f8; }
.auction { background:white; padding:20px; margin:15px auto;
           max-width:420px; border-radius:15px;
           box-shadow:0 10px 20px rgba(0,0,0,.1); }
.price { font-size:2.8em; color:#e63946; font-weight:bold; }
button { padding:12px 18px; border:none; border-radius:8px;
         font-size:1em; margin:5px; cursor:pointer; }
.start { background:#2a9d8f; color:white; }
.wave { background:#1da1f2; color:white; }
.orange { background:#f77f00; color:white; }
</style>
</head>
<body>

<h1 style="text-align:center;">🔴 Marché au Cadran LIVE</h1>
<div id="lots"></div>

<script>
function refresh(){
 fetch('/lots').then(r=>r.json())
