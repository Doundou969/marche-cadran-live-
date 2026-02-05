from flask import Flask, jsonify, request, render_template_string
import threading
import time
import uuid
import sqlite3
import os

app = Flask(__name__)
auction_lock = threading.Lock()
DB_NAME = "marche.db"

# ==========================================
# BASE DE DONNÉES
# ==========================================
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS lots (
        id TEXT PRIMARY KEY, product TEXT, quantity TEXT, 
        start_price INTEGER, current_price INTEGER, min_price INTEGER, 
        time_left INTEGER, active BOOLEAN, winner TEXT, 
        pay_method TEXT, pay_ref TEXT, confirmed BOOLEAN, ndvi REAL
    )''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# LOGIQUE DU CADRAN
# ==========================================
def auction_timer(lot_id):
    while True:
        time.sleep(1)
        with auction_lock:
            conn = get_db_connection()
            lot = conn.execute("SELECT * FROM lots WHERE id=?", (lot_id,)).fetchone()
            if not lot or not lot['active'] or lot['time_left'] <= 0:
                conn.close()
                break
            
            new_price = lot['current_price'] - 1
            new_time = lot['time_left'] - 1

            if new_price <= lot['min_price']:
                conn.execute("UPDATE lots SET active=0, winner='Retiré' WHERE id=?", (lot_id,))
                conn.commit()
                conn.close()
                break
            else:
                conn.execute("UPDATE lots SET current_price=?, time_left=? WHERE id=?", (new_price, new_time, lot_id))
                conn.commit()
                conn.close()

# ==========================================
# ROUTES API & LOGIQUE
# ==========================================

@app.route('/lots')
def get_lots():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM lots").fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in rows])

@app.route('/reset')
def reset_db():
    conn = get_db_connection()
    conn.execute('DROP TABLE IF EXISTS lots')
    init_db()
    conn.execute('''INSERT INTO lots (id, product, quantity, start_price, current_price, min_price, time_left, active, confirmed, ndvi)
                    VALUES ('A1', 'Arachide de Kaffrine', '2 Tonnes', 450, 450, 300, 120, 0, 0, 0.78),
                           ('A2', 'Oignon des Niayes', '5 Tonnes', 600, 600, 400, 150, 0, 0, 0.82)''')
    conn.commit()
    conn.close()
    return "✅ Base réinitialisée. Lots A1 et A2 créés. <a href='/'>Retour à l'accueil</a>"

@app.route('/start/<lot_id>', methods=['POST'])
def start_lot(lot_id):
    conn = get_db_connection()
    conn.execute("UPDATE lots SET active=1, winner=NULL, confirmed=0, current_price=start_price, time_left=120 WHERE id=?", (lot_id,))
    conn.commit()
    conn.close()
    threading.Thread(target=auction_timer, args=(lot_id,), daemon=True).start()
    return jsonify({"status": "started"})

@app.route('/buy/<lot_id>', methods=['POST'])
def buy_lot(lot_id):
    data = request.json
    with auction_lock:
        conn = get_db_connection()
        lot = conn.execute("SELECT * FROM lots WHERE id=?", (lot_id,)).fetchone()
        if not lot or not lot['active']:
            return jsonify({"error": "Lot indisponible ou non lancé"}), 400
        
        ref = f"REF-{uuid.uuid4().hex[:8].upper()}"
        conn.execute("UPDATE lots SET active=0, winner=?, pay_method=?, pay_ref=? WHERE id=?", 
                    (data.get('buyer', 'Anonyme'), data.get('method'), ref, lot_id))
        conn.commit()
        conn.close()
        return jsonify({"reference": ref, "amount": lot['current_price'], "method": data.get('method')})

@app.route('/confirm/<lot_id>', methods=['POST'])
def confirm_lot(lot_id):
    conn = get_db_connection()
    conn.execute("UPDATE lots SET confirmed=1 WHERE id=?", (lot_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "Paiement validé"})

# ==========================================
# INTERFACES (HTML INTÉGRÉ)
# ==========================================

@app.route('/')
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <title>Marché au Cadran LIVE</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: sans-serif; background: #f4f7f6; padding: 10px; text-align: center; }
        .card { background: white; padding: 20px; margin: 10px auto; max-width: 400px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-top: 5px solid #2e7d32; }
        .price { font-size: 3em; color: #e63946; font-weight: bold; }
        button { padding: 12px; margin: 5px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; width: 45%; }
        .wave { background: #1da1f2; color: white; }
        .orange { background: #ff6600; color: white; }
        .status { background: #e8f5e9; padding: 10px; border-radius: 8px; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>🟢 Marché Agricole Live</h1>
    <div id="lots-container">Chargement...</div>
    <script>
        function update() {
            fetch('/lots').then(r => r.json()).then(data => {
                let html = "";
                data.forEach(l => {
                    html += `<div class="card">
                        <h3>${l.product}</h3>
                        <p>📦 ${l.quantity} | 🛰 NDVI: ${l.ndvi}</p>
                        <div class="price">${l.current_price} <small>F</small></div>
                        <p>⏱ ${l.time_left}s</p>
                        ${l.winner ? `<div class="status">🔨 VENDU À: ${l.winner}<br>REF: ${l.pay_ref}<br>${l.confirmed ? '✅ PAIEMENT VALIDÉ' : '⏳ Vérification...'}</div>` : `
                        <button class="wave" onclick="buy('${l.id}','wave')">WAVE</button>
                        <button class="orange" onclick="buy('${l.id}','orange')">ORANGE</button>`}
                    </div>`;
                });
                document.getElementById('lots-container').innerHTML = html;
            });
        }
        function buy(id, m) {
            fetch('/buy/'+id, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({method:m})})
            .then(r => r.json()).then(d => d.error ? alert(d.error) : alert("Réserve faite ! REF: "+d.reference));
        }
        setInterval(update, 1000);
    </script>
</body>
</html>
""")

@app.route('/admin')
def admin_page():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Admin - PecheurConnect</title>
    <style>
        body { background: #263238; color: white; font-family: sans-serif; padding: 20px; }
        .lot { background: #37474f; padding: 15px; margin: 10px 0; border-radius: 8px; display: flex; justify-content: space-between; }
        button { background: #4caf50; color: white; border: none; padding: 8px 15px; cursor: pointer; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>🛠 Console Administrateur</h1>
    <div id="admin-list"></div>
    <script>
        function refresh() {
            fetch('/lots').then(r => r.json()).then(data => {
                let html = "";
                data.forEach(l => {
                    html += `<div class="lot">
                        <span>${l.product} (${l.current_price} F)</span>
                        <div>
                            ${!l.active && !l.winner ? `<button onclick="start('${l.id}')">🚀 LANCER</button>` : ''}
                            ${l.winner && !l.confirmed ? `<button style="background:orange" onclick="conf('${l.id}')">✅ CONFIRMER PAIEMENT</button>` : ''}
                        </div>
                    </div>`;
                });
                document.getElementById('admin-list').innerHTML = html;
            });
        }
        function start(id) { fetch('/start/'+id, {method:'POST'}).then(refresh); }
        function conf(id) { fetch('/confirm/'+id, {method:'POST'}).then(refresh); }
        setInterval(refresh, 2000);
        refresh();
    </script>
</body>
</html>
""")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
