from flask import Flask, jsonify, request, render_template_string
import threading
import time

app = Flask(__name__)

# =========================
# DONNÉES MULTI-LOTS
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
        "bids": []
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
        "bids": []
    }
}

# =========================
# TIMER DÉGRESSIF
# =========================
def auction_timer(lot_id):
    while lots[lot_id]["active"] and lots[lot_id]["time_left"] > 0:
        time.sleep(1)
        lots[lot_id]["current_price"] -= 1
        lots[lot_id]["time_left"] -= 1

        if lots[lot_id]["current_price"] <= lots[lot_id]["min_price"]:
            break

    lots[lot_id]["active"] = False
    lots[lot_id]["winner"] = (
        lots[lot_id]["bids"][-1] if lots[lot_id]["bids"] else "Aucun acheteur"
    )

# =========================
# FRONT LIVE (MULTI-LOTS)
# =========================
@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Marché Cadran Live</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{font-family:Arial;background:#f5f5f5}
.card{background:white;padding:20px;margin:15px;border-radius:12px}
.price{font-size:2.5em;color:red}
button{padding:12px 20px;font-size:1em}
</style>
</head>
<body>
<h1>🛒 Marché au Cadran Live</h1>
<div id="lots"></div>

<script>
function loadLots(){
 fetch("/api/lots")
 .then(r=>r.json())
 .then(data=>{
   let html="";
   for(let id in data){
     let l=data[id];
     html+=`
     <div class="card">
       <h2>${l.product}</h2>
       <p>Quantité: ${l.quantity}</p>
       <div class="price">${l.current_price} FCFA/kg</div>
       <p>⏱ ${l.time_left}s</p>
       <p>👤 Enchères: ${l.bids.length}</p>
       <button onclick="bid('${id}')">💰 Enchérir</button>
       ${l.winner ? "<p>🏆 Vainqueur: "+l.winner+"</p>" : ""}
     </div>`;
   }
   document.getElementById("lots").innerHTML=html;
 })
}
function bid(id){
 fetch("/api/bid/"+id,{method:"POST"})
}
setInterval(loadLots,1000);
loadLots();
</script>
</body>
</html>
""")

# =========================
# API
# =========================
@app.route("/api/lots")
def get_lots():
    return jsonify(lots)

@app.route("/api/start/<lot_id>", methods=["POST"])
def start_lot(lot_id):
    if lot_id in lots:
        lots[lot_id]["active"] = True
        lots[lot_id]["current_price"] = lots[lot_id]["start_price"]
        lots[lot_id]["time_left"] = 180
        lots[lot_id]["bids"] = []
        lots[lot_id]["winner"] = None
        threading.Thread(target=auction_timer, args=(lot_id,), daemon=True).start()
        return jsonify({"status": "started"})
    return jsonify({"error": "lot not found"}), 404

@app.route("/api/bid/<lot_id>", methods=["POST"])
def bid(lot_id):
    if lot_id in lots and lots[lot_id]["active"]:
        bidder = request.remote_addr
        lots[lot_id]["bids"].append(bidder)
        return jsonify({"status": "ok"})
    return jsonify({"error": "inactive"}), 400

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
