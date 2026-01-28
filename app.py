import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# LINKS REAIS
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1btSAJK1M71CTGrtOVnEV4EHmEaF9NGR6nMvpGI6qHt0/edit?usp=sharing"
URL_TUTORIAL = "https://docs.google.com/document/d/1AFeJ16hdow2g1Di1OthFcUPZV6qkDiefKyIbe8v_mCM/edit?usp=sharing"

st.set_page_config(page_title="Distribuidor GAB PRE/GO", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        m = conn.read(spreadsheet=URL_PLANILHA, worksheet="marcadores")
        e = conn.read(spreadsheet=URL_PLANILHA, worksheet="equipe")
        h = conn.read(spreadsheet=URL_PLANILHA, worksheet="distribuicoes")
        return m, e, h
    except:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_m, df_e, df_h = carregar_dados()

st.title("⚖️ Distribuidor GAB PRE/GO")

with st.container(border=True):
    num_proc = st.text_input("Número do Processo")
    lista_m = df_m['Nome'].tolist() if not df_m.empty else []
    marc_sel = st.selectbox("Marcador", options=["Selecione..."] + lista_m)
    
    if st.button("🚀 Distribuir", type="primary"):
        if num_proc and marc_sel != "Selecione...":
            # Lógica simples de sorteio
            ganhador = df_e.sample(1).iloc[0]['Nome'] if not df_e.empty else "Ninguém"
            
            nova_linha = pd.DataFrame({
                "Data": [datetime.now().strftime("%d/%m/%Y %H:%M")],
                "Processos": [num_proc],
                "Assessor": [ganhador],
                "Peso_Total": [1.0], # Simplificado para o teste
                "Tipo": ["Normal"]
            })
            
            df_atualizado = pd.concat([df_h, nova_linha], ignore_index=True)
            conn.update(spreadsheet=URL_PLANILHA, worksheet="distribuicoes", data=df_atualizado)
            st.success(f"Distribuído para {ganhador}!")
            st.balloons()