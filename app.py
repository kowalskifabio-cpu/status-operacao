import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Status - Gestão de Gates", layout="centered")

st.title("🚀 Sistema de Gestão de Gates")

# Inicia a conexão segura
conn = st.connection("gsheets", type=GSheetsConnection)

with st.form(key="gate_form", clear_on_submit=True):
    pedido = st.text_input("Nome/Número do Pedido")
    gate = st.selectbox("Selecione o Gate", ["Gate 1 - Aceite", "Gate 2 - Produção", "Gate 3 - Material", "Gate 4 - Logística"])
    responsavel = st.selectbox("Quem está validando?", ["Wilson", "Dono do Pedido A", "Dono do Pedido B"])
    obs = st.text_area("Observações")
    
    submit = st.form_submit_button("Registrar Lançamento")

if submit:
    if pedido:
        try:
            # Lê dados sem cache (ttl=0) para ser instantâneo
            df_existente = conn.read(worksheet="Lancamentos", ttl=0)
            
            novo_registro = pd.DataFrame([{
                "Data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "Pedido": pedido,
                "Gate": gate,
                "Responsavel": responsavel,
                "Observacoes": obs
            }])
            
            df_final = pd.concat([df_existente, novo_registro], ignore_index=True)
            
            # Atualiza a planilha
            conn.update(worksheet="Lancamentos", data=df_final)
            
            st.success(f"✅ Registrado com sucesso!")
            st.balloons()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
    else:
        st.error("Digite o nome do pedido.")

st.markdown("---")
st.subheader("📋 Histórico Recente")
try:
    df_vis = conn.read(worksheet="Lancamentos", ttl=0)
    st.dataframe(df_vis.tail(10), use_container_width=True)
except:
    st.write("Aguardando o primeiro registro...")
