from datetime import datetime
import streamlit as st
from core.db import get_price
from core.money import brl
from services.base import ServicePlugin

id = "cftv_install"
label = "CFTV - Instalação"
module = "seguranca"

item_keys = [
    "cftv_camera",
    "cftv_dvr",
    "mao_cftv_por_camera"
]

def render_fields():
    qtd = st.number_input("Quantidade de câmeras", 1, 32, 4)
    return {"qtd": qtd}

def compute(conn, inputs):
    qtd = inputs["qtd"]
    items = []
    subtotal = 0

    def add(desc, qty, unit):
        nonlocal subtotal
        sub = qty * unit
        items.append({"desc": desc, "qty": qty, "unit": unit, "sub": sub})
        subtotal += sub

    add("Câmera", qtd, get_price(conn, "cftv_camera"))
    add("Mão de obra por câmera", qtd, get_price(conn, "mao_cftv_por_camera"))

    return {
        "id": str(datetime.now().timestamp()),
        "service_id": id,
        "service_name": label,
        "items": items,
        "subtotal": subtotal,
        "subtotal_brl": brl(subtotal),
    }

plugin = ServicePlugin(id, label, module, item_keys, render_fields, compute)
