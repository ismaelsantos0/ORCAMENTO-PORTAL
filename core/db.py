import os
import sqlite3
from typing import List, Optional, Tuple

DB_PATH = os.getenv("DB_PATH", "data/db.sqlite")


def get_conn() -> sqlite3.Connection:
    """
    SQLite local. Em Railway isso NÃO é persistente por padrão.
    Para SaaS, o ideal é migrar para Postgres depois.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS precos (
            chave TEXT PRIMARY KEY,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL
        )
        """
    )
    _ensure_columns(conn)
    return conn


def _ensure_columns(conn: sqlite3.Connection) -> None:
    """
    Evolui o schema sem quebrar bancos antigos.
    """
    cols = {row[1] for row in conn.execute("PRAGMA table_info(precos)").fetchall()}

    def add_col(name: str, ddl: str):
        if name not in cols:
            conn.execute(f"ALTER TABLE precos ADD COLUMN {ddl}")

    add_col("modulo", "modulo TEXT DEFAULT ''")        # ex: seguranca
    add_col("categoria", "categoria TEXT DEFAULT ''")  # ex: cftv, mao_obra, estrutura
    add_col("unidade", "unidade TEXT DEFAULT ''")      # un, m, m2, taxa
    add_col("tags", "tags TEXT DEFAULT ''")            # opcional (busca/organização)
    conn.commit()


def ensure_seed(conn: sqlite3.Connection) -> None:
    """
    Seeds com metadata (modulo/categoria/unidade). Você pode editar tudo na tela.
    """
    seeds = [
        # ===== Estrutura (Segurança) =====
        ("haste_reta", "Haste de cerca (reta)", 19.0, "seguranca", "estrutura", "un"),
        ("haste_canto", "Haste de canto", 50.0, "seguranca", "estrutura", "un"),

        # ===== Eletrificador =====
        ("central_sh1800", "Central SH1800", 310.0, "seguranca", "eletrificador", "un"),
        ("bateria", "Bateria", 83.0, "seguranca", "eletrificador", "un"),
        ("sirene", "Sirene", 2.0, "seguranca", "eletrificador", "un"),
        ("cabo_alta_50m", "Cabo de alta isolação (50m)", 75.0, "seguranca", "eletrificador", "un"),
        ("kit_aterramento", "Kit aterramento", 165.0, "seguranca", "eletrificador", "un"),
        ("kit_placas", "Placas de aviso (kit)", 19.0, "seguranca", "eletrificador", "un"),

        # ===== Cerca (materiais) =====
        ("fio_aco_200m", "Fio de aço (rolo 200m)", 80.0, "seguranca", "cerca", "un"),
        ("kit_isoladores", "Kit isoladores (100 un)", 19.90, "seguranca", "cerca", "un"),

        # ===== Concertina =====
        ("concertina_10m", "Concertina 30cm (10m)", 90.0, "seguranca", "concertina", "un"),
        ("concertina_linear_20m", "Concertina linear (20m)", 53.0, "seguranca", "concertina", "un"),

        # ===== CFTV (materiais) =====
        ("cftv_camera", "Câmera (un)", 115.17, "seguranca", "cftv", "un"),
        ("cftv_dvr", "DVR (un)", 0.0, "seguranca", "cftv", "un"),
        ("cftv_hd", "HD para DVR (un)", 0.0, "seguranca", "cftv", "un"),
        ("cftv_fonte_colmeia", "Fonte colmeia 12V (un)", 130.71, "seguranca", "cftv", "un"),
        ("cftv_cabo_cat5_m", "Cabo Cat5e (R$/metro)", 3.88, "seguranca", "cftv", "m"),
        ("cftv_balun", "Balun (un)", 28.79, "seguranca", "cftv", "un"),
        ("cftv_conector_p4_macho", "Conector P4 macho (un)", 7.20, "seguranca", "cftv", "un"),
        ("cftv_conector_p4_femea", "Conector P4 fêmea (un)", 7.20, "seguranca", "cftv", "un"),
        ("cftv_suporte_camera", "Suporte para câmera (un)", 0.0, "seguranca", "cftv", "un"),
        ("cftv_caixa_hermetica", "Caixa hermética (un)", 83.50, "seguranca", "cftv", "un"),

        # ===== Mão de obra (Segurança) =====
        ("mao_cerca_base", "Mão de obra cerca (taxa base)", 250.0, "seguranca", "mao_obra", "taxa"),
        ("mao_cerca_por_m", "Mão de obra cerca (R$/metro)", 18.0, "seguranca", "mao_obra", "m"),

        ("mao_concertina_base", "Mão de obra concertina (taxa base)", 150.0, "seguranca", "mao_obra", "taxa"),
        ("mao_concertina_por_m", "Mão de obra concertina (R$/metro)", 8.0, "seguranca", "mao_obra", "m"),

        ("mao_linear_base", "Mão de obra concertina linear (taxa base)", 200.0, "seguranca", "mao_obra", "taxa"),
        ("mao_linear_por_m", "Mão de obra concertina linear (R$/metro)", 10.0, "seguranca", "mao_obra", "m"),

        ("mao_cftv_dvr", "Mão de obra CFTV (instalação do DVR)", 200.0, "seguranca", "mao_obra", "taxa"),
        ("mao_cftv_por_camera_inst", "Mão de obra CFTV (instalação por câmera)", 120.0, "seguranca", "mao_obra", "un"),
        ("mao_cftv_por_camera_defeito", "Mão de obra CFTV (manutenção por câmera com defeito)", 80.0, "seguranca", "mao_obra", "un"),
    ]

    for k, d, v, mod, cat, uni in seeds:
        if not _exists(conn, k):
            upsert_item(conn, k, d, v, mod, cat, uni)


def _exists(conn: sqlite3.Connection, key: str) -> bool:
    cur = conn.execute("SELECT 1 FROM precos WHERE chave=?", (key,))
    return cur.fetchone() is not None


def get_price(conn: sqlite3.Connection, key: str, default: float = 0.0) -> float:
    cur = conn.execute("SELECT valor FROM precos WHERE chave=?", (key,))
    row = cur.fetchone()
    return float(row[0]) if row else float(default)


def upsert_item(
    conn: sqlite3.Connection,
    key: str,
    desc: str,
    value: float,
    modulo: str = "",
    categoria: str = "",
    unidade: str = "",
    tags: str = "",
) -> None:
    conn.execute(
        """
        INSERT INTO precos (chave, descricao, valor, modulo, categoria, unidade, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(chave) DO UPDATE SET
            descricao=excluded.descricao,
            valor=excluded.valor,
            modulo=excluded.modulo,
            categoria=excluded.categoria,
            unidade=excluded.unidade,
            tags=excluded.tags
        """,
        (key, desc, float(value), modulo or "", categoria or "", unidade or "", tags or ""),
    )
    conn.commit()


def update_value(conn: sqlite3.Connection, key: str, value: float) -> None:
    conn.execute("UPDATE precos SET valor=? WHERE chave=?", (float(value), key))
    conn.commit()


def list_items(
    conn: sqlite3.Connection,
    modulo: Optional[str] = None,
    categoria: Optional[str] = None,
    keys: Optional[List[str]] = None,
    search: Optional[str] = None,
) -> List[Tuple[str, str, float, str, str, str]]:
    """
    Retorna: (chave, descricao, valor, modulo, categoria, unidade)
    """
    q = "SELECT chave, descricao, valor, modulo, categoria, unidade FROM precos"
    where = []
    params = []

    if modulo:
        where.append("modulo=?")
        params.append(modulo)

    if categoria:
        where.append("categoria=?")
        params.append(categoria)

    if keys:
        placeholders = ",".join(["?"] * len(keys))
        where.append(f"chave IN ({placeholders})")
        params.extend(keys)

    if search:
        where.append("(descricao LIKE ? OR chave LIKE ? OR tags LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])

    if where:
        q += " WHERE " + " AND ".join(where)

    q += " ORDER BY categoria, descricao"
    cur = conn.execute(q, params)
    return cur.fetchall()
