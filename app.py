import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import os
import time

# Configuração da Página
st.set_page_config(page_title="Status - Gestão por Itens", layout="wide", page_icon="🏗️")

# --- FUNÇÃO DE AUTO-REFRESH (5 MINUTOS) ---
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

refresh_interval = 300 
if time.time() - st.session_state.last_refresh > refresh_interval:
    st.session_state.last_refresh = time.time()
    st.rerun()

# --- ESTILIZAÇÃO E ANIMAÇÕES (CSS) ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { color: #634D3E !important; }
    .stButton>button { background-color: #634D3E; color: white; border-radius: 5px; width: 100%; }
    .stInfo { background-color: #f0f2f6; border-left: 5px solid #B59572; }
    
    @keyframes blinker { 50% { opacity: 0.3; } }
    .alerta-vencido {
        color: white; background-color: #FF0000; padding: 5px;
        border-radius: 5px; font-weight: bold; animation: blinker 1s linear infinite;
        text-align: center;
    }

    @keyframes rocket-launch {
        0% { transform: translateY(100vh) translateX(0px); opacity: 1; }
        50% { transform: translateY(50vh) translateX(20px); }
        100% { transform: translateY(-100vh) translateX(-20px); opacity: 0; }
    }
    .rocket-container {
        position: fixed; bottom: -100px; left: 50%; font-size: 50px;
        z-index: 9999; animation: rocket-launch 3s ease-in forwards;
    }
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
else:
    st.sidebar.title("STATUS MARCENARIA")

st.sidebar.markdown("---")
papel_usuario = st.sidebar.selectbox("Seu Papel Hoje (ERCI):", 
    ["PCP", "Dono do Pedido (DP)", "Produção", "Compras", "Financeiro", "Logística", "Gerência Geral"])

# Corrigindo a lista para garantir que o menu apareça corretamente
menu = st.sidebar.radio("Navegação", 
    [
        "📊 Resumo e Prazos", 
        "🚨 Auditoria", 
        "📥 Importar Itens (Sistema)",
        "✅ Validar Gates por Item", 
        "👤 Cadastro de Gestores",
        "⚠️ Alteração de Pedido"
    ])

# --- FUNÇÃO DE GESTÃO DE GATES POR ITEM ---
def checklist_gate_item(gate_id, aba, itens_checklist, responsavel_r, executor_e, msg_bloqueio, proximo_status, objetivo, momento):
    st.header(f"Ficha de Controle: {gate_id}")
    st.markdown(f"**Objetivo:** {objetivo} | **Momento:** {momento}")
    st.info(f"⚖️ **R:** {responsavel_r} | 🔨 **E:** {executor_e}")
    
    try:
        df_pedidos = conn.read(worksheet="Pedidos", ttl=0)
        df_pedidos['Busca'] = df_pedidos['CTR'].astype(str) + " / " + df_pedidos['Item'].astype(str) + " - " + df_pedidos['Pedido'].str[:40]
        item_sel = st.selectbox(f"Selecione o Item para {gate_id}", [""] + df_pedidos['Busca'].tolist(), key=f"sel_{aba}")
        
        if item_sel:
            row_item = df_pedidos[df_pedidos['Busca'] == item_sel].iloc[0]
            id_item = row_item['ID_Item']
            status_atual = row_item['Status_Atual']
            
            concluido = False
            if gate_id == "GATE 1" and status_atual != "Aguardando Gate 1": concluido = True
            elif gate_id == "GATE 2" and status_atual not in ["Aguardando Gate 1", "Aguardando Produção (G2)"]: concluido = True
            elif gate_id == "GATE 3" and status_atual not in ["Aguardando Gate 1", "Aguardando Produção (G2)", "Aguardando Materiais (G3)"]: concluido = True
            elif gate_id == "GATE 4" and status_atual == "CONCLUÍDO ✅": concluido = True

            if concluido:
                st.warning(f"✅ Já aprovado. Status: {status_atual}")
                if papel_usuario != "Gerência Geral": return

            pode_assinar = (papel_usuario == responsavel_r or papel_usuario == executor_e or papel_usuario == "Gerência Geral")
            with st.form(f"form_{aba}"):
                respostas = {}
                for secao, itens in itens_checklist.items():
                    st.markdown(f"#### 🔹 {secao}")
                    for item in itens: respostas[item] = st.checkbox(item)
                obs = st.text_area("Observações Técnicas")
                if st.form_submit_button("VALIDAR E AVANÇAR PROCESSO 🚀", disabled=not pode_assinar):
                    if not all(respostas.values()):
                        st.error(f"❌ BLOQUEIO: {msg_bloqueio}")
                    else:
                        df_gate = conn.read(worksheet=aba, ttl=0)
                        nova = {"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "ID_Item": id_item, "Validado_Por": papel_usuario, "Obs": obs}
                        nova.update(respostas)
                        conn.update(worksheet=aba, data=pd.concat([df_gate, pd.DataFrame([nova])], ignore_index=True))
                        atualizar_status_item(id_item, proximo_status)
                        st.success("Item avançou no processo!")
                        disparar_foguete()
    except Exception as e: st.error(f"Erro: {e}")

# --- PÁGINAS ---

if menu == "📥 Importar Itens (Sistema)":
    st.header("📥 Importar Itens da Marcenaria")
    st.write("Arraste o arquivo Excel/CSV exportado (egsDataGrid).")
    up = st.file_uploader("Arquivo de itens", type=["csv", "xlsx"])
    if up:
        df_up = pd.read_csv(up) if up.name.endswith('csv') else pd.read_excel(up)
        
        # Mapeamento conforme seu arquivo egsDataGrid
        colunas_preview = ['Centro de custo', 'Obra', 'Item', 'Produto', 'Data Entrega']
        st.dataframe(df_up[[c for c in colunas_preview if c in df_up.columns]].head())
        
        if st.button("Confirmar Importação de Itens"):
            df_base = conn.read(worksheet="Pedidos", ttl=0)
            novos = []
            for _, r in df_up.iterrows():
                uid = f"{r['Centro de custo']}-{r['Item']}"
                if uid not in df_base['ID_Item'].astype(str).values:
                    novos.append({
                        "ID_Item": uid, 
                        "CTR": r['Centro de custo'], 
                        "Obra": r['Obra'], 
                        "Item": r['Item'],
                        "Pedido": r['Produto'], 
                        "Dono": r['Gestor'], # Captura o gestor direto do sistema
                        "Status_Atual": "Aguardando Gate 1",
                        "Data_Entrega": str(r['Data Entrega']), 
                        "Prev_Inicio": str(r['Prev. Inicio']) if 'Prev. Inicio' in r else "", 
                        "Prev_Fim": str(r['Prev. Fim']) if 'Prev. Fim' in r else "", 
                        "Quantidade": r['Quantidade'], 
                        "Unidade": r['Unidade']
                    })
            if novos:
                conn.update(worksheet="Pedidos", data=pd.concat([df_base, pd.DataFrame(novos)], ignore_index=True))
                st.success(f"{len(novos)} itens importados com sucesso!")
            else: st.warning("Nenhum item novo detectado.")

elif menu == "📊 Resumo e Prazos":
    st.header("🚦 Monitor de Produção (Itens)")
    try:
        df_p = conn.read(worksheet="Pedidos", ttl=0)
        df_p['Data_Entrega'] = pd.to_datetime(df_p['Data_Entrega'], errors='coerce')
        
        col1, col2 = st.columns(2)
        with col1: ctr_filter = st.multiselect("Filtrar por CTR", options=df_p['CTR'].unique())
        if ctr_filter: df_p = df_p[df_p['CTR'].isin(ctr_filter)]
        
        for _, row in df_p.sort_values(by='Data_Entrega').iterrows():
            dias = (row['Data_Entrega'].date() - date.today()).days if pd.notnull(row['Data_Entrega']) else None
            alerta = "🟢"
            classe = ""
            if dias is not None:
                if dias < 0: alerta = "❌ VENCIDO"; classe = "alerta-vencido"
                elif dias <= 3: alerta = "🔴 CRÍTICO"; classe = "alerta-vencido"
                elif dias <= 7: alerta = "🟡 ATENÇÃO"

            c1, c2, c3, c4 = st.columns([2, 4, 2, 1])
            with c1: st.write(f"**{row['CTR']}**\nItem: {row['Item']}")
            with c2: st.write(f"**{row['Pedido']}**\n👤 {row['Dono']}")
            with c3: st.write(f"📅 {row['Data_Entrega'].strftime('%d/%m/%Y') if pd.notnull(row['Data_Entrega']) else 'S/D'}\n📍 {row['Status_Atual']}")
            with c4:
                if classe: st.markdown(f'<div class="{classe}">{alerta}</div>', unsafe_allow_html=True)
                else: st.write(alerta)
            st.markdown("---")
    except Exception as e: st.error(f"Erro no monitor: {e}")

elif menu == "✅ Validar Gates por Item":
    tab1, tab2, tab3, tab4 = st.tabs(["Gate 1", "Gate 2", "Gate 3", "Gate 4"])
    with tab1:
        itens = {"Informações": ["Item identificado", "Medidas conferidas", "Tipo de obra definido"], "Escopo": ["Material definido", "Projeto técnico recebido"]}
        checklist_gate_item("GATE 1", "Checklist_G1", itens, "Dono do Pedido (DP)", "PCP", "Item mal definido ➡️ BLOQUEADO", "Aguardando Produção (G2)", "Impedir erro de projeto", "Antes da liberação")
    # ... (Manter tabs 2, 3 e 4 conforme script anterior)

elif menu == "⚠️ Alteração de Pedido":
    st.header("🔄 Edição e Alteração de Itens")
    df_p = conn.read(worksheet="Pedidos", ttl=0)
    # Criando identificador para seleção
    df_p['Busca_Edit'] = df_p['CTR'].astype(str) + " / " + df_p['Item'].astype(str) + " - " + df_p['Pedido'].str[:40]
    item_edit = st.selectbox("Selecione o Item para Editar", [""] + df_p['Busca_Edit'].tolist())
    
    if item_edit:
        # Encontra o item pelo identificador composto
        item_data = df_p[df_p['Busca_Edit'] == item_edit].iloc[0]
        uid = item_data['ID_Item']
        
        with st.form("edit_item"):
            col1, col2 = st.columns(2)
            novo_gestor = col1.text_input("Novo Gestor", value=item_data['Dono'])
            novo_prazo = col2.date_input("Nova Data de Entrega", value=pd.to_datetime(item_data['Data_Entrega']).date() if pd.notnull(item_data['Data_Entrega']) else date.today())
            motivo = st.text_area("Motivo da alteração (Histórico de Auditoria)")
            
            if st.form_submit_button("Salvar Alterações"):
                df_p.loc[df_p['ID_Item'] == uid, 'Dono'] = novo_gestor
                df_p.loc[df_p['ID_Item'] == uid, 'Data_Entrega'] = novo_prazo.strftime('%Y-%m-%d')
                conn.update(worksheet="Pedidos", data=df_p)
                
                df_alt = conn.read(worksheet="Alteracoes", ttl=0)
                nova_alt = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Pedido": item_data['Pedido'], "CTR": item_data['CTR'], "Usuario": papel_usuario, "O que mudou": f"Gestor: {novo_gestor}, Prazo: {novo_prazo}. Motivo: {motivo}"}])
                conn.update(worksheet="Alteracoes", data=pd.concat([df_alt, nova_alt], ignore_index=True))
                st.success("Dados atualizados e auditados!")

elif menu == "🚨 Auditoria":
    st.header("🚨 Histórico de Auditoria")
    df_aud = conn.read(worksheet="Alteracoes", ttl=0)
    st.dataframe(df_aud, use_container_width=True)

elif menu == "👤 Cadastro de Gestores":
    st.header("Gestores")
    with st.form("f_g"):
        n = st.text_input("Nome")
        if st.form_submit_button("Salvar"):
            df = conn.read(worksheet="Gestores", ttl=0)
            conn.update(worksheet="Gestores", data=pd.concat([df, pd.DataFrame([{"Nome": n}])], ignore_index=True))
            st.success("Salvo!")
