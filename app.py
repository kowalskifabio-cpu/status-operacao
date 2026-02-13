import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import os
import time

# Configuração da Página
st.set_page_config(page_title="Status - Gestão Integral de Gates", layout="wide", page_icon="🏗️")

# --- FUNÇÃO DE AUTO-REFRESH (5 MINUTOS) ---
# Adiciona um timer invisível para recarregar a página e os dados da planilha
# Essencial para o monitor fixo na fábrica
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

refresh_interval = 300 # 5 minutos em segundos
if time.time() - st.session_state.last_refresh > refresh_interval:
    st.session_state.last_refresh = time.time()
    st.rerun()

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

# ORDENAÇÃO MANTIDA CONFORME SOLICITADO
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

# --- FUNÇÃO DE GESTÃO DE GATES (INTEGRAL COM TRAVA DE RE-APROVAÇÃO) ---
def checklist_gate(gate_id, aba, itens_checklist, responsavel_r, executor_e, msg_bloqueio, proximo_status, objetivo, momento):
    st.header(f"Ficha de Controle: {gate_id}")
    st.markdown(f"**Objetivo:** {objetivo}")
    st.markdown(f"**Momento:** {momento}")
    st.info(f"⚖️ **Responsável (R):** {responsavel_r} | 🔨 **Executor (E):** {executor_e}")
    
    try:
        df_pedidos = conn.read(worksheet="Pedidos", ttl=0)
        pedido_sel = st.selectbox(f"Selecione o Pedido para {gate_id}", [""] + df_pedidos["Pedido"].tolist(), key=f"sel_{aba}")
        
        if pedido_sel:
            status_atual = df_pedidos.loc[df_pedidos['Pedido'] == pedido_sel, 'Status_Atual'].values[0]
            
            concluido = False
            if gate_id == "GATE 1" and status_atual != "Aguardando Gate 1": concluido = True
            elif gate_id == "GATE 2" and status_atual not in ["Aguardando Gate 1", "Aguardando Produção (G2)"]: concluido = True
            elif gate_id == "GATE 3" and status_atual not in ["Aguardando Gate 1", "Aguardando Produção (G2)", "Aguardando Materiais (G3)"]: concluido = True
            elif gate_id == "GATE 4" and status_atual == "CONCLUÍDO ✅": concluido = True

            if concluido:
                st.warning(f"✅ Este Gate já foi aprovado anteriormente. O status atual do pedido é: **{status_atual}**.")
                if papel_usuario != "Gerência Geral":
                    st.info("Somente a Gerência Geral pode re-validar gates concluídos.")
                    return
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

if menu == "📊 Resumo e Prazos":
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
        st.dataframe(df_p[['Pedido', 'CTR', 'Dono', 'Status_Atual', 'Dias_Restantes', 'Alerta']].sort_values(by='Dias_Restantes', na_position='last'), use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao processar resumo: {e}")

elif menu == "🚨 Auditoria":
    st.header("🚨 Auditoria e Histórico de Alterações")
    st.error("Qualquer exceção mata o ERCI!")
    st.subheader("Registros de Mini-Gates (Mudanças de Escopo)")
    try:
        df_aud = conn.read(worksheet="Alteracoes", ttl=0)
        colunas_exibicao = ['Data', 'Pedido', 'CTR', 'Usuario', 'O que mudou', 'Impacto no Prazo', 'Impacto Financeiro']
        colunas_reais = [col for col in colunas_exibicao if col in df_aud.columns]
        st.dataframe(df_aud[colunas_reais], use_container_width=True)
    except:
        st.write("Sem registros de alteração.")
    st.markdown("---")
    st.markdown("#### Regras de Burla (Alerta):")
    st.write("- 'Só dessa vez libera' | - 'É urgente' | - 'Sempre foi assim'")

elif menu == "👤 Cadastro de Gestores":
    st.header("Cadastro de Gestores (Donos de Pedido)")
    with st.form("form_gestores"):
        novo_nome = st.text_input("Nome Completo do Gestor")
        if st.form_submit_button("Salvar Gestor"):
            if novo_nome:
                df_g = conn.read(worksheet="Gestores", ttl=0)
                conn.update(worksheet="Gestores", data=pd.concat([df_g, pd.DataFrame([{"Nome": novo_nome}])], ignore_index=True))
                st.success(f"Gestor {novo_nome} cadastrado!")
    try:
        df_l = conn.read(worksheet="Gestores", ttl=0)
        st.table(df_l)
    except:
        st.write("Nenhum gestor encontrado.")

elif menu == "🆕 Novo Pedido":
    st.header("Cadastrar Novo Pedido / Obra")
    try:
        df_gestores = conn.read(worksheet="Gestores", ttl=0)
        lista_gestores = df_gestores["Nome"].tolist()
    except:
        lista_gestores = []
    
    with st.form("cadastro_pedido"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome do Pedido / Cliente")
            ctr = st.text_input("CTR (Número do Contrato/Projeto)")
        with col2:
            gestor_responsavel = st.selectbox("Selecione o Gestor Responsável", lista_gestores)
            prazo = st.date_input("Data Prometida de Entrega", min_value=date.today())
        desc = st.text_area("Descrição")
        
        if st.form_submit_button("Criar Ficha do Pedido"):
            if nome and ctr and gestor_responsavel:
                df = conn.read(worksheet="Pedidos", ttl=0)
                if ctr in df['CTR'].astype(str).values:
                    st.error(f"❌ Erro: O CTR {ctr} já está cadastrado no sistema. Use um número único.")
                else:
                    novo = pd.DataFrame([{
                        "Data": date.today().strftime("%d/%m/%Y"), 
                        "Pedido": nome, 
                        "CTR": ctr,
                        "Descricao": desc, 
                        "Dono": gestor_responsavel, 
                        "Status_Atual": "Aguardando Gate 1", 
                        "Prazo_Entrega": prazo.strftime("%Y-%m-%d")
                    }])
                    conn.update(worksheet="Pedidos", data=pd.concat([df, novo], ignore_index=True))
                    st.success(f"Pedido {nome} (CTR: {ctr}) cadastrado com sucesso!")
            else:
                st.error("Preencha Nome, CTR e selecione um Gestor.")

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

elif menu == "⚠️ Alteração de Pedido":
    st.header("🔄 Registro de Alteração de Escopo (Mini-Gate)")
    st.warning("Mudança de projeto = novo mini-gate. Mudança sem registro não existe.")
    try:
        df_p = conn.read(worksheet="Pedidos", ttl=0)
        pedido_alt = st.selectbox("Selecione o Pedido para Alteração", [""] + df_p["Pedido"].tolist())
        if pedido_alt:
            ctr_vinculada = df_p.loc[df_p['Pedido'] == pedido_alt, 'CTR'].values[0]
            
            with st.form("form_alteracao"):
                st.info(f"📍 Pedido selecionado: {pedido_alt} | CTR: {ctr_vinculada}")
                mudanca = st.text_area("O que mudou no projeto/pedido?")
                impacto_f = st.selectbox("Impacto Financeiro?", ["Nenhum", "Acréscimo de Valor", "Desconto / Estorno"])
                impacto_p = st.selectbox("Impacto no Prazo?", ["Mantido", "Prorrogado", "Antecipado"])
                
                if st.form_submit_button("Registrar Alteração Oficial"):
                    if mudanca:
                        df_alt = conn.read(worksheet="Alteracoes", ttl=0)
                        nova_alt = pd.DataFrame([{
                            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), 
                            "Pedido": pedido_alt, 
                            "CTR": ctr_vinculada,
                            "Usuario": papel_usuario, 
                            "O que mudou": mudanca, 
                            "Impacto no Prazo": impacto_p, 
                            "Impacto Financeiro": impacto_f
                        }])
                        conn.update(worksheet="Alteracoes", data=pd.concat([df_alt, nova_alt], ignore_index=True))
                        st.success("Alteração registrada no histórico de Auditoria!")
                    else:
                        st.error("Descreva a mudança.")
    except: st.error("Erro ao carregar pedidos.")
