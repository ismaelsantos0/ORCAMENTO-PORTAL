import streamlit as st

from core.db import get_conn, list_items, upsert_item, ensure_seed
from core.money import brl
from services.registry import SERVICE_REGISTRY
from assets.ui import inject_css, card

st.set_page_config(page_title="RR Smart — Orçamentos", page_icon="🧾", layout="wide")

inject_css()

conn = get_conn()
ensure_seed(conn)

st.sidebar.markdown("## 🧾 RR Smart")
st.sidebar.caption("Gerador de orçamentos (MVP)")

menu = st.sidebar.radio("Navegação", ["Dashboard", "Novo orçamento", "Itens & preços"], index=1)

plugins = list(SERVICE_REGISTRY.values())
labels = [p.label for p in plugins]

# ===== Dashboard =====
if menu == "Dashboard":
    st.markdown("# Dashboard")
    st.caption("Visão geral do seu uso (depois a gente liga com histórico).")

    c1, c2, c3 = st.columns(3)
    with c1:
        card("Serviços disponíveis", "Plugins ativos no sistema", right=str(len(plugins)))
    with c2:
        card("Status", "Base pronta pra virar SaaS", right="MVP")
    with c3:
        card("PDF", "Completo + Resumo (quando ligar)", right="Em evolução")

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    st.markdown("### Próximos passos")
    st.markdown(
        """
- Melhorar telas e navegação (portal de verdade)  
- PDFs profissionais (modelo completo e resumo)  
- Histórico de orçamentos + clientes  
- Multiempresa + login (SaaS)
        """
    )

# ===== Novo orçamento =====
elif menu == "Novo orçamento":
    st.markdown("# Novo orçamento")
    st.caption("Escolha um serviço, informe os dados e calcule o subtotal do serviço.")

    left, right = st.columns([2, 1])
    with left:
        selected_label = st.selectbox("Serviço", labels)
        plugin = plugins[labels.index(selected_label)]

        st.markdown('<span class="pill">📦 Itens filtrados por serviço</span>', unsafe_allow_html=True)
        inputs = plugin.render_fields()

        st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

        if st.button("Calcular"):
            result = plugin.compute(conn, inputs)
            st.success(f"Subtotal: {result['subtotal_brl']}")

            st.markdown("### Composição")
            for it in result["items"]:
                st.write(f"- **{it['desc']}** — {it['qty']} × {brl(it['unit'])} = {brl(it['sub'])}")

    with right:
        st.markdown("### Atalho rápido")
        st.info("Quer ajustar preços só desse serviço? Vá em **Itens & preços** e filtre pelo serviço.")

# ===== Itens & preços =====
else:
    st.markdown("# Itens & preços")
    st.caption("Aqui você edita os valores sem bagunça: filtra por serviço e vê só o que importa.")

    selected_label = st.selectbox("Filtrar por serviço", labels)
    plugin = plugins[labels.index(selected_label)]

    search = st.text_input("Buscar item (nome ou chave)", value="")

    rows = list_items(conn, modulo=plugin.module, keys=plugin.item_keys, search=search)

    st.markdown('<div class="portal-card">', unsafe_allow_html=True)
    st.markdown(f"**Serviço:** {plugin.label}  \n**Módulo:** `{plugin.module}`  \n**Itens:** {len(rows)}")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    st.subheader("Editar valores")
    with st.form("form_prices"):
        edited = []
        for chave, desc, val, mod, cat, uni in rows:
            c1, c2, c3 = st.columns([3, 6, 3])
            with c1:
                st.text_input("Chave", value=chave, disabled=True, key=f"k_{chave}")
            with c2:
                st.text_input("Descrição", value=desc, key=f"d_{chave}")
            with c3:
                st.number_input("Valor (R$)", value=float(val), min_value=0.0, step=1.0, key=f"v_{chave}")

            edited.append(chave)

        if st.form_submit_button("Salvar"):
            for chave, desc, val, mod, cat, uni in rows:
                new_desc = st.session_state.get(f"d_{chave}", desc)
                new_val = st.session_state.get(f"v_{chave}", float(val))
                upsert_item(conn, chave, new_desc, float(new_val), mod, cat, uni)
            st.success("Preços atualizados!")

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    st.subheader("Cadastrar novo item (para este módulo)")
    st.caption("Esse item entra no catálogo e depois você pode passar a usar nos serviços quando quiser.")

    with st.form("new_item"):
        n1, n2, n3 = st.columns([3, 6, 3])
        with n1:
            new_key = st.text_input("Chave (ex: cftv_caixa_extra)")
        with n2:
            new_desc = st.text_input("Descrição")
        with n3:
            new_val = st.number_input("Valor (R$)", value=0.0, min_value=0.0, step=1.0)

        new_cat = st.text_input("Categoria (ex: cftv / mao_obra / estrutura)", value="cftv")
        new_unit = st.selectbox("Unidade", ["un", "m", "m2", "taxa"], index=0)

        if st.form_submit_button("Cadastrar"):
            if not new_key.strip() or not new_desc.strip():
                st.error("Informe chave e descrição.")
            else:
                upsert_item(conn, new_key.strip(), new_desc.strip(), float(new_val), plugin.module, new_cat, new_unit)
                st.success("Item cadastrado!")
                st.rerun()
