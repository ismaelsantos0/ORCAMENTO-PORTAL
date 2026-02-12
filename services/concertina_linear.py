from datetime import datetime
import streamlit as st
from core.db import get_price
from core.money import brl
from services.base import ServicePlugin
from core.utils import ceil_div

id = "concertina_linear"
label = "Concertina linear eletrificada"
module = "seguranca"

item_keys = [
    "haste_reta",
    "haste_canto",
    "concertina_linear_20m"
]

def render_fields():
    per = st.number_input("Perímetro (m)", 1.0, 500.0, 36.0)
    fios = st.number_input("Qtd fios", 1, 10, 6)
    espac = st.number_input("Espaçamento (m)", 0.5, 5.0, 2.5)
    cantos = st.number_input("Cantos", 1, 20, 4)
    return {"per": per, "fios": fios, "espac": espac, "cantos": cantos}

def compute(conn, inputs):
    per = inputs["per"]
    fios = inputs["fios"]
    espac = inputs["espac"]
    cantos = inputs["cantos"]

    vaos = ceil_div(per, espac)
    total_hastes = vaos + 1
    retas = total_hastes - cantos

    metros = per * fios
    rolos = ceil_div(metros, 20)

    items = []
    subtotal = 0

    def add(desc, qty, unit):
        nonlocal subtotal
        sub = qty * unit
        items.append({"desc": desc, "qty": qty, "unit": unit, "sub": sub})
        subtotal += sub

    add("Haste reta", retas, get_price(conn, "haste_reta"))
    add("Haste de canto", cantos, get_price(conn, "haste_canto"))
    add("Concertina linear (20m)", rolos, get_price(conn, "concertina_linear_20m"))

    return {
        "id": str(datetime.now().timestamp()),
        "service_id": id,
        "service_name": label,
        "items": items,
        "subtotal": subtotal,
        "subtotal_brl": brl(subtotal),
    }

plugin = ServicePlugin(id, label, module, item_keys, render_fields, compute)
