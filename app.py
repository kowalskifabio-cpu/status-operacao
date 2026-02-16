import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import os
import time

# Configuração da Página
st.set_page_config(page_title="Status - Gestão Integral de Gates", layout="wide", page_icon="🏗️")

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
    
    /* Animação para pedidos atrasados ou críticos */
    @keyframes blinker {
        50% { opacity: 0.3; }
    }
    .alerta-vencido {
        color: white;
        background-color: #FF0000;
        padding: 5px;
        border-radius: 5px;
        font-weight: bold;
        animation: blinker 1s linear infinite;
        text-align: center;
    }

    /* Animação do Foguete */
    @keyframes rocket-launch {
        0% { transform: translateY(100vh) translateX(0px); opacity: 1; }
        50% { transform: translateY(50vh) translateX(20px); }
        100% { transform: translateY(-100vh) translateX(-20px); opacity: 0; }
    }
    .rocket-container {
        position: fixed;
        bottom: -100px;
        left: 50%;
        font-size: 50px;
        z-index: 9999;
        animation: rocket-launch 3s ease-in forwards;
    }
    </style>
    """, unsafe_allow_html=True)

# Função para disparar animação do foguete
def disparar_foguete():
    st.markdown('<div class="rocket-container">🚀</div>', unsafe_allow_html=True)

# Conexão com Planilha
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO: ATUALIZA O STATUS NO RESUMO ---
def atualizar_quadro_resumo(identificador_composto, novo_status):
    nome_pedido = identificador_composto.split(" / ")[1]
    df_pedidos = conn.read(worksheet="Pedidos", ttl=0)
    df_pedidos.loc[df_pedidos['Pedido'] == nome_pedido, 'Status_Atual'] = novo_status
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
        "🚨 Auditoria", 
        "👤 Cadastro de Gestores", 
        "🆕 Novo Pedido", 
        "✅ Gate 1: Aceite Técnico", 
        "🏭 Gate 2: Produção", 
        "💰 Gate 3: Material", 
        "🚛 Gate 4: Entrega", 
        "⚠️ Alteração de Pedido"
    ])

# --- FUNÇÃO DE GESTÃO DE GATES (INTEGRAL COM IDENTIFICAÇÃO CTR/PEDIDO) ---
def checklist_gate(gate_id, aba, itens_checklist, responsavel_r, executor_e, msg_bloqueio, proximo_status, objetivo, momento):
    st.header(f"Ficha de Controle: {gate_id}")
    st.markdown(f"**Objetivo:** {objetivo}")
    st.markdown(f"**Momento:** {momento}")
    st.info(f"⚖️ **Responsável (R):** {responsavel_r} | 🔨 **Executor (E):** {executor_e}")
    
    try:
        df_pedidos = conn.read(worksheet="Pedidos", ttl=0)
        df_pedidos['Identificador'] = df_pedidos['CTR'].astype(str) + " / " + df_pedidos['Pedido']
        lista_pedidos = [""] + df_pedidos['Identificador'].tolist()
        
        pedido_sel = st.selectbox(f"Selecione o Pedido (CTR/Pedido) para {gate_id}", lista_pedidos, key=f"sel_{aba}")
        
        if pedido_sel:
            nome_real = pedido_sel.split(" / ")[1]
            status_atual = df_pedidos.loc[df_pedidos['Pedido'] == nome_real, 'Status_Atual'].values[0]
            
            concluido = False
            if gate_id == "GATE 1" and status_atual != "Aguardando Gate 1": concluido = True
            elif gate_id == "GATE 2" and status_atual not in ["Aguardando Gate 1", "Aguardando Produção (G2)"]: concluido = True
            elif gate_id == "GATE 3" and status_atual not in ["Aguardando Gate 1", "Aguardando Produção (G2)", "Aguardando Materiais (G3)"]: concluido = True
            elif gate_id == "GATE 4" and status_atual == "CONCLUÍDO ✅": concluido = True

            if concluido:
                st.warning(f"✅ Este Gate já foi aprovado anteriormente. Status atual: **{status_atual}**.")
                if papel_usuario != "Gerência Geral":
                    return
    except:
        st.error("Erro ao ler aba Pedidos.")
        return

    if pedido_sel:
        pode_assinar = (papel_usuario == responsavel_r or papel_usuario == executor_e or papel_usuario == "Gerência Geral")
        if not pode_assinar:
            st.warning(f"⚠️ Acesso limitado.")

        with st.form(f"form_{aba}"):
            respostas = {}
            for secao, itens in itens_checklist.items():
                st.markdown(f"#### 🔹 {secao}")
                for item in itens:
                    respostas[item] = st.checkbox(item)
            
            obs = st.text_area("Observações Técnicas")
            btn = st.form_submit_button("VALIDAR E AVANÇAR PROCESSO 🚀", disabled=not pode_assinar)
            
            if btn:
                if not all(respostas.values()):
                    st.error(f"❌ BLOQUEIO: {msg_bloqueio}")
                else:
                    df_gate = conn.read(worksheet=aba, ttl=0)
                    nova_linha = {"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Pedido": pedido_sel, "Validado_Por": papel_usuario, "Obs": obs}
                    nova_linha.update(respostas)
                    conn.update(worksheet=aba, data=pd.concat([df_gate, pd.DataFrame([nova_linha])], ignore_index=True))
                    
                    atualizar_quadro_resumo(pedido_sel, proximo_status)
                    st.success(f"🚀 Sucesso!")
                    disparar_foguete() # TROCADO PARA FOGUETE

# --- PÁGINAS ---

if menu == "📊 Resumo e Prazos":
    st.header("🚦 Monitor de Pedidos e Prazos")
    try:
        df_p = conn.read(worksheet="Pedidos", ttl=0)
        df_p['Prazo_Entrega'] = pd.to_datetime(df_p['Prazo_Entrega'], errors='coerce')
        df_p['Dias_Restantes'] = df_p.apply(lambda row: (row['Prazo_Entrega'].date() - date.today()).days if pd.notnull(row['Prazo_Entrega']) else None, axis=1)
        
        def alerta_prazo(dias):
            if dias is None: return "⚪ SEM DATA"
            if dias < 0: return "❌ VENCIDO"
            if dias <= 3: return "🔴 CRÍTICO"
            if dias <= 7: return "🟡 ATENÇÃO"
            return "🟢 NO PRAZO"
            
        df_p['Alerta'] = df_p['Dias_Restantes'].apply(alerta_prazo)
        
        # Aplica o efeito visual de piscar no monitor apenas para Vencidos e Críticos
        st.subheader("Pedidos em Produção")
        for idx, row in df_p.sort_values(by='Dias_Restantes', na_position='last').iterrows():
            col_a, col_b, col_c, col_d = st.columns([2, 1, 2, 1])
            with col_a: st.write(f"**{row['Pedido']}** (CTR: {row['CTR']})")
            with col_b: st.write(f"👤 {row['Dono']}")
            with col_c: st.write(f"📍 {row['Status_Atual']}")
            with col_d:
                if row['Alerta'] in ["❌ VENCIDO", "🔴 CRÍTICO"]:
                    st.markdown(f'<div class="alerta-vencido">{row["Alerta"]} ({row["Dias_Restantes"]} dias)</div>', unsafe_allow_html=True)
                else:
                    st.write(f"{row['Alerta']}")
            st.markdown("---")

    except Exception as e:
        st.error(f"Erro: {e}")

elif menu == "🚨 Auditoria":
    st.header("🚨 Auditoria e Histórico")
    try:
        df_aud = conn.read(worksheet="Alteracoes", ttl=0)
        st.dataframe(df_aud, use_container_width=True)
    except:
        st.write("Sem registros.")

elif menu == "👤 Cadastro de Gestores":
    st.header("Cadastro de Gestores")
    with st.form("form_gestores"):
        novo_nome = st.text_input("Nome Completo")
        if st.form_submit_button("Salvar"):
            if novo_nome:
                df_g = conn.read(worksheet="Gestores", ttl=0)
                conn.update(worksheet="Gestores", data=pd.concat([df_g, pd.DataFrame([{"Nome": novo_nome}])], ignore_index=True))
                st.success("Cadastrado!")

elif menu == "🆕 Novo Pedido":
    st.header("Cadastrar Novo Pedido")
    try:
        df_gestores = conn.read(worksheet="Gestores", ttl=0)
        lista_gestores = df_gestores["Nome"].tolist()
    except:
        lista_gestores = []
    
    with st.form("cadastro_pedido"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome do Pedido / Cliente")
            ctr = st.text_input("CTR")
        with col2:
            gestor_responsavel = st.selectbox("Gestor Responsável", lista_gestores)
            prazo = st.date_input("Prazo de Entrega", min_value=date.today())
        desc = st.text_area("Descrição")
        
        if st.form_submit_button("Criar Pedido"):
            if nome and ctr and gestor_responsavel:
                df = conn.read(worksheet="Pedidos", ttl=0)
                if ctr in df['CTR'].astype(str).values:
                    st.error("❌ CTR Duplicado!")
                else:
                    novo = pd.DataFrame([{"Data": date.today().strftime("%d/%m/%Y"), "Pedido": nome, "CTR": ctr, "Descricao": desc, "Dono": gestor_responsavel, "Status_Atual": "Aguardando Gate 1", "Prazo_Entrega": prazo.strftime("%Y-%m-%d")}])
                    conn.update(worksheet="Pedidos", data=pd.concat([df, novo], ignore_index=True))
                    st.success("Cadastrado!")

elif menu == "✅ Gate 1: Aceite Técnico":
    itens = {"Informações Commercial": ["Pedido registrado no sistema", "Cliente identificado", "Tipo de obra definido", "Responsável identificado"], "Escopo Técnico": ["Projeto mínimo recebido", "Ambientes definidos", "Materiais principais", "Itens fora do padrão"], "Prazo (prévia)": ["Prazo solicitado registrado", "Prazo avaliado", "Risco de prazo"], "Governança": ["Dono do Pedido definido", "PCP validou viabilidade", "Aprovado formalmente"]}
    checklist_gate("GATE 1", "Checklist_G1", itens, "Dono do Pedido (DP)", "PCP", "Projeto incompleto ➡️ BLOQUEADO", "Aguardando Produção (G2)", "impedir entrada mal definida", "antes do planejamento")

elif menu == "🏭 Gate 2: Produção":
    itens = {"Planejamento": ["Pedido sequenciado", "Capacidade validada", "Gargalo identificado", "Gargalo protegido"], "Projeto": ["Projeto técnico liberado", "Medidas conferidas", "Versão registrada"], "Comunicação": ["Produção ciente", "Prazo interno registrado", "Alterações registradas"]}
    checklist_gate("GATE 2", "Checklist_G2", itens, "PCP", "Produção", "Fora de sequência ➡️ NÃO inicia", "Aguardando Materiais (G3)", "garantir execução do plano", "antes de cortar")

elif menu == "💰 Gate 3: Material":
    itens = {"Materiais": ["Lista validada", "Quantidades conferidas", "Materiais especiais"], "Compras": ["Fornecedores definidos", "Lead times confirmados", "Datas registradas"], "Financeiro": ["Impacto caixa validado", "Compra autorizada", "Forma de pagamento"]}
    checklist_gate("GATE 3", "Checklist_G3", itens, "Financeiro", "Compras", "Material crítico não comprado ➡️ BLOQUEADA", "Aguardando Entrega (G4)", "eliminar produção sem material", "antes do início físico")

elif menu == "🚛 Gate 4: Entrega":
    itens = {"Produto": ["Produção concluída", "Qualidade conferida", "Separados por pedido"], "Logística": ["Checklist carga", "Frota definida", "Rota planejada"], "Prazo": ["Data validada com logística", "Cliente informado", "Equipe montagem"]}
    checklist_gate("GATE 4", "Checklist_G4", itens, "Dono do Pedido (DP)", "Logística", "Produto incompleto ➡️ NÃO autorizada", "CONCLUÍDO ✅", "garantir entrega sem retrabalho", "antes de prometer data")

elif menu == "⚠️ Alteração de Pedido":
    st.header("🔄 Registro de Alteração de Escopo")
    try:
        df_p = conn.read(worksheet="Pedidos", ttl=0)
        df_p['Identificador'] = df_p['CTR'].astype(str) + " / " + df_p['Pedido']
        pedido_alt = st.selectbox("Selecione o Pedido (CTR/Pedido)", [""] + df_p['Identificador'].tolist())
        if pedido_alt:
            nome_real = pedido_alt.split(" / ")[1]
            ctr_vinculada = df_p.loc[df_p['Pedido'] == nome_real, 'CTR'].values[0]
            with st.form("form_alt"):
                mudanca = st.text_area("O que mudou?")
                if st.form_submit_button("Registrar Alteração"):
                    df_alt = conn.read(worksheet="Alteracoes", ttl=0)
                    nova = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Pedido": nome_real, "CTR": ctr_vinculada, "Usuario": papel_usuario, "O que mudou": mudanca}])
                    conn.update(worksheet="Alteracoes", data=pd.concat([df_alt, nova], ignore_index=True))
                    st.success("Alteração registrada!")
                    disparar_foguete()
    except: st.error("Erro ao carregar dados.")
