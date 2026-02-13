import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import os

# Configuração da Página
st.set_page_config(page_title="Status - Gestão e Prazos", layout="wide", page_icon="🏗️")

# Estilização Status
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { color: #634D3E !important; }
    .stButton>button { background-color: #634D3E; color: white; border-radius: 5px; width: 100%; }
    .stDataFrame { border: 1px solid #634D3E; }
    </style>
    """, unsafe_allow_html=True)

# Conexão com Planilha
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO: ATUALIZA O STATUS NO RESUMO ---
def atualizar_quadro_resumo(nome_pedido, novo_status):
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
    ["🆕 Novo Pedido", "✅ Gate 1: Aceite Técnico", "🏭 Gate 2: Produção", "💰 Gate 3: Material", "🚛 Gate 4: Entrega", "📊 Resumo e Prazos", "🚨 Auditoria"])

# --- FUNÇÃO DE GESTÃO DE GATES ---
def checklist_gate(gate_id, aba, itens_checklist, responsavel_r, executor_e, msg_bloqueio, proximo_status):
    st.header(f"Ficha de Controle: {gate_id}")
    st.info(f"⚖️ **Responsável (R):** {responsavel_r} | 🔨 **Executor (E):** {executor_e}")
    
    try:
        df_pedidos = conn.read(worksheet="Pedidos", ttl=0)
        pedido_sel = st.selectbox("Selecione o Pedido", [""] + df_pedidos["Pedido"].tolist())
    except:
        st.error("Erro ao ler aba Pedidos.")
        return

    if pedido_sel:
        pode_assinar = (papel_usuario == responsavel_r or papel_usuario == executor_e or papel_usuario == "Gerência Geral")
        
        with st.form(f"form_{aba}"):
            respostas = {}
            for secao, itens in itens_checklist.items():
                st.markdown(f"**{secao}**")
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
                    updated_df = pd.concat([df_gate, pd.DataFrame([nova_linha])], ignore_index=True)
                    conn.update(worksheet=aba, data=updated_df)
                    
                    atualizar_quadro_resumo(pedido_sel, proximo_status)
                    st.success(f"🚀 Sucesso! Pedido avançou para: {proximo_status}")
                    st.balloons()

# --- PÁGINAS ---
if menu == "🆕 Novo Pedido":
    st.header("Cadastrar Novo Pedido / Obra")
    with st.form("cadastro_pedido"):
        nome = st.text_input("Nome do Pedido")
        desc = st.text_area("Descrição")
        prazo = st.date_input("Data Prometida de Entrega", min_value=date.today())
        if st.form_submit_button("Criar Ficha do Pedido"):
            if nome:
                df = conn.read(worksheet="Pedidos", ttl=0)
                novo = pd.DataFrame([{
                    "Data": date.today().strftime("%d/%m/%Y"), 
                    "Pedido": nome, 
                    "Descricao": desc, 
                    "Dono": papel_usuario, 
                    "Status_Atual": "Aguardando Gate 1",
                    "Prazo_Entrega": prazo.strftime("%Y-%m-%d")
                }])
                conn.update(worksheet="Pedidos", data=pd.concat([df, novo], ignore_index=True))
                st.success(f"Pedido {nome} cadastrado com prazo para {prazo.strftime('%d/%m/%Y')}!")
            else:
                st.error("O nome do pedido é obrigatório.")

elif menu == "✅ Gate 1: Aceite Técnico":
    itens = {"🔹 Checklist": ["Pedido registrado", "Cliente identificado", "Projeto mínimo recebido", "Prazo comercial avaliado", "Dono do Pedido definido", "PCP validou viabilidade"]}
    checklist_gate("GATE 1", "Checklist_G1", itens, "Dono do Pedido (DP)", "PCP", "Checklist incompleto!", "Aguardando Produção (G2)")

elif menu == "🏭 Gate 2: Produção":
    itens = {"🔹 Checklist": ["Pedido sequenciado", "Capacidade validada", "Gargalo protegido", "Projeto técnico liberado", "Medidas conferidas", "Produção ciente do plano"]}
    checklist_gate("GATE 2", "Checklist_G2", itens, "PCP", "Produção", "Checklist incompleto!", "Aguardando Materiais (G3)")

elif menu == "💰 Gate 3: Material":
    itens = {"🔹 Checklist": ["Lista validada", "Lead times confirmados", "Impacto no caixa validado", "Compra autorizada Financeiro"]}
    checklist_gate("GATE 4", "Checklist_G3", itens, "Financeiro", "Compras", "Checklist incompleto!", "Aguardando Entrega (G4)")

elif menu == "🚛 Gate 4: Entrega":
    itens = {"🔹 Checklist": ["Produção concluída", "Qualidade conferida", "Checklist de carga ok", "Rota planejada", "Cliente informado"]}
    checklist_gate("GATE 4", "Checklist_G4", itens, "Dono do Pedido (DP)", "Logística", "Checklist incompleto!", "CONCLUÍDO ✅")

elif menu == "📊 Resumo e Prazos":
    st.header("🚦 Monitor de Pedidos e Prazos")
    df_p = conn.read(worksheet="Pedidos", ttl=0)
    
    # Lógica de cálculo de dias restantes
    df_p['Prazo_Entrega'] = pd.to_datetime(df_p['Prazo_Entrega'])
    df_p['Dias_Restantes'] = (df_p['Prazo_Entrega'].dt.date - date.today()).apply(lambda x: x.days)
    
    # Função para o Semáforo Visual
    def alerta_prazo(dias):
        if dias < 0: return "❌ VENCIDO"
        if dias <= 3: return "🔴 CRÍTICO"
        if dias <= 7: return "🟡 ATENÇÃO"
        return "🟢 NO PRAZO"

    df_p['Alerta_Prazo'] = df_p['Dias_Restantes'].apply(alerta_prazo)
    
    # Exibição organizada
    st.dataframe(
        df_p[['Pedido', 'Status_Atual', 'Prazo_Entrega', 'Dias_Restantes', 'Alerta_Prazo']].sort_values(by='Dias_Restantes'), 
        use_container_width=True
    )

elif menu == "🚨 Auditoria":
    st.header("🚨 Auditoria de Governança")
    st.error("Qualquer exceção mata o ERCI! Monitoramento de frases de burla:")
    st.write("- 'É urgente!'")
    st.write("- 'Sempre foi assim!'")
    st.write("- 'Só dessa vez!'")
