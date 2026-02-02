from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import threading
import time

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

# ===== ÉTAT GLOBAL =====
auction = {
    "active": False,
    "product": "Arachide 1er qualité - Diourbel",
    "quantity": "500 kg",
    "start_price": 350,
    "current_price": 350,
    "min_price": 250,
    "time_left": 300,
    "bids": [],
    "winner": None
}

# ===== TIMER =====
def auction_timer():
    while auction["active"] and auction["time_left"] > 0:
        time.sleep(1)
        auction["time_left"] -= 1
        if auction["current_price"] > auction["min_price"]:
            auction["current_price"] -= 1

        socketio.emit("update", auction)

    auction["active"] = False
    auction["winner"] = auction["bids"][0] if auction["bids"] else "Aucun acheteur"
    socketio.emit("update", auction)

# ===== ROUTE =====
@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Marché Cadran Live</title>
<script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
<style>
body { font-family: Arial; background:#f4f6f8; text-align:center }
.card { background:white; padding:20px; max-width:420px; margin:auto; border-radius:12px }
.price { font-size:48px; color:red }
</style>
</head>
<body>

<h2>🛒 Marché Cadran Live</h2>

<div class="card">
  <h3 id="product"></h3>
  <p id="quantity"></p>
  <div class="price" id="price"></div>
  <p>⏱️ <span id="time"></span> sec</p>
  <button onclick="bid()">💰 Enchérir</button>
</div>

<script>
const socket = io();

socket.on("update", data => {
  document.getElementById("product").innerText = data.product;
  document.getElementById("quantity").innerText = data.quantity;
  document.getElementById("price").innerText = data.current_price + " FCFA/kg";
  document.getElementById("time").innerText = data.time_left;
});

function bid(){
  socket.emit("bid", "Acheteur " + Math.floor(Math.random()*100));
}
</script>

</body>
</html>
""")

# ===== SOCKET EVENTS =====
@socketio.on("connect")
def connect():
    emit("update", auction)

@socketio.on("bid")
def handle_bid(name):
    if auction["active"]:
        auction["bids"].append(name)
        auction["winner"] = name
        socketio.emit("update", auction)

@socketio.on("start")
def start():
    if not auction["active"]:
        auction["active"] = True
        auction["current_price"] = auction["start_price"]
        auction["time_left"] = 300
        auction["bids"] = []
        auction["winner"] = None
        threading.Thread(target=auction_timer, daemon=True).start()

# ===== RUN (CORRECTION CRITIQUE) =====
if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        allow_unsafe_werkzeug=True
    )
