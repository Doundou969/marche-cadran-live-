from flask import Flask, render_template_string, jsonify, request
import threading, time, uuid

app = Flask(__name__)

# =============================
# DONNÉES DES LOTS
# =============================
lots = [
    {
        "id": 1,
        "produit": "Arachide 1er qualité – Diourbel",
        "prix_depart": 350,
        "prix": 350,
        "min_prix": 250,
        "time_left": 300,
        "actif": True,
        "winner": None,
        "payment": None
    },
    {
        "id": 2,
        "produit": "Arachide – Bambey",
        "prix_depart": 340,
        "prix": 340,
        "min_prix": 240,
        "time_left": 300,
        "actif": True,
        "winner": None,
        "payment": None
    }
]

# =============================
# TIMER ENCHÈRE DESCENDANTE
# =============================
def timer_lot(lot):
    while lot["actif"] and lot["time_left"] > 0:
        time.sleep(1)
        lot["time_left"] -= 1
        if lot["prix"] > lot["min_prix"]:
            lot["prix"] -= 1
    if lot["actif"]:
        lot["actif"] = False
        lot["winner"] = "Aucun acheteur"

def start_lot_thread(lot):
    threading.Thread(target=timer_lot, args=(lot,), daemon=True).start()

# =============================
# ROUTES API
# =============================
@app.route("/api/lots")
def api_lots():
    return jsonify(lots)

@app.route("/start/<int:lot_id>", methods=["POST"])
def start_lot(lot_id):
    for lot in lots:
        if lot["id"] == lot_id:
            lot["actif"] = True
            lot["prix"] = lot["prix_depart"]
            lot["time_left"] = 300
            lot["winner"] = None
            lot["payment"] = None
            start_lot_thread(lot)
            return jsonify({"status":"lot démarré"})
    return jsonify({"error":"Lot non trouvé"}),404

@app.route("/acheter/<int:lot_id>/<string:methode>", methods=["POST"])
def acheter(lot_id, methode):
    for lot in lots:
        if lot["id"] == lot_id and lot["actif"]:
            ref = "MC-" + str(uuid.uuid4())[:8].upper()
            lot["actif"] = False
            lot["winner"] = "Acheteur Live"
            lot["payment"] = {"method": methode, "reference": ref, "status": "pending"}
            return jsonify({
                "status":"pending_payment",
                "reference": ref,
                "amount": lot["prix"],
                "method": methode
            })
    return jsonify({"error":"Lot inactif"}),400

# =============================
# DASHBOARD ADMIN
# =============================
@app.route("/admin")
def admin():
    html = "<h1>Admin Marché Cadran</h1>"
    for lot in lots:
        html += f"""
        <div style='padding:10px;border:1px solid #ccc;margin:5px;'>
        <strong>{lot['produit']}</strong> | Prix: {lot['prix']} FCFA<br>
        Statut: {"Vendu à " + lot['winner'] if lot['winner'] else "Actif"}<br>
        Paiement: {lot['payment']['status'] if lot['payment'] else "-"}<br>
        Méthode: {lot['payment']['method'] if lot['payment'] else "-"}<br>
        Référence: {lot['payment']['reference'] if lot['payment'] else "-"}
        </div>
        """
    return html

# =============================
# FRONTEND (MULTI-LOTS LIVE)
# =============================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Marché au Cadran Live</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body { font-family: Arial,sans-serif; background:#0f172a; color:white; text-align:center; }
h1 { margin:10px; }
.lot { background:#111827; padding:18px; margin:12px auto; max-width:420px; border-radius:12px; }
.prix { font-size:28px; color:#22c55e; font-weight:bold; margin:6px 0; }
button { padding:10px 16px; margin:4px; border:none; border-radius:8px; cursor:pointer; font-size:1em; }
.start { background:#2a9d8f; color:white; }
.wave { background:#1da1f2; color:white; }
.orange { background:#f77f00; color:white; }
.sold { color:#4ade80; font-weight:bold; }
</style>
</head>
<body>

<h1>🔴 Marché au Cadran – LIVE</h1>
<div id="lots">Chargement…</div>

<script>
function chargerLots(){
  fetch("/api/lots").then(r=>r.json()).then(data=>{
    let html="";
    data.forEach(lot=>{
      html += `<div class="lot">
        <h2>${lot.produit}</h2>
        <div class="prix">${lot.prix} FCFA</div>
        <div>⏱ ${lot.time_left} sec</div>
        ${
          lot.actif
          ? `<button class="start" onclick="demarrerLot(${lot.id})">🚀 Démarrer</button>
             <button class="wave" onclick="acheter(${lot.id},'wave')">💙 Wave</button>
             <button class="orange" onclick="acheter(${lot.id},'orange')">🟠 Orange</button>`
          : lot.winner ? `<div class="sold">🔨 VENDU à ${lot.winner}<br>Réf: ${lot.payment.reference}</div>` : ""
        }
      </div>`;
    });
    document.getElementById("lots").innerHTML = html;
  });
}

function demarrerLot(id){ fetch("/start/"+id,{method:"POST"}); }
function acheter(id,methode){ fetch("/acheter/"+id+"/"+methode,{method:"POST"})
  .then(r=>r.json()).then(d=>{
    alert("💳 PAIEMENT À EFFECTUER\\nMéthode: "+d.method.toUpperCase()+"\\nMontant: "+d.amount+" FCFA\\nRéf: "+d.reference);
    chargerLots();
  });
}

setInterval(chargerLots,1000);
chargerLots();
</script>

</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

# =============================
# RUN
# =============================
if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
