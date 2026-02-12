import streamlit as st
from core.db import get_conn, list_items, upsert_item
from services.registry import SERVICE_REGISTRY

st.set_page_config(layout="wide")

conn = get_conn()

menu = st.sidebar.selectbox("Menu", ["Novo orçamento", "Editar preços"])

if menu == "Novo orçamento":
    plugins = list(SERVICE_REGISTRY.values())
    labels = [p.label for p in plugins]
    selected_label = st.selectbox("Escolha o serviço", labels)
    plugin = plugins[labels.index(selected_label)]

    inputs = plugin.render_fields()

    if st.button("Calcular"):
        result = plugin.compute(conn, inputs)
        st.write(result["items"])
        st.success(result["subtotal_brl"])

if menu == "Editar preços":
    st.subheader("Catálogo de Itens")

    plugins = list(SERVICE_REGISTRY.values())
    labels = [p.label for p in plugins]
    selected_label = st.selectbox("Filtrar por serviço", labels)
    plugin = plugins[labels.index(selected_label)]

    rows = list_items(conn, modulo=plugin.module, keys=plugin.item_keys)

    for chave, desc, val, mod, cat, uni in rows:
        new_val = st.number_input(desc, value=float(val), key=chave)
        upsert_item(conn, chave, desc, new_val, mod, cat, uni)

    st.divider()
    st.subheader("Cadastrar novo item")

    key = st.text_input("Chave")
    desc = st.text_input("Descrição")
    val = st.number_input("Valor")
    if st.button("Cadastrar"):
        upsert_item(conn, key, desc, val, plugin.module, "material", "un")
        st.success("Item cadastrado")
