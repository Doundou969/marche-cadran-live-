from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import threading
import time

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret-key"

# ⚠️ PAS de async_mode forcé
socketio = SocketIO(app, cors_allowed_origins="*")

auction = {
    "active": False,
    "product": "Arachide grade A – Kaolack",
    "quantity": "500 kg",
    "start_price": 350,
    "current_price": 350,
    "min_price": 250,
    "time_left": 120,
    "bids": [],
    "winner": None
}

def auction_timer():
    while auction["active"] and auction["time_left"] > 0:
        time.sleep(1)
        auction["time_left"] -= 1
        if auction["current_price"] > auction["min_price"]:
            auction["current_price"] -= 1
        socketio.emit("update", auction)

    auction["active"] = False
    socketio.emit("update", auction)

@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Marché au Cadran Live</title>
<script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
<style>
body { font-family: Arial; background:#f5f6fa; text-align:center }
.card { background:#fff; padding:20px; max-width:420px; margin:auto; border-radius:12px }
.price { font-size:46px; color:#e74c3c }
button { padding:12px 20px; font-size:16px }
</style>
</head>
<body>

<h2>🛒 Marché au Cadran – Live</h2>

<div class="card">
  <h3 id="product"></h3>
  <p id="quantity"></p>
  <div class="price" id="price"></div>
  <p>⏱️ <span id="time"></span> secondes</p>
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
  socket.emit("bid", "Acheteur-" + Math.floor(Math.random()*1000));
}
</script>

</body>
</html>
""")

@socketio.on("connect")
def connect():
    emit("update", auction)

@socketio.on("bid")
def bid(name):
    if auction["active"]:
        auction["bids"].append(name)
        auction["winner"] = name
        socketio.emit("update", auction)

@socketio.on("start")
def start():
    if not auction["active"]:
        auction["active"] = True
        auction["current_price"] = auction["start_price"]
        auction["time_left"] = 120
        auction["bids"] = []
        threading.Thread(target=auction_timer, daemon=True).start()

if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        allow_unsafe_werkzeug=True
    )
