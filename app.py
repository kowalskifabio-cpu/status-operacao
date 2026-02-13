import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Status Marcenaria - Operacional", layout="wide", page_icon="🏭")

# Estilização Status
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { color: #634D3E !important; }
    .stButton>button { background-color: #634D3E; color: white; width: 100%; }
    .stExpander { border: 1px solid #B59572; }
    </style>
    """, unsafe_allow_html=True)

# Conexão
conn = st.connection("gsheets", type=GSheetsConnection)

# Menu Lateral
menu = st.sidebar.selectbox("Menu Principal", 
    ["🆕 Cadastrar Pedido", "✅ Gate 1: Aceite Técnico", "🏭 Gate 2: Produção", "💰 Gate 3: Material", "🚛 Gate 4: Entrega", "📊 Painel de Controle"])

# --- 1. CADASTRO INICIAL ---
if menu == "🆕 Cadastrar Pedido":
    st.header("Novo Pedido / Obra")
    with st.form("cadastro_pedido"):
        nome_pedido = st.text_input("Nome do Pedido / Cliente")
        descricao = st.text_area("Breve Descrição do Escopo")
        dono = st.selectbox("Dono do Pedido (Responsável)", ["Wilson", "Responsável A", "Responsável B"])
        submit = st.form_submit_button("Criar Ficha do Pedido")
        
        if submit and nome_pedido:
            df_pedidos = conn.read(worksheet="Pedidos", ttl=0)
            novo_p = pd.DataFrame([{"Data": datetime.now(), "Pedido": nome_pedido, "Descricao": descricao, "Dono": dono, "Status": "Aguardando G1"}])
            updated = pd.concat([df_pedidos, novo_p], ignore_index=True)
            conn.update(worksheet="Pedidos", data=updated)
            st.success("Pedido criado! Vá para o Gate 1 para validar.")

# --- FUNÇÃO PARA GERAR FORMULÁRIO DE GATE ---
def gerar_formulario_gate(gate_nome, aba, checklist_itens, criterios_bloqueio):
    st.header(f"Ficha de Checklist - {gate_nome}")
    
    # Busca pedidos cadastrados
    pedidos_df = conn.read(worksheet="Pedidos", ttl=0)
    lista_pedidos = pedidos_df["Pedido"].tolist()
    
    pedido_sel = st.selectbox("Selecione o Pedido", lista_pedidos)
    
    st.info(f"**Responsável:** {gate_nome}")
    
    with st.form(f"form_{aba}"):
        respostas = {}
        st.subheader("Checklist Obrigatório")
        
        # Renderiza os itens do checklist (conforme imagens enviadas)
        for secao, itens in checklist_itens.items():
            st.markdown(f"**🔹 {secao}**")
            for item in itens:
                respostas[item] = st.checkbox(item)
        
        obs = st.text_area("Observações Técnicas")
        confirmar = st.form_submit_button("Registrar Validação")
        
        if confirmar:
            # Verifica critério de bloqueio
            if not all(respostas.values()):
                st.error(f"❌ **BLOQUEIO:** {criterios_bloqueio}")
            else:
                df_gate = conn.read(worksheet=aba, ttl=0)
                dados = {"Data": datetime.now(), "Pedido": pedido_sel, "Validador": "Sistema"}
                dados.update(respostas)
                dados["Observacoes"] = obs
                
                updated = pd.concat([df_gate, pd.DataFrame([dados])], ignore_index=True)
                conn.update(worksheet=aba, data=updated)
                st.success(f"🚀 Foguete decolou! {gate_nome} validado.")

# --- MENUS DE GATES (DADOS DAS IMAGENS) ---
if menu == "✅ Gate 1: Aceite Técnico":
    itens = {
        "Informações Comerciais": ["Pedido registrado", "Cliente identificado", "Tipo de obra definido", "Responsável identificado"],
        "Escopo Técnico": ["Projeto mínimo recebido", "Ambientes definidos", "Materiais principais definidos", "Itens fora do padrão identificados"],
        "Prazo (prévia)": ["Prazo solicitado registrado", "Prazo avaliado tecnicamente", "Risco de prazo identificado"],
        "Governança": ["Dono do Pedido definido", "PCP validou viabilidade", "Pedido aprovado formalmente"]
    }
    gerar_formulario_gate("Gate 1", "Checklist_G1", itens, "Projeto incompleto, Dono indefinido ou Prazo inviável.")

elif menu == "🏭 Gate 2: Produção":
    itens = {
        "Planejamento": ["Pedido sequenciado", "Capacidade validada", "Gargalo identificado", "Gargalo protegido no plano"],
        "Projeto": ["Projeto técnico liberado", "Medidas conferidas", "Versão do projeto registrada"],
        "Comunicação": ["Produção ciente do plano", "Prazo interno registrado", "Alterações registradas"]
    }
    gerar_formulario_gate("Gate 2", "Checklist_G2", itens, "Pedido fora da sequência, Gargalo saturado ou sem liberação formal.")

elif menu == "💰 Gate 3: Material":
    itens = {
        "Materiais": ["Lista de materiais validada", "Quantidades conferidas", "Materiais especiais identificados"],
        "Compras": ["Fornecedores definidos", "Lead times confirmados", "Datas de entrega registradas"],
        "Financeiro": ["Impacto no caixa validado", "Compra autorizada formalmente", "Forma de pagamento definida"]
    }
    gerar_formulario_gate("Gate 3", "Checklist_G3", itens, "Material crítico não comprado ou impacto financeiro não aprovado.")

elif menu == "🚛 Gate 4: Entrega":
    itens = {
        "Produto": ["Produção concluída", "Qualidade conferida", "Itens separados por pedido"],
        "Logística": ["Checklist de carga preenchido", "Frota definida", "Rota planejada"],
        "Prazo": ["Data validada com logística", "Cliente informado", "Equipe de montagem alinhada"]
    }
    gerar_formulario_gate("Gate 4", "Checklist_G4", itens, "Produto incompleto, falta de frota ou prazo não validado.")

elif menu == "📊 Painel de Controle":
    st.header("Status Geral dos Pedidos")
    df_p = conn.read(worksheet="Pedidos", ttl=0)
    st.dataframe(df_p, use_container_width=True)
