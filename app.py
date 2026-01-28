import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# LINKS REAIS DO CRISTIANO
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1btSAJK1M71CTGrtOVnEV4EHmEaF9NGR6nMvpGI6qHt0/edit?usp=sharing"
URL_TUTORIAL = "https://docs.google.com/document/d/1AFeJ16hdow2g1Di1OthFcUPZV6qkDiefKyIbe8v_mCM/edit?usp=sharing"

st.set_page_config(page_title="Distribuidor GAB PRE/GO", layout="wide", page_icon="⚖️")

# Conectando ao Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÕES DE DADOS ---
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        m = conn.read(spreadsheet=URL_PLANILHA, worksheet="marcadores")
        e = conn.read(spreadsheet=URL_PLANILHA, worksheet="equipe")
        h = conn.read(spreadsheet=URL_PLANILHA, worksheet="distribuicoes")
        return m, e, h
    except:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- LÓGICA DE SORTEIO (MENOR CARGA) ---
def sortear_assessor(df_equipe, df_hist):
    if df_equipe.empty: return "Erro: Equipe Vazia"
    if df_hist.empty: return df_equipe.iloc[0]['Nome']
    
    cargas = df_hist.groupby('Assessor')['Peso_Total'].sum()
    lista_equipe = df_equipe['Nome'].tolist()
    ranking = {nome: cargas.get(nome, 0.0) for nome in lista_equipe}
    return min(ranking, key=ranking.get)

# --- INTERFACE ---
df_m, df_e, df_h = carregar_dados()

st.title("⚖️ Sistema de Distribuição - GAB PRE/GO")

# Barra Lateral
with st.sidebar:
    st.header("Configurações")
    triador = st.selectbox("Triador da Semana", options=df_e['Nome'].tolist() if not df_e.empty else ["Vazio"])
    if st.button("🔄 Atualizar Planilha"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.link_button("❓ Manual de Instruções", URL_TUTORIAL)

# Área Principal
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        num_proc = st.text_input("Número do(s) Processo(s)", placeholder="Cole aqui...")
    with col2:
        lista_m = df_m['Nome'].tolist() if not df_m.empty else []
        marc_sel = st.selectbox("Marcador / Assunto", options=["Selecione..."] + lista_m)

    is_correlato = st.checkbox("Tratar como Correlatos?", help="Peso reduzido para processos extras")

    if st.button("🚀 EXECUTAR DISTRIBUIÇÃO", type="primary", use_container_width=True):
        if not num_proc or marc_sel == "Selecione...":
            st.warning("Preencha os campos obrigatórios!")
        else:
            # Cálculo do Peso
            peso_base = df_m.loc[df_m['Nome'] == marc_sel, 'Peso'].values[0]
            procs = [p.strip() for p in num_proc.split(',') if p.strip()]
            qtd = len(procs)
            
            if is_correlato:
                peso_final = float(peso_base) + (0.10 * (qtd - 1))
            else:
                peso_final = float(peso_base) * qtd

            # Sorteio
            ganhador = sortear_assessor(df_e, df_h)

            # Salvar
            nova_linha = pd.DataFrame({
                "Data": [datetime.now().strftime("%d/%m/%Y %H:%M")],
                "Processos": [num_proc],
                "Assessor": [ganhador],
                "Peso_Total": [float(peso_final)],
                "Tipo": ["Correlato" if is_correlato else "Normal"],
                "Triador": [triador]
            })
            
            df_atualizado = pd.concat([df_h, nova_linha], ignore_index=True)
            conn.update(spreadsheet=URL_PLANILHA, worksheet="distribuicoes", data=df_atualizado)
            
            st.success(f"✅ Enviado para: **{ganhador}** | Peso total: {peso_final}")
            st.balloons()
            st.cache_data.clear()
            st.rerun()

# --- GRÁFICOS ---
st.divider()
if not df_h.empty:
    st.subheader("📊 Carga Acumulada da Equipe")
    chart_data = df_h.groupby("Assessor")["Peso_Total"].sum().sort_values()
    st.bar_chart(chart_data)
    
    with st.expander("Ver Histórico Recente"):
        st.dataframe(df_h.sort_index(ascending=False), use_container_width=True)
else:
    st.info("Nenhuma distribuição registrada no histórico ainda.")
