import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import os
import time

# Configuração da Página
st.set_page_config(page_title="ERCI - Gestão Integral por Item", layout="wide", page_icon="🏗️")

# --- AUTO-REFRESH (5 MINUTOS) ---
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if time.time() - st.session_state.last_refresh > 300:
    st.session_state.last_refresh = time.time()
    st.rerun()

# --- ESTILIZAÇÃO E ANIMAÇÕES ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { color: #634D3E !important; }
    .stButton>button { background-color: #634D3E; color: white; border-radius: 5px; width: 100%; }
    .stInfo { background-color: #f0f2f6; border-left: 5px solid #B59572; }
    @keyframes blinker { 50% { opacity: 0.3; } }
    .alerta-vencido { color: white; background-color: #FF0000; padding: 5px; border-radius: 5px; font-weight: bold; animation: blinker 1s linear infinite; text-align: center; }
    @keyframes rocket-launch { 0% { transform: translateY(100vh); opacity: 1; } 100% { transform: translateY(-100vh); opacity: 0; } }
    .rocket-container { position: fixed; bottom: -100px; left: 50%; font-size: 50px; z-index: 9999; animation: rocket-launch 3s ease-in forwards; }
    </style>
    """, unsafe_allow_html=True)

def disparar_foguete():
    st.markdown('<div class="rocket-container">🚀</div>', unsafe_allow_html=True)

# Conexão com Planilha
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO: ATUALIZA O STATUS DO ITEM ---
def atualizar_status_item(id_item, novo_status):
    df_pedidos = conn.read(worksheet="Pedidos", ttl=0)
    df_pedidos.loc[df_pedidos['ID_Item'] == id_item, 'Status_Atual'] = novo_status
    conn.update(worksheet="Pedidos", data=df_pedidos)

# --- MENU LATERAL ---
if os.path.exists("Status Apresentação.png"):
    st.sidebar.image("Status Apresentação.png", use_container_width=True)

papel_usuario = st.sidebar.selectbox("Seu Papel Hoje (ERCI):", 
    ["PCP", "Dono do Pedido (DP)", "Produção", "Compras", "Financeiro", "Logística", "Gerência Geral"])

menu = st.sidebar.radio("Navegação", 
    [
        "📊 Resumo e Prazos", 
        "🚨 Auditoria", 
        "📥 Importar Itens (Sistema)",
        "✅ Gate 1: Aceite Técnico", 
        "🏭 Gate 2: Produção", 
        "💰 Gate 3: Material", 
        "🚛 Gate 4: Entrega",
        "👤 Cadastro de Gestores",
        "⚠️ Alteração de Pedido"
    ])

# --- FUNÇÃO DE GESTÃO DE GATES (A INTELIGÊNCIA DO NEGÓCIO) ---
def checklist_gate(gate_id, aba, itens_checklist, responsavel_r, executor_e, msg_bloqueio, proximo_status, objetivo, momento):
    st.header(f"Ficha de Controle: {gate_id}")
    st.markdown(f"**Objetivo:** {objetivo} | **Momento:** {momento}")
    st.info(f"⚖️ **Responsável (R):** {responsavel_r} | 🔨 **Executor (E):** {executor_e}")
    
    try:
        df_pedidos = conn.read(worksheet="Pedidos", ttl=0)
        df_pedidos['Busca'] = df_pedidos['CTR'].astype(str) + " / " + df_pedidos['Item'].astype(str) + " - " + df_pedidos['Pedido'].str[:40]
        item_sel = st.selectbox(f"Selecione o Item para {gate_id}", [""] + df_pedidos['Busca'].tolist(), key=f"sel_{aba}")
        
        if item_sel:
            row_item = df_pedidos[df_pedidos['Busca'] == item_sel].iloc[0]
            id_item = row_item['ID_Item']
            status_atual = row_item['Status_Atual']
            
            # Trava de Gate
            concluido = False
            if gate_id == "GATE 1" and status_atual != "Aguardando Gate 1": concluido = True
            elif gate_id == "GATE 2" and status_atual not in ["Aguardando Gate 1", "Aguardando Produção (G2)"]: concluido = True
            elif gate_id == "GATE 3" and status_atual not in ["Aguardando Gate 1", "Aguardando Produção (G2)", "Aguardando Materiais (G3)"]: concluido = True
            elif gate_id == "GATE 4" and status_atual == "CONCLUÍDO ✅": concluido = True

            if concluido:
                st.warning(f"✅ Este Gate já foi aprovado. Status atual: {status_atual}")
                if papel_usuario != "Gerência Geral": return

            pode_assinar = (papel_usuario == responsavel_r or papel_usuario == executor_e or papel_usuario == "Gerência Geral")
            if not pode_assinar: st.warning(f"⚠️ Acesso limitado a {responsavel_r} ou {executor_e}.")

            with st.form(f"form_{aba}"):
                respostas = {}
                for secao, itens in itens_checklist.items():
                    st.markdown(f"#### 🔹 {secao}")
                    for item in itens: respostas[item] = st.checkbox(item)
                
                obs = st.text_area("Observações Técnicas")
                if st.form_submit_button("VALIDAR E AVANÇAR PROCESSO 🚀", disabled=not pode_assinar):
                    if not all(respostas.values()):
                        st.error(f"❌ CRITÉRIOS DE BLOQUEIO: {msg_bloqueio}")
                    else:
                        df_gate = conn.read(worksheet=aba, ttl=0)
                        nova = {"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "ID_Item": id_item, "Validado_Por": papel_usuario, "Obs": obs}
                        nova.update(respostas)
                        conn.update(worksheet=aba, data=pd.concat([df_gate, pd.DataFrame([nova])], ignore_index=True))
                        atualizar_status_item(id_item, proximo_status)
                        st.success("Sucesso! Item avançou.")
                        disparar_foguete()
    except Exception as e: st.error(f"Erro: {e}")

# --- PÁGINAS ---

if menu == "📊 Resumo e Prazos":
    st.header("🚦 Monitor de Pedidos e Prazos")
    try:
        df_p = conn.read(worksheet="Pedidos", ttl=0)
        df_p['Data_Entrega'] = pd.to_datetime(df_p['Data_Entrega'], errors='coerce')
        for idx, row in df_p.sort_values(by='Data_Entrega', na_position='last').iterrows():
            dias = (row['Data_Entrega'].date() - date.today()).days if pd.notnull(row['Data_Entrega']) else None
            classe = "alerta-vencido" if dias is not None and dias <= 3 else ""
            
            c1, c2, c3, c4 = st.columns([2, 4, 2, 1])
            with c1: st.write(f"**{row['CTR']}**\nItem: {row['Item']}")
            with c2: st.write(f"**{row['Pedido']}**\n👤 {row['Dono']}")
            with c3: st.write(f"📍 {row['Status_Atual']}\n📅 {row['Data_Entrega'].strftime('%d/%m/%Y') if pd.notnull(row['Data_Entrega']) else 'S/D'}")
            with c4:
                if classe: st.markdown(f'<div class="{classe}">⚠️ ALERTA</div>', unsafe_allow_html=True)
                else: st.write("🟢 OK")
            st.markdown("---")
    except: st.error("Erro ao carregar resumo.")

elif menu == "📥 Importar Itens (Sistema)":
    st.header("📥 Importar Itens do Sistema")
    up = st.file_uploader("Arquivo egsDataGrid", type=["csv", "xlsx"])
    if up:
        df_up = pd.read_csv(up) if up.name.endswith('csv') else pd.read_excel(up)
        if st.button("Confirmar Importação"):
            df_base = conn.read(worksheet="Pedidos", ttl=0)
            novos = []
            for _, r in df_up.iterrows():
                uid = f"{r['Centro de custo']}-{r['Item']}"
                if uid not in df_base['ID_Item'].astype(str).values:
                    novos.append({
                        "ID_Item": uid, "CTR": r['Centro de custo'], "Obra": r['Obra'], "Item": r['Item'],
                        "Pedido": r['Produto'], "Dono": r['Gestor'], "Status_Atual": "Aguardando Gate 1",
                        "Data_Entrega": str(r['Data Entrega']), "Prev_Inicio": str(r['Prev. Inicio']), 
                        "Prev_Fim": str(r['Prev. Fim']), "Quantidade": r['Quantidade'], "Unidade": r['Unidade']
                    })
            if novos:
                conn.update(worksheet="Pedidos", data=pd.concat([df_base, pd.DataFrame(novos)], ignore_index=True))
                st.success("Importado!")

elif menu == "✅ Gate 1: Aceite Técnico":
    itens = {"Informações": ["Pedido registrado", "Cliente identificado"], "Escopo Técnico": ["Projeto recebido", "Materiais definidos"]}
    checklist_gate("GATE 1", "Checklist_G1", itens, "Dono do Pedido (DP)", "PCP", "Projeto incompleto", "Aguardando Produção (G2)", "Impedir erro inicial", "Antes do plano")

elif menu == "🏭 Gate 2: Produção":
    itens = {"Planejamento": ["Sequenciado", "Capacidade ok"], "Projeto": ["Desenho liberado"]}
    checklist_gate("GATE 2", "Checklist_G2", itens, "PCP", "Produção", "Sem plano ➡️ BLOQUEADO", "Aguardando Materiais (G3)", "Produzir planejado", "No corte")

elif menu == "💰 Gate 3: Material":
    itens = {"Materiais": ["Ferragens separadas"], "Compras": ["Recebido"]}
    checklist_gate("GATE 3", "Checklist_G3", itens, "Financeiro", "Compras", "Falta material", "Aguardando Entrega (G4)", "Fábrica sem parada", "Na montagem")

elif menu == "🚛 Gate 4: Entrega":
    itens = {"Qualidade": ["Acabamento conferido"], "Logística": ["Rota definida"]}
    checklist_gate("GATE 4", "Checklist_G4", itens, "Dono do Pedido (DP)", "Logística", "Erro acabamento", "CONCLUÍDO ✅", "Entrega perfeita", "Na carga")

elif menu == "🚨 Auditoria":
    st.header("🚨 Auditoria")
    df_aud = conn.read(worksheet="Alteracoes", ttl=0)
    st.dataframe(df_aud, use_container_width=True)

elif menu == "⚠️ Alteração de Pedido":
    st.header("🔄 Edição")
    # Lógica de edição que já tínhamos...
