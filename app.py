import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Status - Gestão de Gates", layout="centered")

st.title("🚀 Sistema de Gestão de Gates")
st.write("Registro oficial de movimentação de pedidos.")

# 1. Inicia a conexão segura (buscando os dados que você colou nos Secrets)
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
            # Lê o que já existe na planilha (trabalhando na aba "Lancamentos")
            # Se a aba tiver outro nome, ajuste aqui
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
            
            # Salva de volta no Google Sheets
            conn.update(worksheet="Lancamentos", data=df_final)
            
            st.success(f"✅ Sucesso! {gate} registrado para {pedido}.")
            st.balloons()
            
        except Exception as e:
            st.error(f"Erro ao salvar na planilha: {e}")
            st.info("Dica: Verifique se você compartilhou a planilha com o e-mail da Service Account como 'Editor'.")
    else:
        st.error("Por favor, preencha o nome do pedido.")

# 4. Histórico para visualização rápida
st.markdown("---")
st.subheader("📋 Histórico Recente")
try:
    df_vis = conn.read(worksheet="Lancamentos", ttl=0)
    st.dataframe(df_vis.tail(10), use_container_width=True)
except:
    st.write("Conectado. Aguardando o primeiro registro para exibir o histórico.")
