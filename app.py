from flask import Flask, jsonify, request, render_template_string
import threading
import time
import uuid
import sqlite3
import os

app = Flask(__name__)
auction_lock = threading.Lock()
DB_NAME = "marche.db"

# =========================
# INITIALISATION DB
# =========================
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

# =========================
# LOGIQUE DU CADRAN
# =========================
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
                conn.execute("UPDATE lots SET current_price=?, time_left=? WHERE id=?", 
                            (new_price, new_time, lot_id))
                conn.commit()
                conn.close()

# =========================
# ROUTES API AVEC LOGS
# =========================

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
    return "✅ Base réinitialisée. Lots A1 et A2 créés."

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
        
        if not lot:
            return jsonify({"error": f"Le lot {lot_id} n'existe pas en base."}), 400
        if not lot['active']:
            return jsonify({"error": "L'enchère n'est pas lancée ou est déjà terminée."}), 400
        
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
