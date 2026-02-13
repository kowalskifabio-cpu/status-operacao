import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# Configuração da página
st.set_page_config(page_title="Status - Gestão de Gates", layout="centered", page_icon="🚀")

st.title("🚀 Sistema de Gestão de Gates")
st.write("Registro oficial de movimentação de pedidos.")

# 1. Inicia a conexão segura
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Erro na conexão com os Secrets: {e}")

# 2. Formulário de Entrada
with st.form(key="gate_form", clear_on_submit=True):
    pedido = st.text_input("Nome/Número do Pedido")
    gate = st.selectbox("Selecione o Gate", ["Gate 1 - Aceite", "Gate 2 - Produção", "Gate 3 - Material", "Gate 4 - Logística"])
    responsavel = st.selectbox("Quem está validando?", ["Wilson", "Dono do Pedido A", "Dono do Pedido B"])
    obs = st.text_area("Observações")
    
    submit = st.form_submit_button("Registrar Lançamento")

# 3. Processamento do Lançamento
if submit:
    if pedido:
        try:
            # Lógica de Decolagem do Foguete (Animação visual)
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for percent_complete in range(100):
                time.sleep(0.01)
                progress_bar.progress(percent_complete + 1)
                if percent_complete < 30:
                    status_text.text("🚀 Preparando motores...")
                elif percent_complete < 60:
                    status_text.text("🔥 Ignição...")
                else:
                    status_text.text("✨ Decolando!")
            
            # Limpa animação
            progress_bar.empty()
            status_text.empty()

            # Lê os dados
            df_existente = conn.read(worksheet="Lancamentos", ttl=0)
            
            # Cria a linha nova
            novo_registro = pd.DataFrame([{
                "Data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "Pedido": pedido,
                "Gate": gate,
                "Responsavel": responsavel,
                "Observacoes": obs
            }])
            
            # Junta os dados
            df_final = pd.concat([df_existente, novo_registro], ignore_index=True)
            
            # Salva no Google Sheets
            conn.update(worksheet="Lancamentos", data=df_final)
            
            st.success(f"🚀 {gate} do pedido {pedido} LANÇADO com sucesso!")
            st.toast("Foguete decolou!", icon="🚀")
            
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
    else:
        st.error("Por favor, preencha o nome do pedido.")

# 4. Histórico para visualização rápida
st.markdown("---")
st.subheader("📋 Histórico Recente")
try:
    df_vis = conn.read(worksheet="Lancamentos", ttl=0)
    # Mostra os 10 mais recentes, invertendo a ordem para o último aparecer no topo
    st.dataframe(df_vis.iloc[::-1].head(10), use_container_width=True)
except:
    st.write("Conectado. Aguardando o primeiro registro...")
