import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import os

# Configuração da Página
st.set_page_config(page_title="Status - Gestão Integral de Gates", layout="wide", page_icon="🏗️")

# Estilização Status
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { color: #634D3E !important; }
    .stButton>button { background-color: #634D3E; color: white; border-radius: 5px; width: 100%; }
    .stInfo { background-color: #f0f2f6; border-left: 5px solid #B59572; }
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
    ["🆕 Novo Pedido", "👤 Gestores", "✅ Gate 1: Aceite Técnico", "🏭 Gate 2: Produção", "💰 Gate 3: Material", "🚛 Gate 4: Entrega", "📊 Resumo e Prazos", "🚨 Auditoria"])

# --- FUNÇÃO DE GESTÃO DE GATES (INTEGRAL) ---
def checklist_gate(gate_id, aba, itens_checklist, responsavel_r, executor_e, msg_bloqueio, proximo_status, objetivo, momento):
    st.header(f"Ficha de Controle: {gate_id}")
    st.markdown(f"**Objetivo:** {objetivo}")
    st.markdown(f"**Momento:** {momento}")
    st.info(f"⚖️ **Responsável (R):** {responsavel_r} | 🔨 **Executor (E):** {executor_e}")
    
    try:
        df_pedidos = conn.read(worksheet="Pedidos", ttl=0)
        pedido_sel = st.selectbox("Selecione o Pedido", [""] + df_pedidos["Pedido"].tolist())
    except:
        st.error("Erro ao ler aba Pedidos.")
        return

    if pedido_sel:
        pode_assinar = (papel_usuario == responsavel_r or papel_usuario == executor_e or papel_usuario == "Gerência Geral")
        
        if not pode_assinar:
            st.warning(f"⚠️ Acesso limitado: Apenas {responsavel_r} ou {executor_e} validam este Gate.")

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
                    st.error(f"❌ CRITÉRIOS DE BLOQUEIO: {msg_bloqueio}")
                else:
                    try:
                        df_gate = conn.read(worksheet=aba, ttl=0)
                        nova_linha = {"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Pedido": pedido_sel, "Validado_Por": papel_usuario, "Obs": obs}
                        nova_linha.update(respostas)
                        updated_df = pd.concat([df_gate, pd.DataFrame([nova_linha])], ignore_index=True)
                        conn.update(worksheet=aba, data=updated_df)
                        
                        atualizar_quadro_resumo(pedido_sel, proximo_status)
                        st.success(f"🚀 Sucesso! Pedido avançou para: {proximo_status}")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

# --- PÁGINAS ---

if menu == "🆕 Novo Pedido":
    st.header("Cadastrar Novo Pedido / Obra")
    
    # Busca lista de gestores dinâmica da planilha
    try:
        df_gestores = conn.read(worksheet="Gestores", ttl=0)
        lista_gestores = df_gestores["Nome"].tolist()
    except:
        lista_gestores = ["Cadastre um gestor primeiro"]

    with st.form("cadastro_pedido"):
        nome = st.text_input("Nome do Pedido")
        desc = st.text_area("Descrição")
        dono = st.selectbox("Dono do Pedido (Gestor)", lista_gestores)
        prazo = st.date_input("Data Prometida de Entrega", min_value=date.today())
        if st.form_submit_button("Criar Ficha do Pedido"):
            if nome and dono != "Cadastre um gestor primeiro":
                df = conn.read(worksheet="Pedidos", ttl=0)
                novo = pd.DataFrame([{"Data": date.today().strftime("%d/%m/%Y"), "Pedido": nome, "Descricao": desc, "Dono": dono, "Status_Atual": "Aguardando Gate 1", "Prazo_Entrega": prazo.strftime("%Y-%m-%d")}])
                conn.update(worksheet="Pedidos", data=pd.concat([df, novo], ignore_index=True))
                st.success(f"Pedido {nome} cadastrado!")
            else:
                st.error("Campos obrigatórios faltando.")

elif menu == "👤 Gestores":
    st.header("Gestão de Donos de Pedido (Gestores)")
    
    with st.form("cadastro_gestor"):
        novo_gestor = st.text_input("Nome do Novo Gestor")
        if st.form_submit_button("Adicionar Gestor"):
            if novo_gestor:
                df_g = conn.read(worksheet="Gestores", ttl=0)
                novo_g = pd.DataFrame([{"Nome": novo_gestor}])
                conn.update(worksheet="Gestores", data=pd.concat([df_g, novo_g], ignore_index=True))
                st.success(f"Gestor {novo_gestor} adicionado!")
            else:
                st.error("Digite o nome do gestor.")
    
    st.subheader("Gestores Cadastrados")
    try:
        df_list = conn.read(worksheet="Gestores", ttl=0)
        st.dataframe(df_list, use_container_width=True)
    except:
        st.write("Nenhum gestor cadastrado.")

elif menu == "✅ Gate 1: Aceite Técnico":
    itens = {
        "Informações Comerciais": ["Pedido registrado no sistema", "Cliente identificado", "Tipo de obra definido (residencial / corporativa / construtora)", "Responsável do cliente identificado"],
        "Escopo Técnico": ["Projeto mínimo recebido (plantas / medidas críticas)", "Ambientes definidos", "Materiais principais definidos (MDF, pintura, especiais)", "Itens fora do padrão identificados"],
        "Prazo (prévia)": ["Prazo solicitado pelo comercial registrado", "Prazo avaliado tecnicamente", "Risco de prazo identificado (se houver)"],
        "Governança": ["Dono do Pedido definido", "PCP validou viabilidade inicial", "Pedido aprovado formalmente"]
    }
    checklist_gate("GATE 1", "Checklist_G1", itens, "Dono do Pedido (DP)", "PCP", "Projeto incompleto, Dono do pedido indefinido, Prazo inviável sem ajuste. ➡️ Pedido BLOQUEADO até correção", "Aguardando Produção (G2)", "impedir entrada de pedido mal definido", "antes de qualquer planejamento ou promessa interna")

elif menu == "🏭 Gate 2: Produção":
    itens = {
        "Planejamento": ["Pedido sequenciado na programação", "Capacidade validada", "Gargalo identificado", "Gargalo protegido no plano"],
        "Projeto": ["Projeto técnico liberado", "Medidas conferidas", "Versão do projeto registrada"],
        "Comunicação": ["Produção ciente do plano", "Prazo interno registrado", "Alterações registradas (se houver)"]
    }
    checklist_gate("GATE 2", "Checklist_G2", itens, "PCP", "Produção", "Pedido fora da sequência, Gargalo saturado sem ajuste, Projeto sem liberação formal. ➡️ Produção NÃO inicia", "Aguardando Materiais (G3)", "garantir que a produção execute plano, não urgência", "antes de cortar material")

elif menu == "💰 Gate 3: Material":
    itens = {
        "Materiais": ["Lista de materiais validada", "Quantidades conferidas", "Materiais especiais identificados"],
        "Compras": ["Fornecedores definidos", "Lead times confirmados", "Datas de entrega registradas"],
        "Financeiro": ["Impacto no caixa validado", "Compra autorizada formalmente", "Forma de pagamento definida"]
    }
    checklist_gate("GATE 3", "Checklist_G3", itens, "Financeiro", "Compras", "Material crítico não comprado, Impacto financeiro não aprovado, Lead time incompatível. ➡️ Produção BLOQUEADA", "Aguardando Entrega (G4)", "eliminar produção sem material", "antes do início físico da produção")

elif menu == "🚛 Gate 4: Entrega":
    itens = {
        "Produto": ["Produção concluída", "Qualidade conferida", "Itens separados por pedido"],
        "Logística": ["Checklist de carga preenchido", "Frota definida", "Rota planejada"],
        "Prazo": ["Data validada com logística", "Cliente informado", "Equipe de montagem alinhada"]
    }
    checklist_gate("GATE 4", "Checklist_G4", itens, "Dono do Pedido (DP)", "Logística", "Produto incompleto, Falta de frota adequada, Prazo não validado. ➡️ Entrega NÃO autorizada", "CONCLUÍDO ✅", "garantir entrega sem retrabalho e improviso", "antes de prometer data ao cliente")

elif menu == "📊 Resumo e Prazos":
    st.header("🚦 Monitor de Pedidos e Prazos")
    try:
        df_p = conn.read(worksheet="Pedidos", ttl=0)
        df_p['Prazo_Entrega'] = pd.to_datetime(df_p['Prazo_Entrega'], errors='coerce')
        
        def calcular_dias(row):
            if pd.isnull(row['Prazo_Entrega']): return None
            delta = row['Prazo_Entrega'].date() - date.today()
            return delta.days

        df_p['Dias_Restantes'] = df_p.apply(calcular_dias, axis=1)
        
        def alerta_prazo(dias):
            if dias is None: return "⚪ SEM DATA"
            if dias < 0: return "❌ VENCIDO"
            if dias <= 3: return "🔴 CRÍTICO"
            if dias <= 7: return "🟡 ATENÇÃO"
            return "🟢 NO PRAZO"
        
        df_p['Alerta'] = df_p['Dias_Restantes'].apply(alerta_prazo)
        df_p['Prazo_Exibicao'] = df_p['Prazo_Entrega'].dt.strftime('%d/%m/%Y').fillna("Não Definido")
        st.dataframe(df_p[['Pedido', 'Dono', 'Status_Atual', 'Prazo_Exibicao', 'Dias_Restantes', 'Alerta']].sort_values(by='Dias_Restantes', na_position='last'), use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao processar resumo: {e}")

elif menu == "🚨 Auditoria":
    st.header("🚨 Auditoria de Governança")
    st.error("Qualquer exceção mata o ERCI!")
    st.write("- 'Só dessa vez libera'")
    st.write("- 'Depois a gente formaliza'")
    st.write("- 'É urgente'")
    st.write("- 'Sempre foi assim'")
