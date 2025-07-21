from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import os
from pathlib import Path

app = Flask(__name__)
CORS(app)  # para que tu front (o Postman) pueda llamarlo

# CONFIG DB
DB = dict(host="localhost", user="root", password="", database="bd_propiedades_inmobiliarias")

def get_conn():
    return mysql.connector.connect(**DB)

@app.route("/")
def index():
    return {"status": "EÓN chatbot API v1.0"}

@app.route("/chat", methods=["POST"])
def chat():
    data   = request.get_json(force=True)
    texto  = data.get("message", "").strip()
    if not texto:
        return jsonify({"reply": "Por favor escribe lo que buscas."})

    conn = get_conn()
    cur  = conn.cursor(dictionary=True)

    # Búsqueda simple por palabras clave
    sql = """
    SELECT titulo, precio, moneda, distrito, area_total, habitaciones, banos, link_detalle
    FROM propiedades
    WHERE (titulo LIKE %s OR descripcion LIKE %s) AND estado='activa'
    ORDER BY fecha_publicacion DESC
    LIMIT 10
    """
    like = f"%{texto}%"
    cur.execute(sql, (like, like))
    props = cur.fetchall()
    cur.close(); conn.close()

    if not props:
        return jsonify({"reply": "No encontré propiedades que coincidan con tu búsqueda 😅"})

    respuesta = f"Encontré {len(props)} opción(es):\n"
    for p in props:
        respuesta += (
            f"- {p['titulo']} | "
            f"{p['moneda']} {p['precio']} | "
            f"{p['distrito']} | "
            f"{p['habitaciones']} hab, {p['banos']} baños | "
            f"{p['link_detalle']}\n"
        )
    return jsonify({"reply": respuesta})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)