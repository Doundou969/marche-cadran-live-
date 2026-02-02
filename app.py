from flask import Flask, render_template_string, jsonify, request
import threading
import time

app = Flask(__name__)

live_auction = {
    'active': False,
    'product': 'Arachide 1er qualité – Diourbel',
    'quantity': '500 kg',
    'start_price': 350,
    'current_price': 350,
    'min_price': 250,
    'time_left': 300,
    'winner': None,
    'winner_price': None
}

def auction_timer():
    while live_auction['active'] and live_auction['time_left'] > 0:
        time.sleep(1)
        live_auction['time_left'] -= 1
        if live_auction['current_price'] > live_auction['min_price']:
            live_auction['current_price'] -= 1

    if live_auction['active']:
        live_auction['active'] = False
        live_auction['winner'] = "Aucun acheteur"
        live_auction['winner_price'] = None

@app.route('/')
def dashboard():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Marché Cadran Live</title>
<meta name="viewport" content="width=device-width">
<style>
body { font-family: Arial; background:#f4f7fb; text-align:center; }
.auction { background:white; padding:25px; border-radius:15px; max-width:420px; margin:auto; box-shadow:0 10px 25px rgba(0,0,0,.1); }
.price { font-size:3.5em; color:#e63946; font-weight:bold; }
.timer { font-size:1.5em; color:#f77f00; }
button { padding:15px 25px; font-size:1.1em; border:none; border-radius:10px; cursor:pointer; margin:5px; }
.start { background:#2a9d8f; color:white; }
.bid { background:#e63946; color:white; }
.sold { color:green; font-size:1.3em; font-weight:bold; }
</style>
</head>
<body>

<h1>🔴 LIVE – Marché au Cadran</h1>

<div class="auction">
    <h2 id="product"></h2>
    <p>Quantité : <strong id="quantity"></strong></p>

    <div class="price" id="price"></div>
    <div class="timer">⏱ <span id="time"></span> sec</div>

    <div id="status"></div>

    <button class="start" onclick="startAuction()">🚀 Démarrer</button>
    <button class="bid" onclick="bid()">💰 ACHETER MAINTENANT</button>
</div>

<script>
function refresh(){
 fetch('/auction').then(r=>r.json()).then(d=>{
   document.getElementById('product').innerText = d.product;
   document.getElementById('quantity').innerText = d.quantity;
   document.getElementById('price').innerText = d.current_price + " FCFA/kg";
   document.getElementById('time').innerText = d.time_left;

   if(d.winner){
     document.getElementById('status').innerHTML =
       "<div class='sold'>🔨 VENDU à " + d.winner +
       "<br>Prix : " + d.winner_price + " FCFA/kg</div>";
   }
 });
}
setInterval(refresh,1000);

function startAuction(){
 fetch('/start',{method:'POST'});
}

function bid(){
 fetch('/bid',{
   method:'POST',
   headers:{'Content-Type':'application/json'},
   body:JSON.stringify({buyer:"Acheteur "+Math.floor(Math.random()*100)})
 });
}
</script>
</body>
</html>
""")

@app.route('/auction')
def auction():
    return jsonify(live_auction)

@app.route('/start', methods=['POST'])
def start():
    live_auction.update({
        'active': True,
        'current_price': live_auction['start_price'],
        'time_left': 300,
        'winner': None,
        'winner_price': None
    })
    threading.Thread(target=auction_timer, daemon=True).start()
    return jsonify({"status":"started"})

@app.route('/bid', methods=['POST'])
def bid():
    if not live_auction['active']:
        return jsonify({"error":"Auction inactive"}), 400

    buyer = request.json.get('buyer')
    live_auction['active'] = False
    live_auction['winner'] = buyer
    live_auction['winner_price'] = live_auction['current_price']
    return jsonify({"status":"sold"})

if __name__ == "__main__":
    print("🚀 Marché au Cadran LIVE prêt")
    app.run(host="0.0.0.0", port=5000, debug=True)

