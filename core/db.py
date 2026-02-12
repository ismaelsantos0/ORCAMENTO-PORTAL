import os
import sqlite3

DB_PATH = "data/db.sqlite"

def get_conn():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS precos (
            chave TEXT PRIMARY KEY,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            modulo TEXT,
            categoria TEXT,
            unidade TEXT
        )
    """)
    return conn

def get_price(conn, key):
    cur = conn.execute("SELECT valor FROM precos WHERE chave=?", (key,))
    row = cur.fetchone()
    return float(row[0]) if row else 0.0

def upsert_item(conn, key, desc, value, modulo, categoria, unidade):
    conn.execute("""
        INSERT INTO precos (chave, descricao, valor, modulo, categoria, unidade)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(chave) DO UPDATE SET
            descricao=excluded.descricao,
            valor=excluded.valor,
            modulo=excluded.modulo,
            categoria=excluded.categoria,
            unidade=excluded.unidade
    """, (key, desc, value, modulo, categoria, unidade))
    conn.commit()

def list_items(conn, modulo=None, keys=None):
    q = "SELECT chave, descricao, valor, modulo, categoria, unidade FROM precos"
    params = []
    where = []

    if modulo:
        where.append("modulo=?")
        params.append(modulo)

    if keys:
        placeholders = ",".join(["?"] * len(keys))
        where.append(f"chave IN ({placeholders})")
        params.extend(keys)

    if where:
        q += " WHERE " + " AND ".join(where)

    q += " ORDER BY categoria, descricao"
    return conn.execute(q, params).fetchall()
