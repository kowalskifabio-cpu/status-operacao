import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Status - Gestão Operacional", layout="wide", page_icon="🏗️")

# --- ESTILIZAÇÃO STATUS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { color: #634D3E !important; }
    .stButton>button { background-color: #634D3E; color: white; border-radius: 5px; }
    .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# Conexão com Planilha
conn = st.connection("gsheets", type=GSheetsConnection)

# --- MENU LATERAL ---
st.sidebar.image("Status Apresentação.png", use_container_width=True)
st.sidebar.title("GOVERNANÇA STATUS")

# Identificação de Papel (ERCI)
papel_usuario = st.sidebar.selectbox("Seu Papel Hoje:", 
    ["PCP", "Dono do Pedido (DP)", "Produção", "Compras", "Financeiro", "Logística", "Gerência Geral"])

menu = st.sidebar.radio("Navegação", 
    ["🆕 Cadastrar Novo Pedido", "✅ Gate 1: Aceite Técnico", "🏭 Gate 2: Produção", "💰 Gate 3: Material", "🚛 Gate 4: Entrega", "📊 Resumo da Governança"])

# --- FUNÇÃO DE APOIO: REGISTRO DE GATES ---
def checklist_gate(gate_id, aba, itens_checklist, responsavel_r, executor_e, msg_bloqueio):
    st.header(f"Ficha de Controle: {gate_id}")
    st.info(f"⚖️ **Responsável (R):** {responsavel_r} | 🔨 **Executor (E):** {executor_e}")
    
    # Carrega pedidos existentes
    try:
        df_pedidos = conn.read(worksheet="Pedidos", ttl=0)
        lista_pedidos = df_pedidos["Pedido"].tolist()
        pedido_sel = st.selectbox("Selecione o Pedido", [""] + lista_pedidos)
    except:
        st.error("Nenhum pedido encontrado. Cadastre um pedido primeiro.")
        return

    if pedido_sel:
        # Verifica se o papel do usuário pode assinar este Gate
        pode_assinar = (papel_usuario == responsavel_r or papel_usuario == executor_e or papel_usuario == "Gerência Geral")
        
        if not pode_assinar:
            st.warning(f"⚠️ Apenas {responsavel_r} ou {executor_e} podem validar este Gate.")

        with st.form(f"form_{aba}"):
            st.subheader("Checklist Obrigatório")
            respostas = {}
            
            # Monta o checklist baseado nas seções das imagens
            for secao, itens in itens_checklist.items():
                st.markdown(f"**{secao}**")
                for item in itens:
                    respostas[item] = st.checkbox(item)
            
            obs = st.text_area("Observações Técnicas")
            btn_salvar = st.form_submit_button("VALIDAR GATE 🚀", disabled=not pode_assinar)
            
            if btn_salvar:
                if not all(respostas.values()):
                    st.error(f"❌ BLOQUEIO: {msg_bloqueio}")
                else:
                    try:
                        df_existente = conn.read(worksheet=aba, ttl=0)
                        nova_linha = {"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Pedido": pedido_sel, "Validado_Por": papel_usuario, "Obs": obs}
                        nova_linha.update(respostas)
                        df_final = pd.concat([df_existente, pd.DataFrame([nova_linha])], ignore_index=True)
                        conn.update(worksheet=aba, data=df_final)
                        st.success(f"Foguete decolou! {gate_id} validado para o pedido {pedido_sel}.")
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

# --- PÁGINAS DO MENU ---

if menu == "🆕 Cadastrar Novo Pedido":
    st.header("Cadastrar Novo Pedido / Obra")
    with st.form("cadastro_pedido"):
        nome = st.text_input("Nome/Número do Pedido")
        desc = st.text_area("Descrição do Escopo")
        dono = st.selectbox("Dono do Pedido (Responsável)", ["Wilson", "Responsável A", "Responsável B"])
        if st.form_submit_button("Criar Ficha do Pedido"):
            if nome:
                df = conn.read(worksheet="Pedidos", ttl=0)
                novo = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Pedido": nome, "Descricao": desc, "Dono": dono, "Status_Atual": "Gate 1"}])
                conn.update(worksheet="Pedidos", data=pd.concat([df, novo], ignore_index=True))
                st.success(f"Pedido {nome} cadastrado com sucesso!")
            else:
                st.error("O nome do pedido é obrigatório.")

elif menu == "✅ Gate 1: Aceite Técnico":
    # Itens extraídos da imagem d82120.png
    itens = {
        "🔹 Informações Comerciais": ["Pedido registrado", "Cliente identificado", "Tipo de obra definido", "Responsável do cliente id"],
        "🔹 Escopo Técnico": ["Projeto mínimo recebido", "Ambientes definidos", "Materiais definidos", "Itens fora do padrão id"],
        "🔹 Prazo (prévia)": ["Prazo comercial registrado", "Prazo avaliado tecnicamente", "Risco de prazo identificado"],
        "🔹 Governança": ["Dono do Pedido definido", "PCP validou viabilidade", "Pedido aprovado formalmente"]
    }
    checklist_gate("GATE 1", "Checklist_G1", itens, "Dono do Pedido (DP)", "PCP", "Projeto incompleto, Dono indefinido ou Prazo inviável.")

elif menu == "🏭 Gate 2: Produção":
    # Itens extraídos da imagem d8208a.png
    itens = {
        "🔹 Planejamento": ["Pedido sequenciado", "Capacidade validada", "Gargalo identificado", "Gargalo protegido"],
        "🔹 Projeto": ["Projeto técnico liberado", "Medidas conferidas", "Versão registrada"],
        "🔹 Comunicação": ["Produção ciente do plano", "Prazo interno registrado", "Alterações registradas"]
    }
    checklist_gate("GATE 2", "Checklist_G2", itens, "PCP", "Produção", "Pedido fora da sequência ou sem liberação formal.")

elif menu == "💰 Gate 3: Material":
    # Itens extraídos da imagem d82406.png
    itens = {
        "🔹 Materiais": ["Lista validada", "Quantidades conferidas", "Especiais identificados"],
        "🔹 Compras": ["Fornecedores definidos", "Lead times confirmados", "Entregas registradas"],
        "🔹 Financeiro": ["Impacto no caixa validado", "Compra autorizada formalmente", "Pagamento definido"]
    }
    checklist_gate("GATE 3", "Checklist_G3", itens, "Financeiro", "Compras", "Material crítico não comprado ou sem aval financeiro.")

elif menu == "🚛 Gate 4: Entrega":
    # Itens extraídos da imagem d82463.png
    itens = {
        "🔹 Produto": ["Produção concluída", "Qualidade conferida", "Itens separados"],
        "🔹 Logística": ["Checklist de carga preenchido", "Frota definida", "Rota planejada"],
        "🔹 Prazo": ["Data validada com logística", "Cliente informado", "Equipe alinhada"]
    }
    checklist_gate("GATE 4", "Checklist_G4", itens, "Dono do Pedido (DP)", "Logística", "Produto incompleto ou prazo não validado.")

elif menu == "📊 Resumo da Governança":
    st.header("Painel de Controle de Pedidos")
    try:
        df_p = conn.read(worksheet="Pedidos", ttl=0)
        st.dataframe(df_p, use_container_width=True)
    except:
        st.write("Aguardando dados...")
