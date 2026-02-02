from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret123"

# ✅ MODE COMPATIBLE PYTHON 3.13 (PAS EVENTLET)
socketio = SocketIO(app, cors_allowed_origins="*")

# 🔹 Données en mémoire (MVP)
lots = [
    {"id": 1, "nom": "Arachide Grade A", "prix": 500},
    {"id": 2, "nom": "Mil Local", "prix": 300},
    {"id": 3, "nom": "Maïs Séché", "prix": 250},
]

@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Marché au Cadran Live</title>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <style>
        body { font-family: Arial; background: #f7f7f7; padding: 20px; }
        .lot { background: white; padding: 15px; margin-bottom: 10px; border-radius: 8px; }
        button { padding: 6px 10px; }
    </style>
</head>
<body>

<h1>📡 Marché au Cadran Live</h1>

<div id="lots"></div>

<script>
const socket = io();

const lotsDiv = document.getElementById("lots");

socket.on("connect", () => {
    console.log("🟢 Connecté au serveur");
});

socket.on("update_lots", (data) => {
    lotsDiv.innerHTML = "";
    data.forEach(lot => {
        lotsDiv.innerHTML += `
            <div class="lot">
                <strong>${lot.nom}</strong><br>
                💰 Prix : <span>${lot.prix}</span> FCFA<br>
                <button onclick="enchere(${lot.id})">Acheter</button>
            </div>
        `;
    });
});

function enchere(id) {
    socket.emit("new_bid", { lot_id: id });
}
</script>

</body>
</html>
""")

@socketio.on("connect")
def handle_connect():
    emit("update_lots", lots)

@socketio.on("new_bid")
def handle_new_bid(data):
    lot_id = data.get("lot_id")
    for lot in lots:
        if lot["id"] == lot_id:
            lot["prix"] += 25
    socketio.emit("update_lots", lots)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
