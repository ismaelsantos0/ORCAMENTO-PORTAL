import streamlit as st
from streamlit_option_menu import option_menu

from assets.ui import inject_css, kpi, section
from core.db import get_conn, ensure_seed, list_items, upsert_item
from core.money import brl
from services.registry import SERVICE_REGISTRY

st.set_page_config(page_title="RR Smart | Orçamentos", page_icon="🧾", layout="wide")
inject_css()

conn = get_conn()
ensure_seed(conn)

plugins = list(SERVICE_REGISTRY.values())
labels = [p.label for p in plugins]

# ===== Sidebar / Portal Menu =====
with st.sidebar:
    st.markdown("### RR Smart Soluções")
    st.caption("Portal de Orçamentos")
    page = option_menu(
        menu_title=None,
        options=["Dashboard", "Novo orçamento", "Itens & preços"],
        icons=["speedometer2", "file-earmark-plus", "tags"],
        default_index=1,
        styles={
            "container": {"padding": "0.35rem"},
            "icon": {"font-size": "1rem"},
            "nav-link": {"font-size": "0.95rem", "border-radius": "12px"},
            "nav-link-selected": {"background-color": "rgba(124,92,255,0.22)"},
        },
    )

# ===== Dashboard =====
if page == "Dashboard":
    section("Dashboard", "Visão geral do portal (depois a gente liga com histórico e clientes).")

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi("Serviços disponíveis", str(len(plugins)), "Plugins ativos no sistema", badge="MVP")
    with c2:
        kpi("Módulos", "Segurança", "Pronto para expandir", badge="Escalável")
    with c3:
        kpi("PDF", "2 modelos", "Completo + Resumo", badge="Em evolução")

    st.markdown("### Próximos upgrades")
    st.markdown(
        "- Histórico de orçamentos (salvar/duplicar)\n"
        "- Cadastro de clientes\n"
        "- PDF premium (assinatura/escopo)\n"
        "- Multiempresa + login (SaaS)"
    )

# ===== Novo orçamento =====
elif page == "Novo orçamento":
    section("Novo orçamento", "Escolha um serviço, preencha os dados e calcule o orçamento.")

    left, right = st.columns([2.2, 1])

    with left:
        selected_label = st.selectbox("Serviço", labels)
        plugin = plugins[labels.index(selected_label)]

        st.markdown(f'<span class="badge">📦 Itens filtrados por serviço</span> <span class="badge">🧩 {plugin.module}</span>', unsafe_allow_html=True)
        st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

        inputs = plugin.render_fields()

        colA, colB = st.columns([1, 1])
        with colA:
            calc = st.button("Calcular", type="primary")
        with colB:
            st.button("Limpar", type="secondary")

        if calc:
            result = plugin.compute(conn, inputs)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**Subtotal do serviço:** <span style='font-size:1.4rem; font-weight:800;'>{result['subtotal_brl']}</span>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
            st.markdown("### Composição (itens)")
            for it in result["items"]:
                st.write(f"• **{it['desc']}** — {it['qty']} × {brl(it['unit'])} = **{brl(it['sub'])}**")

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**Atalho**")
        st.caption("Se precisar ajustar valores desse serviço, vá em **Itens & preços** e filtre pelo serviço.")
        st.markdown("</div>", unsafe_allow_html=True)

# ===== Itens & preços =====
else:
    section("Itens & preços", "Edite valores sem bagunça: escolha um serviço e veja apenas os itens dele.")

    selected_label = st.selectbox("Filtrar por serviço", labels)
    plugin = plugins[labels.index(selected_label)]

    search = st.text_input("Buscar item (nome/chave)", value="")

    rows = list_items(conn, modulo=plugin.module, keys=plugin.item_keys, search=search)

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi("Serviço", plugin.label, "Filtro aplicado")
    with c2:
        kpi("Módulo", plugin.module, "Organização por módulo")
    with c3:
        kpi("Itens exibidos", str(len(rows)), "Apenas itens do serviço")

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    st.markdown("### Editar valores")
    with st.form("form_prices"):
        for chave, desc, val, mod, cat, uni in rows:
            a, b, c = st.columns([3, 6, 3])
            with a:
                st.text_input("Chave", value=chave, disabled=True, key=f"k_{chave}")
                st.caption(f"{cat} • {uni}")
            with b:
                st.text_input("Descrição", value=desc, key=f"d_{chave}")
            with c:
                st.number_input("Valor (R$)", value=float(val), min_value=0.0, step=1.0, key=f"v_{chave}")

        saved = st.form_submit_button("Salvar alterações")
        if saved:
            for chave, desc, val, mod, cat, uni in rows:
                new_desc = st.session_state.get(f"d_{chave}", desc)
                new_val = st.session_state.get(f"v_{chave}", float(val))
                upsert_item(conn, chave, new_desc, float(new_val), mod, cat, uni)
            st.success("Preços atualizados!")

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    st.markdown("### ➕ Cadastrar novo item (dentro do módulo do serviço)")
    with st.form("new_item"):
        x1, x2, x3 = st.columns([3, 6, 3])
        with x1:
            new_key = st.text_input("Chave (ex: cftv_caixa_extra)")
        with x2:
            new_desc = st.text_input("Descrição")
        with x3:
            new_val = st.number_input("Valor (R$)", value=0.0, min_value=0.0, step=1.0)

        y1, y2 = st.columns([1, 1])
        with y1:
            new_cat = st.text_input("Categoria (ex: cftv / mao_obra / estrutura)", value="cftv")
        with y2:
            new_unit = st.selectbox("Unidade", ["un", "m", "m2", "taxa"], index=0)

        add = st.form_submit_button("Cadastrar item")
        if add:
            if not new_key.strip() or not new_desc.strip():
                st.error("Informe chave e descrição.")
            else:
                upsert_item(conn, new_key.strip(), new_desc.strip(), float(new_val), plugin.module, new_cat, new_unit)
                st.success("Item cadastrado!")
                st.rerun()
