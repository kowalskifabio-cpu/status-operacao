import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Status - Lançamento de Gates", layout="centered")

st.title("🚀 Lançamento de Gates")
st.write("Registro oficial de movimentação de pedidos.")

# 1. Cria a conexão com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Cria o formulário
with st.form(key="gate_form", clear_on_submit=True):
    pedido = st.text_input("Nome/Número do Pedido")
    gate = st.selectbox("Selecione o Gate", ["Gate 1 - Aceite", "Gate 2 - Produção", "Gate 3 - Material", "Gate 4 - Logística"])
    responsavel = st.selectbox("Quem está validando?", ["Wilson", "Dono do Pedido A", "Dono do Pedido B"])
    obs = st.text_area("Observações (Opcional)")
    
    submit = st.form_submit_button("Registrar Lançamento")

# 3. O que acontece quando clica no botão
if submit:
    if pedido:
        # Lê o que já tem na planilha
        df_existente = conn.read(ttl=0) # ttl=0 força ele a ler os dados novos sempre
        
        # Cria a linha nova
        novo_registro = pd.DataFrame([{
            "Data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "Pedido": pedido,
            "Gate": gate,
            "Responsavel": responsavel,
            "Observacoes": obs
        }])
        
        # Junta o novo com o antigo
        df_final = pd.concat([df_existente, novo_registro], ignore_index=True)
        
        # Manda tudo de volta para o Google Sheets
        conn.update(data=df_final)
        
        st.success(f"✅ Registrado com sucesso!")
        st.balloons()
    else:
        st.error("Por favor, digite o nome do pedido.")

# 4. Mostra os últimos lançamentos logo abaixo (para conferência rápida)
st.markdown("---")
st.subheader("📋 Últimos Lançamentos")
df_visualizar = conn.read(ttl=0)
st.dataframe(df_visualizar.tail(5)) # Mostra só as últimas 5 linhas
