import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import os
import time

# Configuração da Página
st.set_page_config(page_title="ERCI - Gestão em Lote", layout="wide", page_icon="🏗️")

# --- FUNÇÃO DE AUTO-REFRESH (5 MINUTOS) ---
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 300:
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
    .alerta-vencido { color: white; background-color: #FF0000; padding: 5px; border-radius: 5px; font-weight: bold; animation: blinker 1s linear infinite; text-align: center; }
    @keyframes rocket-launch { 0% { transform: translateY(100vh) translateX(0px); opacity: 1; } 100% { transform: translateY(-100vh) translateX(-20px); opacity: 0; } }
    .rocket-container { position: fixed; bottom: -100px; left: 50%; font-size: 50px; z-index: 9999; animation: rocket-launch 3s ease-in forwards; }
    </style>
    """, unsafe_allow_html=True)

def disparar_foguete():
    st.markdown('<div class="rocket-container">🚀</div>', unsafe_allow_html=True)

# Conexão com Planilha
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO: ATUALIZA STATUS EM LOTE ---
def atualizar_status_lote(lista_ids, novo_status):
    df_pedidos = conn.read(worksheet="Pedidos", ttl=0)
    df_pedidos.loc[df_pedidos['ID_Item'].isin(lista_ids), 'Status_Atual'] = novo_status
    conn.update(worksheet="Pedidos", data=df_pedidos)

# --- MENU LATERAL ---
if os.path.exists("Status Apresentação.png"):
    st.sidebar.image("Status Apresentação.png", use_container_width=True)
else:
    st.sidebar.title("STATUS MARCENARIA")

st.sidebar.markdown("---")
papel_usuario = st.sidebar.selectbox("Seu Papel Hoje (ERCI):", 
    ["PCP", "Dono do Pedido (DP)", "Produção", "Compras", "Financeiro", "Logística", "Gerência Geral"])

menu = st.sidebar.radio("Navegação", 
    [
        "📊 Resumo e Prazos", 
        "📦 Gestão por Pedido",
        "🚨 Auditoria", 
        "📥 Importar Itens (Sistema)",
        "✅ Gate 1: Aceite Técnico", 
        "🏭 Gate 2: Produção", 
        "💰 Gate 3: Material", 
        "🚛 Gate 4: Entrega",
        "👤 Cadastro de Gestores"
    ])

# --- FUNÇÃO DE GESTÃO DE GATES EM LOTE (HÍBRIDO) ---
def checklist_gate(gate_id, aba, itens_checklist, responsavel_r, executor_e, msg_bloqueio, proximo_status, objetivo, momento):
    st.header(f"Ficha de Controle: {gate_id}")
    st.markdown(f"**Objetivo:** {objetivo} | **Momento:** {momento}")
    st.info(f"⚖️ **R:** {responsavel_r} | 🔨 **E:** {executor_e}")
    
    try:
        df_pedidos = conn.read(worksheet="Pedidos", ttl=0)
        
        # 1. Seleciona a CTR primeiro
        ctr_lista = [""] + sorted(df_p['CTR'].unique().tolist()) if 'df_p' in locals() else [""] + sorted(df_pedidos['CTR'].unique().tolist())
        ctr_sel = st.selectbox(f"1º Passo: Selecione a CTR (Obra) para {gate_id}", ctr_lista, key=f"ctr_{aba}")
        
        if ctr_sel:
            # 2. Filtra itens da CTR que estão no status correto para este Gate
            # (Se for Gate 1, status deve ser 'Aguardando Gate 1', etc)
            filtro_status = "Aguardando Gate 1" if gate_id == "GATE 1" else \
                            "Aguardando Produção (G2)" if gate_id == "GATE 2" else \
                            "Aguardando Materiais (G3)" if gate_id == "GATE 3" else \
                            "Aguardando Entrega (G4)"
            
            itens_pendentes = df_pedidos[(df_pedidos['CTR'] == ctr_sel) & (df_pedidos['Status_Atual'] == filtro_status)]
            
            if itens_pendentes.empty:
                st.success(f"Todos os itens desta CTR já passaram pelo {gate_id} ou estão em outros estágios.")
                return

            # 3. Seleção de itens em lote
            st.markdown(f"**2º Passo: Marque os itens da CTR que deseja validar em lote:**")
            selecionados = st.multiselect("Itens Pendentes:", options=itens_pendentes['ID_Item'].tolist(), 
                                         format_func=lambda x: f"{x.split('-')[-1]}", # Mostra só o nome do produto
                                         default=itens_pendentes['ID_Item'].tolist())
            
            if selecionados:
                pode_assinar = (papel_usuario == responsavel_r or papel_usuario == executor_e or papel_usuario == "Gerência Geral")
                if not pode_assinar: st.warning(f"⚠️ Acesso limitado a {responsavel_r} ou {executor_e}.")

                with st.form(f"form_lote_{aba}"):
                    respostas = {}
                    for secao, itens in itens_checklist.items():
                        st.markdown(f"#### 🔹 {secao}")
                        for item in itens: respostas[item] = st.checkbox(item)
                    
                    obs = st.text_area("Observações Técnicas para este lote")
                    
                    if st.form_submit_button("VALIDAR LOTE DE ITENS 🚀", disabled=not pode_assinar):
                        if not all(respostas.values()):
                            st.error(f"❌ BLOQUEIO: {msg_bloqueio}")
                        else:
                            # Processamento do Lote
                            df_gate = conn.read(worksheet=aba, ttl=0)
                            novas_entradas = []
                            for id_item in selecionados:
                                item_nome = df_pedidos[df_pedidos['ID_Item'] == id_item]['Pedido'].iloc[0]
                                nova = {"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "ID_Item": id_item, "Validado_Por": papel_usuario, "Obs": obs}
                                nova.update(respostas)
                                novas_entradas.append(nova)
                            
                            conn.update(worksheet=aba, data=pd.concat([df_gate, pd.DataFrame(novas_entradas)], ignore_index=True))
                            atualizar_status_lote(selecionados, proximo_status)
                            st.success(f"🚀 Sucesso! {len(selecionados)} itens avançaram para: {proximo_status}")
                            disparar_foguete()
                            time.sleep(1)
                            st.rerun()
    except Exception as e: st.error(f"Erro no processamento em lote: {e}")

# --- PÁGINAS ---

if menu == "📊 Resumo e Prazos":
    st.header("🚦 Monitor de Produção (Itens)")
    try:
        df_p = conn.read(worksheet="Pedidos", ttl=0)
        df_p['Data_Entrega'] = pd.to_datetime(df_p['Data_Entrega'], errors='coerce')
        for idx, row in df_p.sort_values(by='Data_Entrega', na_position='last').iterrows():
            dias = (row['Data_Entrega'].date() - date.today()).days if pd.notnull(row['Data_Entrega']) else None
            classe = "alerta-vencido" if dias is not None and dias <= 3 else ""
            c1, c2, c3, c4 = st.columns([2, 4, 2, 1])
            with c1: st.write(f"**{row['CTR']}**")
            with c2: st.write(f"**{row['Pedido']}**\n👤 {row['Dono']}")
            with c3: st.write(f"📍 {row['Status_Atual']}\n📅 {row['Data_Entrega'].strftime('%d/%m/%Y') if pd.notnull(row['Data_Entrega']) else 'S/D'}")
            with c4:
                if classe: st.markdown(f'<div class="{classe}">⚠️ ALERTA</div>', unsafe_allow_html=True)
                else: st.write("🟢 OK")
            st.markdown("---")
    except: st.error("Erro no monitor.")

elif menu == "✅ Gate 1: Aceite Técnico":
    itens = {
        "Informações Comerciais": ["Pedido registrado no sistema", "Cliente identificado", "Tipo de obra definido", "Responsável identificado"],
        "Escopo Técnico": ["Projeto mínimo recebido", "Ambientes definidos", "Materiais principais definidos", "Itens fora do padrão identificados"],
        "Prazo (prévia)": ["Prazo solicitado registrado", "Prazo avaliado tecnicamente", "Risco de prazo identificado"],
        "Governança": ["Dono do Pedido definido", "PCP validou viabilidade inicial", "Pedido aprovado formalmente"]
    }
    checklist_gate("GATE 1", "Checklist_G1", itens, "Dono do Pedido (DP)", "PCP", "Projeto incompleto ➡️ BLOQUEADO", "Aguardando Produção (G2)", "Impedir entrada mal definida", "Antes do plano")

elif menu == "🏭 Gate 2: Produção":
    itens = {
        "Planejamento": ["Pedido sequenciado na programação", "Capacidade validada", "Gargalo identificado", "Gargalo protegido no plano"],
        "Projeto": ["Projeto técnico liberado", "Medidas conferidas", "Versão do projeto registrada"],
        "Comunicação": ["Produção ciente do plano", "Prazo interno registrado", "Alterações registradas"]
    }
    checklist_gate("GATE 2", "Checklist_G2", itens, "PCP", "Produção", "Sem plano ➡️ BLOQUEADO", "Aguardando Materiais (G3)", "Produzir planejado", "No corte")

elif menu == "💰 Gate 3: Material":
    itens = {
        "Materiais": ["Lista de materiais validada", "Quantidades conferidas", "Materiais especiais"],
        "Compras": ["Fornecedores definidos", "Lead times confirmados", "Datas registradas"],
        "Financeiro": ["Impacto caixa validado", "Compra autorizada", "Forma de pagamento"]
    }
    checklist_gate("GATE 3", "Checklist_G3", itens, "Financeiro", "Compras", "Falta material ➡️ PARADO", "Aguardando Entrega (G4)", "Fábrica sem parada", "Na montagem")

elif menu == "🚛 Gate 4: Entrega":
    itens = {
        "Produto": ["Produção concluída", "Qualidade conferida", "Separados por pedido"],
        "Logística": ["Checklist carga preenchido", "Frota definida", "Rota planejada"],
        "Prazo": ["Data validada com logística", "Cliente informado", "Equipe montagem alinhada"]
    }
    checklist_gate("GATE 4", "Checklist_G4", itens, "Dono do Pedido (DP)", "Logística", "Erro acabamento ➡️ NÃO carrega", "CONCLUÍDO ✅", "Entrega perfeita", "Na carga")

# ... (Manter demais páginas: Importação, Gestão por Pedido, Auditoria, Gestores)
