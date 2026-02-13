import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Status - Gestão de Gates", layout="centered")

# --- TRUQUE DE LIMPEZA DA CHAVE ---
# Isso remove quebras de linha invisíveis que causam o erro de PEM file
if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
    if "private_key" in st.secrets["connections"]["gsheets"]:
        # Garante que os \n sejam interpretados corretamente como quebras de linha
        st.secrets["connections"]["gsheets"]["private_key"] = st.secrets["connections"]["gsheets"]["private_key"].replace("\\n", "\n")

st.title("🚀 Sistema de Gestão de Gates")

# Inicia a conexão
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
            # Tenta ler a planilha
            df_existente = conn.read(worksheet="Lancamentos", ttl=0)
            
            novo_registro = pd.DataFrame([{
                "Data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "Pedido": pedido,
                "Gate": gate,
                "Responsavel": responsavel,
                "Observacoes": obs
            }])
            
            df_final = pd.concat([df_existente, novo_registro], ignore_index=True)
            
            # Tenta salvar
            conn.update(worksheet="Lancamentos", data=df_final)
            st.success("✅ Registrado com sucesso!")
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
    st.write("Conectado! Aguardando o primeiro registro...")
