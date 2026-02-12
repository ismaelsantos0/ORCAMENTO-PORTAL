import streamlit as st
from streamlit_option_menu import option_menu

from assets.ui import inject_css, section, kpi
from core.auth import hash_password, verify_password
from core.db import (
    get_engine, init_db,
    create_user_with_company, get_user_by_email,
    get_membership_company, get_subscription_status,
    list_items, upsert_item, seed_company_items
)
from core.money import brl

st.set_page_config(page_title="RR Smart | Portal", page_icon="🧾", layout="wide")
inject_css()

engine = get_engine()
init_db(engine)

def require_login():
    if "user" not in st.session_state:
        st.session_state.user = None
    if st.session_state.user is None:
        auth_page()
        st.stop()

def auth_page():
    section("Acesso", "Entre com sua conta ou crie uma nova (trial automático).")
    tab1, tab2 = st.tabs(["Entrar", "Criar conta"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            email = st.text_input("Email", key="login_email")
        with c2:
            password = st.text_input("Senha", type="password", key="login_pass")

        if st.button("Entrar", type="primary"):
            u = get_user_by_email(engine, email)
            if not u or not verify_password(password, u["password_hash"]):
                st.error("Email ou senha inválidos.")
                return
            mem = get_membership_company(engine, u["id"])
            if not mem:
                st.error("Sua conta não tem empresa vinculada.")
                return
            st.session_state.user = {"id": u["id"], "name": u["name"], "email": u["email"], **mem}
            st.rerun()

    with tab2:
        name = st.text_input("Seu nome", key="reg_name")
        company = st.text_input("Nome da empresa", value="RR Smart Soluções", key="reg_company")
        whatsapp = st.text_input("WhatsApp", value="", key="reg_whats")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Senha", type="password", key="reg_pass")

        if st.button("Criar conta", type="primary"):
            if not (name.strip() and company.strip() and email.strip() and password.strip()):
                st.error("Preencha nome, empresa, email e senha.")
                return
            if get_user_by_email(engine, email):
                st.error("Esse email já está cadastrado.")
                return
            res = create_user_with_company(engine, email, name, hash_password(password), company, whatsapp)
            # seed itens iniciais da empresa
            seed_company_items(engine, res["company_id"])
            u = get_user_by_email(engine, email)
            mem = get_membership_company(engine, u["id"])
            st.session_state.user = {"id": u["id"], "name": u["name"], "email": u["email"], **mem}
            st.success("Conta criada! Trial ativado.")
            st.rerun()

def subscription_guard(company_id: int):
    sub = get_subscription_status(engine, company_id)
    if not sub["active"]:
        st.error("Seu acesso está bloqueado. Plano inativo ou expirado.")
        st.info(f"Status: {sub['status']} | Plano: {sub['plan_name']}")
        st.stop()
    return sub

# ---------- APP ----------
require_login()
u = st.session_state.user
sub = subscription_guard(u["company_id"])

with st.sidebar:
    st.markdown("### RR Smart Soluções")
    st.caption(f"👤 {u['name']}")
    st.caption(f"🏢 {u['company_name']}")
    st.caption(f"📦 Plano: {sub['plan_name']} ({sub['status']})")
    page = option_menu(
        None,
        ["Dashboard", "Catálogo de Itens", "Orçar CFTV (dinâmico)"],
        icons=["speedometer2", "tags", "camera-video"],
        default_index=0,
        styles={
            "container": {"padding": "0.35rem"},
            "nav-link": {"border-radius": "12px"},
            "nav-link-selected": {"background-color": "rgba(124,92,255,0.22)"},
        },
    )
    if st.button("Sair"):
        st.session_state.user = None
        st.rerun()

if page == "Dashboard":
    section("Dashboard", "Base SaaS pronta: usuários, empresa, plano e dados persistentes no Postgres.")

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi("Empresa", u["company_name"], "Tenant ativo", badge="SaaS")
    with c2:
        kpi("Plano", sub["plan_name"], f"Status: {sub['status']}", badge="OK" if sub["active"] else "Bloq")
    with c3:
        kpi("Módulo", "Segurança", "Pronto para plugins", badge="v1")

    st.markdown("### Próximo passo")
    st.write("Agora vamos plugar seus serviços (cerca, concertina, etc.) usando esse banco por empresa.")

elif page == "Catálogo de Itens":
    section("Catálogo de Itens", "Aqui você cadastra/edita itens e fica salvo no Railway (Postgres).")

    module = st.selectbox("Módulo", ["seguranca"], index=0)
    category = st.selectbox("Categoria", ["cftv_camera", "cftv", "mao_obra", "cerca", "concertina", "estrutura", "eletrificador"], index=0)
    q = st.text_input("Buscar", value="")

    items = list_items(engine, u["company_id"], module=module, category=category, search=q)

    c1, c2, c3 = st.columns(3)
    with c1: kpi("Categoria", category, "Filtro aplicado")
    with c2: kpi("Itens", str(len(items)), "Ativos no catálogo")
    with c3: kpi("Persistência", "Postgres", "Não perde no deploy", badge="Railway")

    st.markdown("### Itens")
    for it in items:
        a, b, c = st.columns([5, 2, 2])
        with a:
            st.markdown(f"**{it['name']}**")
            st.caption(f"`{it['key']}` • {it['unit']}")
        with b:
            new_price = st.number_input("Preço", value=float(it["price"]), min_value=0.0, step=1.0, key=f"p_{it['key']}")
        with c:
            if st.button("Salvar", key=f"s_{it['key']}"):
                upsert_item(engine, u["company_id"], it["key"], it["name"], module, category, it["unit"], new_price)
                st.success("Atualizado!")
                st.rerun()

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.markdown("### ➕ Cadastrar novo item")
    with st.form("new_item"):
        key = st.text_input("Chave (ex: cftv_camera_bullet_6mp)")
        name = st.text_input("Nome (ex: Câmera Bullet 6MP)")
        unit = st.selectbox("Unidade", ["un", "m", "m2", "taxa"], index=0)
        price = st.number_input("Preço", value=0.0, min_value=0.0, step=1.0)
        ok = st.form_submit_button("Cadastrar")
        if ok:
            if not key.strip() or not name.strip():
                st.error("Informe chave e nome.")
            else:
                upsert_item(engine, u["company_id"], key.strip(), name.strip(), module, category, unit, price)
                st.success("Item cadastrado e salvo no Postgres!")
                st.rerun()

else:
    section("Orçar CFTV (dinâmico)", "Selecione 1 ou vários tipos de câmera do catálogo e informe as quantidades.")

    # carrega todas as câmeras da categoria cftv_camera
    cams = list_items(engine, u["company_id"], module="seguranca", category="cftv_camera", search="")
    if not cams:
        st.warning("Nenhum tipo de câmera cadastrado. Vá em 'Catálogo de Itens' e cadastre em categoria 'cftv_camera'.")
        st.stop()

    cam_labels = [f"{c['name']} ({brl(c['price'])})" for c in cams]
    cam_map = {cam_labels[i]: cams[i] for i in range(len(cams))}

    selected = st.multiselect("Tipos de câmera", cam_labels, default=[cam_labels[0]])
    if not selected:
        st.info("Selecione pelo menos 1 tipo de câmera.")
        st.stop()

    st.markdown("### Quantidades")
    total_cameras = 0
    items = []
    subtotal = 0.0

    for label in selected:
        cam = cam_map[label]
        qty = st.number_input(f"Qtd — {cam['name']}", min_value=0, step=1, value=1, key=f"q_{cam['key']}")
        if qty > 0:
            total_cameras += qty
            sub = qty * float(cam["price"])
            items.append((cam["name"], qty, float(cam["price"]), sub))
            subtotal += sub

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    # mão de obra por câmera
    mao = list_items(engine, u["company_id"], module="seguranca", category="mao_obra", search="por câmera")
    mao_unit = 0.0
    if mao:
        mao_unit = float(mao[0]["price"])

    mao_total = total_cameras * mao_unit
    total = subtotal + mao_total

    c1, c2, c3 = st.columns(3)
    with c1: kpi("Câmeras (total)", str(total_cameras), "Soma de todos os tipos")
    with c2: kpi("Materiais", brl(subtotal), "Câmeras selecionadas")
    with c3: kpi("Total", brl(total), f"Mão de obra: {brl(mao_total)}", badge="Prévia")

    st.markdown("### Resumo")
    for (name, qty, unit, sub) in items:
        st.write(f"• **{name}** — {qty} × {brl(unit)} = **{brl(sub)}**")
    st.write(f"• **Mão de obra por câmera** — {total_cameras} × {brl(mao_unit)} = **{brl(mao_total)}**")
