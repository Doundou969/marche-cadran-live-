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
# API
# =====================
@app.route("/lots")
def get_lots():
    return jsonify(lots)

@app.route("/start/<lot_id>", methods=["POST"])
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

@app.route("/buy/<lot_id>", methods=["POST"])
def buy_lot(lot_id):
    data = request.json
    buyer = data.get("buyer")
    method = data.get("method")

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
# FRONTEND (HTML SÛR)
# =====================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Marché au Cadran Live</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
body { font-family: Arial, sans-serif; background:#f4f6f8; margin:0; padding:10px; }
h1 { text-align:center; }
.auction {
  background:#fff; padding:18px; margin:15px auto; max-width:420px;
  border-radius:15px; box-shadow:0 8px 20px rgba(0,0,0,.1);
}
.price { font-size:2.6em; color:#e63946; font-weight:bold; }
.timer { color:#f77f00; }
button {
  padding:12px 18px; margin:6px 4px;
  border:none; border-radius:8px; font-size:1em; cursor:pointer;
}
.start { background:#2a9d8f; color:white; }
.wave { background:#1da1f2; color:white; }
.orange { background:#f77f00; color:white; }
.sold { color:green; font-weight:bold; }
</style>
</head>

<body>

<h1>🔴 Marché au Cadran LIVE</h1>
<div id="lots">Chargement…</div>

<script>
function refreshLots(){
  fetch('/lots')
    .then(r => r.json())
    .then(data => {
      let html = '';
      data.forEach(lot => {
        html += `
        <div class="auction">
          <h3>${lot.product}</h3>
          <p>Quantité : <strong>${lot.quantity}</strong></p>
          <div class="price">${lot.current_price} FCFA/kg</div>
          <div class="timer">⏱ ${lot.time_left} sec</div>

          ${
            lot.winner
            ? `<div class="sold">🔨 VENDU à ${lot.winner}<br>
               ${lot.payment ? 'Réf : ' + lot.payment.reference : ''}</div>`
            : `<button class="start" onclick="startLot('${lot.id}')">🚀 Démarrer</button><br>
               <button class="wave" onclick="buyLot('${lot.id}','wave')">💙 Wave</button>
               <button class="orange" onclick="buyLot('${lot.id}','orange')">🟠 Orange</button>`
          }
        </div>`;
      });
      document.getElementById("lots").innerHTML = html;
    });
}

setInterval(refreshLots, 1000);
refreshLots();

function startLot(id){
  fetch('/start/' + id, {method:'POST'});
}

function buyLot(id, method){
  fetch('/buy/' + id, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({buyer:'Acheteur Live', method:method})
  })
  .then(r => r.json())
  .then(d => {
    alert(
      "PAIEMENT À EFFECTUER\\n" +
      "Méthode : " + d.method.toUpperCase() + "\\n" +
      "Montant : " + d.amount + " FCFA/kg\\n" +
      "Référence : " + d.reference
    );
  });
}
</script>

</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

# =====================
# RUN
# =====================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
