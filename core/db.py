import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

def get_engine() -> Engine:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL não definido (crie um Postgres no Railway).")
    # Railway geralmente fornece postgres://, SQLAlchemy prefere postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return create_engine(url, pool_pre_ping=True)

def now_utc():
    return datetime.now(timezone.utc)

def init_db(engine: Engine) -> None:
    with engine.begin() as c:
        c.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """))
        c.execute(text("""
        CREATE TABLE IF NOT EXISTS companies (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            whatsapp TEXT DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """))
        c.execute(text("""
        CREATE TABLE IF NOT EXISTS memberships (
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            role TEXT NOT NULL DEFAULT 'admin',
            PRIMARY KEY (user_id, company_id)
        );
        """))
        c.execute(text("""
        CREATE TABLE IF NOT EXISTS plans (
            id BIGSERIAL PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            price_monthly_cents INT NOT NULL DEFAULT 0,
            max_users INT NOT NULL DEFAULT 1,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """))
        c.execute(text("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            company_id BIGINT PRIMARY KEY REFERENCES companies(id) ON DELETE CASCADE,
            plan_id BIGINT NOT NULL REFERENCES plans(id),
            status TEXT NOT NULL DEFAULT 'trial', -- trial|active|past_due|canceled
            current_period_end TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """))
        c.execute(text("""
        CREATE TABLE IF NOT EXISTS items (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            key TEXT NOT NULL,
            name TEXT NOT NULL,
            module TEXT NOT NULL DEFAULT 'seguranca',
            category TEXT NOT NULL DEFAULT '',
            unit TEXT NOT NULL DEFAULT 'un',
            price NUMERIC(12,2) NOT NULL DEFAULT 0,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(company_id, key)
        );
        """))

    seed_plans(engine)

def seed_plans(engine: Engine) -> None:
    with engine.begin() as c:
        # cria planos básicos se não existirem
        c.execute(text("""
        INSERT INTO plans (code, name, price_monthly_cents, max_users)
        VALUES
          ('basic', 'Básico', 2900, 1),
          ('pro', 'Pro', 5900, 3),
          ('agency', 'Agência', 9900, 10)
        ON CONFLICT (code) DO NOTHING;
        """))

# ---------- USERS / AUTH ----------
def create_user_with_company(engine: Engine, email: str, name: str, password_hash: str, company_name: str, whatsapp: str) -> Dict[str, Any]:
    trial_days = int(os.getenv("TRIAL_DAYS", "7"))
    end = now_utc() + timedelta(days=trial_days)

    with engine.begin() as c:
        u = c.execute(text("""
            INSERT INTO users (email, name, password_hash)
            VALUES (:email, :name, :ph)
            RETURNING id;
        """), {"email": email.lower().strip(), "name": name.strip(), "ph": password_hash}).fetchone()
        user_id = int(u[0])

        co = c.execute(text("""
            INSERT INTO companies (name, whatsapp)
            VALUES (:name, :whatsapp)
            RETURNING id;
        """), {"name": company_name.strip(), "whatsapp": whatsapp.strip()}).fetchone()
        company_id = int(co[0])

        c.execute(text("""
            INSERT INTO memberships (user_id, company_id, role)
            VALUES (:u, :c, 'admin');
        """), {"u": user_id, "c": company_id})

        plan_id = c.execute(text("SELECT id FROM plans WHERE code='basic'")).fetchone()[0]
        c.execute(text("""
            INSERT INTO subscriptions (company_id, plan_id, status, current_period_end)
            VALUES (:cid, :pid, 'trial', :end);
        """), {"cid": company_id, "pid": int(plan_id), "end": end})

    return {"user_id": user_id, "company_id": company_id}

def get_user_by_email(engine: Engine, email: str) -> Optional[Dict[str, Any]]:
    with engine.begin() as c:
        row = c.execute(text("""
            SELECT id, email, name, password_hash
            FROM users
            WHERE email=:e
        """), {"e": email.lower().strip()}).fetchone()
        if not row:
            return None
        return {"id": int(row[0]), "email": row[1], "name": row[2], "password_hash": row[3]}

def get_membership_company(engine: Engine, user_id: int) -> Optional[Dict[str, Any]]:
    with engine.begin() as c:
        row = c.execute(text("""
            SELECT c.id, c.name, c.whatsapp, m.role
            FROM memberships m
            JOIN companies c ON c.id = m.company_id
            WHERE m.user_id=:u
            ORDER BY c.id
            LIMIT 1
        """), {"u": user_id}).fetchone()
        if not row:
            return None
        return {"company_id": int(row[0]), "company_name": row[1], "whatsapp": row[2], "role": row[3]}

def get_subscription_status(engine: Engine, company_id: int) -> Dict[str, Any]:
    with engine.begin() as c:
        row = c.execute(text("""
            SELECT s.status, s.current_period_end, p.code, p.name, p.max_users
            FROM subscriptions s
            JOIN plans p ON p.id = s.plan_id
            WHERE s.company_id=:cid
        """), {"cid": company_id}).fetchone()

    if not row:
        return {"active": False, "status": "none", "plan": "none", "plan_name": "Sem plano", "max_users": 0}

    status = row[0]
    end = row[1]
    plan_code = row[2]
    plan_name = row[3]
    max_users = int(row[4])

    active = (status in ("trial", "active")) and (end is None or end > now_utc())
    return {"active": active, "status": status, "period_end": end, "plan": plan_code, "plan_name": plan_name, "max_users": max_users}

# ---------- ITEMS ----------
def list_items(engine: Engine, company_id: int, module: str = "seguranca", category: Optional[str] = None, search: str = "") -> List[Dict[str, Any]]:
    where = "company_id=:cid AND module=:m AND active=true"
    params = {"cid": company_id, "m": module}

    if category:
        where += " AND category=:cat"
        params["cat"] = category

    if search:
        where += " AND (name ILIKE :q OR key ILIKE :q)"
        params["q"] = f"%{search}%"

    with engine.begin() as c:
        rows = c.execute(text(f"""
            SELECT key, name, category, unit, price
            FROM items
            WHERE {where}
            ORDER BY category, name
        """), params).fetchall()

    out = []
    for r in rows:
        out.append({"key": r[0], "name": r[1], "category": r[2], "unit": r[3], "price": float(r[4])})
    return out

def upsert_item(engine: Engine, company_id: int, key: str, name: str, module: str, category: str, unit: str, price: float) -> None:
    with engine.begin() as c:
        c.execute(text("""
            INSERT INTO items (company_id, key, name, module, category, unit, price, active)
            VALUES (:cid, :k, :n, :m, :cat, :u, :p, true)
            ON CONFLICT (company_id, key) DO UPDATE SET
                name=excluded.name,
                module=excluded.module,
                category=excluded.category,
                unit=excluded.unit,
                price=excluded.price,
                active=true
        """), {"cid": company_id, "k": key, "n": name, "m": module, "cat": category, "u": unit, "p": float(price)})

def seed_company_items(engine: Engine, company_id: int) -> None:
    # seeds iniciais da sua área (segurança)
    seeds = [
        ("cftv_camera_bullet_2mp", "Câmera Bullet 2MP", "seguranca", "cftv_camera", "un", 115.17),
        ("cftv_camera_dome_4mp", "Câmera Dome 4MP", "seguranca", "cftv_camera", "un", 165.00),
        ("cftv_dvr", "DVR", "seguranca", "cftv", "un", 0.0),
        ("cftv_hd", "HD para DVR", "seguranca", "cftv", "un", 0.0),
        ("mao_cftv_dvr", "Mão de obra (instalação DVR)", "seguranca", "mao_obra", "taxa", 200.0),
        ("mao_cftv_por_camera_inst", "Mão de obra (instalação por câmera)", "seguranca", "mao_obra", "un", 120.0),
    ]
    for k, n, m, cat, u, p in seeds:
        upsert_item(engine, company_id, k, n, m, cat, u, p)
