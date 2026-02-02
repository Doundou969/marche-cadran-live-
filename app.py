from flask import Flask, render_template_string, jsonify
import time
import threading

app = Flask(__name__)

# =============================
# DONNÉES DES LOTS (TEST)
# =============================
lots = [
    {"id": 1, "produit": "Riz local 50kg", "prix": 20000, "actif": True},
    {"id": 2, "produit": "Oignon 25kg", "prix": 15000, "actif": True},
    {"id": 3, "produit": "Arachide 100kg", "prix": 30000, "actif": True},
]

# =============================
# LOGIQUE ENCHÈRE DESCENDANTE
# =============================
def cadran():
    while True:
        for lot in lots:
            if lot["actif"] and lot["prix"] > 1000:
                lot["prix"] -= 100
        time.sleep(2)

threading.Thread(target=cadran, daemon=True).start()

# =============================
# FRONTEND MULTI-LOTS
# =============================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Marché au Cadran Live</title>
    <style>
        body { font-family: Arial; background:#0f172a; color:white; text-align:center; }
        .lot { background:#111827; padding:20px; margin:15px; border-radius:12px; }
        .prix { font-size:32px; color:#22c55e; }
        button { padding:12px 20px; border:none; border-radius:8px; background:#f59e0b; cursor:pointer; }
    </style>
</head>
<body>

<h1>📉 Marché au Cadran – Live</h1>
<div id="lots"></div>

<script>
function chargerLots() {
    fetch("/api/lots")
        .then(res => res.json())
        .then(data => {
            let html = "";
            data.forEach(lot => {
                html += `
                <div class="lot">
                    <h2>${lot.produit}</h2>
                    <div class="prix">${lot.prix} FCFA</div>
                    ${lot.actif 
                        ? `<button onclick="acheter(${lot.id})">💰 ACHETER</button>`
                        : `<strong>🔴 VENDU</strong>`}
                </div>`;
            });
            document.getElementById("lots").innerHTML = html;
        });
}

function acheter(id) {
    fetch("/acheter/" + id, {method:"POST"})
        .then(() => chargerLots());
}

setInterval(chargerLots, 2000);
chargerLots();
</script>

</body>
</html>
"""

# =============================
# ROUTES
# =============================
@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/api/lots")
def api_lots():
    return jsonify(lots)

@app.route("/acheter/<int:lot_id>", methods=["POST"])
def acheter(lot_id):
    for lot in lots:
        if lot["id"] == lot_id:
            lot["actif"] = False
    return jsonify({"status": "ok"})

# =============================
# RUN
# =============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
