import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import os
import time

# Configuração da Página
st.set_page_config(page_title="Status - Gestão Integral por Item", layout="wide", page_icon="🏗️")

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

# --- FUNÇÃO: ATUALIZA O STATUS DO ITEM (SUPORTE A LOTE) ---
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
        "👤 Cadastro de Gestores",
        "⚠️ Alteração de Pedido"
    ])

# --- FUNÇÃO DE GESTÃO DE GATES (HÍBRIDA: UNITÁRIA E LOTE POR CTR) ---
def checklist_gate(gate_id, aba, itens_checklist, responsavel_r, executor_e, msg_bloqueio, proximo_status, objetivo, momento):
    st.header(f"Ficha de Controle: {gate_id}")
    st.markdown(f"**Objetivo:** {objetivo} | **Momento:** {momento}")
    st.info(f"⚖️ **R:** {responsavel_r} | 🔨 **E:** {executor_e}")
    
    try:
        df_pedidos = conn.read(worksheet="Pedidos", ttl=0)
        
        # Define o status que o item deve ter para aparecer neste Gate
        status_requerido = "Aguardando Gate 1" if gate_id == "GATE 1" else \
                           "Aguardando Produção (G2)" if gate_id == "GATE 2" else \
                           "Aguardando Materiais (G3)" if gate_id == "GATE 3" else \
                           "Aguardando Entrega (G4)"

        # 1. Seleciona a CTR
        ctr_lista = [""] + sorted(df_pedidos['CTR'].unique().tolist())
        ctr_sel = st.selectbox(f"Selecione a CTR (Pedido) para {gate_id}", ctr_lista, key=f"ctr_gate_{aba}")
        
        if ctr_sel:
            # 2. Filtra itens pendentes desta CTR para este Gate
            itens_pendentes = df_pedidos[(df_pedidos['CTR'] == ctr_sel) & (df_pedidos['Status_Atual'] == status_requerido)]
            
            if itens_pendentes.empty:
                st.success(f"Não há itens pendentes para o {gate_id} nesta CTR.")
                return

            # 3. Seleção em lote (Flegar itens)
            st.markdown("##### Selecione os itens para validar em lote:")
            selecionados = st.multiselect(
                "Itens disponíveis:",
                options=itens_pendentes['ID_Item'].tolist(),
                format_func=lambda x: itens_pendentes[itens_pendentes['ID_Item'] == x]['Pedido'].iloc[0],
                default=itens_pendentes['ID_Item'].tolist(),
                key=f"multi_{aba}"
            )
            
            if selecionados:
                pode_assinar = (papel_usuario == responsavel_r or papel_usuario == executor_e or papel_usuario == "Gerência Geral")
                if not pode_assinar: st.warning(f"⚠️ Acesso limitado.")

                with st.form(f"form_batch_{aba}"):
                    respostas = {}
                    for secao, itens in itens_checklist.items():
                        st.markdown(f"#### 🔹 {secao}")
                        for item in itens: respostas[item] = st.checkbox(item)
                    
                    obs = st.text_area("Observações Técnicas (válidas para todo o lote selecionado)")
                    
                    if st.form_submit_button("VALIDAR LOTE SELECIONADO 🚀", disabled=not pode_assinar):
                        if not all(respostas.values()):
                            st.error(f"❌ BLOQUEIO: {msg_bloqueio}")
                        else:
                            # Registra na aba do Gate para cada item
                            df_gate = conn.read(worksheet=aba, ttl=0)
                            novas_linhas = []
                            for id_item in selecionados:
                                nova = {"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "ID_Item": id_item, "Validado_Por": papel_usuario, "Obs": obs}
                                nova.update(respostas)
                                novas_linhas.append(nova)
                            
                            conn.update(worksheet=aba, data=pd.concat([df_gate, pd.DataFrame(novas_linhas)], ignore_index=True))
                            
                            # Atualiza status em lote
                            atualizar_status_lote(selecionados, proximo_status)
                            
                            st.success(f"🚀 {len(selecionados)} itens avançaram para {proximo_status}!")
                            disparar_foguete()
                            time.sleep(1)
                            st.rerun()
    except Exception as e: st.error(f"Erro no processamento: {e}")

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

elif menu == "📦 Gestão por Pedido":
    st.header("📦 Gestão de Itens por CTR")
    try:
        df_p = conn.read(worksheet="Pedidos", ttl=0)
        ctr_lista = df_p['CTR'].unique().tolist()
        ctr_sel = st.selectbox("Selecione a CTR (Pedido) para gerenciar todos os itens:", [""] + ctr_lista)
        if ctr_sel:
            itens_ctr = df_p[df_p['CTR'] == ctr_sel].copy()
            st.info(f"Gerenciando {len(itens_ctr)} itens da obra: {itens_ctr['Obra'].iloc[0]}")
            for idx, row in itens_ctr.iterrows():
                with st.expander(f"Item: {row['Pedido']} | Status: {row['Status_Atual']}"):
                    with st.form(f"form_edit_{row['ID_Item']}"):
                        col1, col2 = st.columns(2)
                        n_gestor = col1.text_input("Gestor Responsável", value=row['Dono'])
                        n_data = col2.date_input("Data de Entrega", value=pd.to_datetime(row['Data_Entrega']).date() if pd.notnull(row['Data_Entrega']) else date.today())
                        n_motivo = st.text_area("Motivo do Ajuste Manual")
                        if st.form_submit_button("Salvar Alterações"):
                            df_p.loc[df_p['ID_Item'] == row['ID_Item'], 'Dono'] = n_gestor
                            df_p.loc[df_p['ID_Item'] == row['ID_Item'], 'Data_Entrega'] = n_data.strftime('%Y-%m-%d')
                            conn.update(worksheet="Pedidos", data=df_p)
                            df_alt = conn.read(worksheet="Alteracoes", ttl=0)
                            log = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Pedido": row['Pedido'], "CTR": row['CTR'], "Usuario": papel_usuario, "O que mudou": f"Ajuste Manual: Gestor={n_gestor}, Prazo={n_data}. Motivo: {n_motivo}"}])
                            conn.update(worksheet="Alteracoes", data=pd.concat([df_alt, log], ignore_index=True))
                            st.success(f"Item {row['Pedido']} atualizado!")
                            st.rerun()
    except Exception as e: st.error(f"Erro na gestão: {e}")

elif menu == "📥 Importar Itens (Sistema)":
    st.header("📥 Importar Itens da Marcenaria")
    up = st.file_uploader("Arquivo egsDataGrid", type=["csv", "xlsx"])
    if up:
        try:
            df_up = pd.read_csv(up) if up.name.endswith('csv') else pd.read_excel(up)
            st.dataframe(df_up[['Centro de custo', 'Obra', 'Produto', 'Data Entrega']].head())
            if st.button("Confirmar Importação"):
                df_base = conn.read(worksheet="Pedidos", ttl=0)
                novos = []
                for _, r in df_up.iterrows():
                    uid = f"{r['Centro de custo']}-{r['Produto']}"
                    if uid not in df_base['ID_Item'].astype(str).values:
                        novos.append({
                            "ID_Item": uid, "CTR": r['Centro de custo'], "Obra": r['Obra'], "Item": r['Item'],
                            "Pedido": r['Produto'], "Dono": r['Gestor'], "Status_Atual": "Aguardando Gate 1",
                            "Data_Entrega": str(r['Data Entrega']), "Prev_Inicio": str(r['Prev. Inicio']) if 'Prev. Inicio' in r else "", 
                            "Prev_Fim": str(r['Prev. Fim']) if 'Prev. Fim' in r else "", 
                            "Quantidade": r['Quantidade'], "Unidade": r['Unidade']
                        })
                if novos:
                    conn.update(worksheet="Pedidos", data=pd.concat([df_base, pd.DataFrame(novos)], ignore_index=True))
                    st.success(f"{len(novos)} itens importados!")
                else: st.warning("Itens já existentes.")
        except Exception as e: st.error(f"Erro: {e}")

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

elif menu == "🚨 Auditoria":
    st.header("🚨 Auditoria")
    df_aud = conn.read(worksheet="Alteracoes", ttl=0)
    st.table(df_aud)

elif menu == "👤 Cadastro de Gestores":
    st.header("Gestores")
    with st.form("f_g"):
        n = st.text_input("Nome")
        if st.form_submit_button("Salvar"):
            df = conn.read(worksheet="Gestores", ttl=0)
            conn.update(worksheet="Gestores", data=pd.concat([df, pd.DataFrame([{"Nome": n}])], ignore_index=True))
            st.success("Salvo!")

elif menu == "⚠️ Alteração de Pedido":
    # Função mantida por compatibilidade com script anterior
    st.header("🔄 Edição Unitária")
    # (Código de edição unitária que já estava no script anterior...)
