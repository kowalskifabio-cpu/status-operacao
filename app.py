import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import os

# Configuração da Página
st.set_page_config(page_title="Status - Gestão Operacional", layout="wide", page_icon="🏗️")

# Estilização Status
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { color: #634D3E !important; }
    .stButton>button { background-color: #634D3E; color: white; border-radius: 5px; width: 100%; }
    .stExpander { border: 1px solid #B59572; }
    </style>
    """, unsafe_allow_html=True)

# Conexão com Planilha
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO PARA ATUALIZAR STATUS NO RESUMO ---
def atualizar_status_pedido(nome_pedido, novo_status):
    df_pedidos = conn.read(worksheet="Pedidos", ttl=0)
    # Localiza o pedido e altera o status
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
    ["🆕 Novo Pedido", "✅ Gate 1: Aceite Técnico", "🏭 Gate 2: Produção", "💰 Gate 3: Material", "🚛 Gate 4: Entrega", "📊 Resumo Geral"])

# --- FUNÇÃO DE GESTÃO DE GATES ---
def checklist_gate(gate_id, aba, itens_checklist, responsavel_r, executor_e, msg_bloqueio, proximo_status):
    st.header(f"Ficha de Controle: {gate_id}")
    st.info(f"⚖️ **Responsável (R):** {responsavel_r} | 🔨 **Executor (E):** {executor_e}")
    
    try:
        df_pedidos = conn.read(worksheet="Pedidos", ttl=0)
        pedido_sel = st.selectbox("Selecione o Pedido", [""] + df_pedidos["Pedido"].tolist())
    except:
        st.error("Aba 'Pedidos' não encontrada. Cadastre um pedido primeiro.")
        return

    if pedido_sel:
        pode_assinar = (papel_usuario == responsavel_r or papel_usuario == executor_e or papel_usuario == "Gerência Geral")
        
        if not pode_assinar:
            st.warning(f"⚠️ Acesso limitado: Apenas {responsavel_r} ou {executor_e} validam este Gate.")

        with st.form(f"form_{aba}"):
            respostas = {}
            for secao, itens in itens_checklist.items():
                st.markdown(f"**{secao}**")
                for item in itens:
                    respostas[item] = st.checkbox(item)
            
            obs = st.text_area("Observações Técnicas")
            btn = st.form_submit_button("VALIDAR GATE 🚀", disabled=not pode_assinar)
            
            if btn:
                if not all(respostas.values()):
                    st.error(f"❌ BLOQUEIO: {msg_bloqueio}")
                else:
                    # 1. Registra o checklist na aba específica
                    df_gate = conn.read(worksheet=aba, ttl=0)
                    nova_linha = {"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Pedido": pedido_sel, "Validado_Por": papel_usuario, "Obs": obs}
                    nova_linha.update(respostas)
                    updated_df = pd.concat([df_gate, pd.DataFrame([nova_linha])], ignore_index=True)
                    conn.update(worksheet=aba, data=updated_df)
                    
                    # 2. ATUALIZA O STATUS NA ABA DE RESUMO
                    atualizar_status_pedido(pedido_sel, proximo_status)
                    
                    st.success(f"🚀 Foguete decolou! Status atualizado para: {proximo_status}")

# --- PÁGINAS ---
if menu == "🆕 Novo Pedido":
    st.header("Cadastrar Novo Pedido / Obra")
    with st.form("cadastro_pedido"):
        nome = st.text_input("Nome do Pedido")
        desc = st.text_area("Descrição")
        dono = st.selectbox("Dono do Pedido", ["Wilson", "Dono A", "Dono B"])
        if st.form_submit_button("Criar Ficha do Pedido"):
            df = conn.read(worksheet="Pedidos", ttl=0)
            novo = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Pedido": nome, "Descricao": desc, "Dono": dono, "Status_Atual": "Aguardando Gate 1"}])
            conn.update(worksheet="Pedidos", data=pd.concat([df, novo], ignore_index=True))
            st.success(f"Pedido {nome} cadastrado!")

elif menu == "✅ Gate 1: Aceite Técnico":
    itens = {"🔹 Info": ["Pedido registrado", "Cliente identificado", "Tipo de obra", "Responsável id"], "🔹 Escopo": ["Projeto mínimo", "Ambientes", "Materiais", "Itens fora padrão"], "🔹 Prazo/Gov": ["Prazo comercial", "Avaliação técnica", "Risco identificado", "Dono definido", "Viabilidade PCP", "Aprovado formalmente"]}
    checklist_gate("GATE 1", "Checklist_G1", itens, "Dono do Pedido (DP)", "PCP", "Projeto incompleto ou prazo inviável.", "Aguardando Gate 2")

elif menu == "🏭 Gate 2: Produção":
    itens = {"🔹 Planejamento": ["Pedido sequenciado", "Capacidade validada", "Gargalo identificado", "Gargalo protegido"], "🔹 Projeto/Comunicação": ["Projeto técnico", "Medidas conferidas", "Versão registrada", "Produção ciente", "Prazo interno", "Alterações registradas"]}
    checklist_gate("GATE 2", "Checklist_G2", itens, "PCP", "Produção", "Pedido fora da sequência ou sem liberação.", "Aguardando Gate 3")

elif menu == "💰 Gate 3: Material":
    itens = {"🔹 Materiais/Compras": ["Lista validada", "Quantidades", "Especiais", "Fornecedores", "Lead times", "Entregas"], "🔹 Financeiro": ["Impacto caixa", "Autorização formal", "Pagamento definido"]}
    checklist_gate("GATE 3", "Checklist_G3", itens, "Financeiro", "Compras", "Material não comprado ou sem aval financeiro.", "Aguardando Gate 4")

elif menu == "🚛 Gate 4: Entrega":
    itens = {"🔹 Produto/Logística": ["Produção concluída", "Qualidade", "Itens separados", "Checklist carga", "Frota", "Rota", "Data logística", "Cliente informado", "Equipe alinhada"]}
    checklist_gate("GATE 4", "Checklist_G4", itens, "Dono do Pedido (DP)", "Logística", "Produto incompleto ou prazo não validado.", "Concluído")

elif menu == "📊 Resumo Geral":
    st.header("Acompanhamento de Pedidos")
    df_p = conn.read(worksheet="Pedidos", ttl=0)
    st.dataframe(df_p, use_container_width=True)
