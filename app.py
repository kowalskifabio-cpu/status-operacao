import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Status - Lançamento de Gates", page_icon="🚀")

# Design Simples e Ágil
st.title("🚀 Lançamento de Gates")
st.write("Registro oficial de movimentação de pedidos.")

# Conexão com a Planilha
conn = st.connection("gsheets", type=GSheetsConnection)

# Formulário de Lançamento Rápido
with st.form(key="gate_form", clear_on_submit=True):
    pedido = st.text_input("Nome/Número do Pedido")
    gate = st.selectbox("Selecione o Gate", ["Gate 1 - Aceite", "Gate 2 - Produção", "Gate 3 - Material", "Gate 4 - Logística"])
    responsavel = st.selectbox("Quem está validando?", ["Wilson", "Dono do Pedido A", "Dono do Pedido B"])
    obs = st.text_area("Observações (Opcional)")
    
    submit = st.form_submit_button("Registrar Lançamento")

if submit:
    if pedido:
        # Preparar dados
        novo_registro = pd.DataFrame([{
            "Data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "Pedido": pedido,
            "Gate": gate,
            "Responsavel": responsavel,
            "Observacoes": obs
        }])
        
        # Adicionar à planilha existente
        existing_data = conn.read(worksheet="Lancamentos")
        updated_df = pd.concat([existing_data, novo_registro], ignore_index=True)
        conn.update(worksheet="Lancamentos", data=updated_df)
        
        st.success(f"Lançamento do {gate} para o pedido {pedido} realizado!")
        st.balloons()
    else:
        st.error("O campo 'Pedido' é obrigatório.")
