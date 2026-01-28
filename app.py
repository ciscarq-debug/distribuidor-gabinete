import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÕES ---
# Transformando o link para formato de exportação direta
ID_PLANILHA = "1btSAJK1M71CTGrtOVnEV4EHmEaF9NGR6nMvpGI6qHt0"
URL_BASE = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/gviz/tq?tqx=out:csv&sheet="

URL_TUTORIAL = "https://docs.google.com/document/d/1AFeJ16hdow2g1Di1OthFcUPZV6qkDiefKyIbe8v_mCM/edit?usp=sharing"

st.set_page_config(page_title="Distribuidor GAB PRE/GO", layout="wide", page_icon="⚖️")

# --- FUNÇÃO DE CARREGAMENTO (MÉTODO DIRETO) ---
@st.cache_data(ttl=10)
def carregar_dados():
    try:
        # Lê cada aba individualmente via Pandas
        df_m = pd.read_csv(URL_BASE + "marcadores")
        df_e = pd.read_csv(URL_BASE + "equipe")
        # Para a aba de distribuicoes, tentamos ler, se falhar (vazia), criamos um DF novo
        try:
            df_h = pd.read_csv(URL_BASE + "distribuicoes")
        except:
            df_h = pd.DataFrame(columns=["Data", "Processos", "Assessor", "Peso_Total", "Tipo", "Triador"])
        
        # Limpeza básica
        df_m.columns = df_m.columns.str.strip()
        df_e.columns = df_e.columns.str.strip()
        
        return df_m, df_e, df_h
    except Exception as ex:
        st.error(f"Erro ao acessar Google Sheets: {ex}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- LÓGICA DE SORTEIO ---
def sortear_assessor(df_equipe, df_hist):
    lista_equipe = df_equipe['Nome'].dropna().unique().tolist()
    if not lista_equipe: return "Equipe não encontrada"
    
    if df_hist.empty or 'Assessor' not in df_hist.columns:
        return lista_equipe[0]
    
    # Cálculo de carga acumulada
    cargas = df_hist.groupby('Assessor')['Peso_Total'].sum()
    ranking = {nome: cargas.get(nome, 0.0) for nome in lista_equipe}
    return min(ranking, key=ranking.get)

# --- INTERFACE ---
df_m, df_e, df_h = carregar_dados()

st.title("⚖️ Sistema de Distribuição - GAB PRE/GO")

with st.sidebar:
    st.header("Configurações")
    nomes = df_e['Nome'].dropna().tolist() if not df_e.empty else []
    triador = st.selectbox("Triador da Semana", options=nomes if nomes else ["Nenhum"])
    if st.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.link_button("❓ Manual", URL_TUTORIAL)

# Formulário
with st.container(border=True):
    c1, c2 = st.columns(2)
    with c1:
        num_proc = st.text_input("Processo(s)")
    with c2:
        marcs = df_m['Nome'].dropna().tolist() if not df_m.empty else []
        marc_sel = st.selectbox("Marcador", options=["Selecione..."] + marcs)
    
    is_correlato = st.checkbox("Correlatos?")

    if st.button("🚀 DISTRIBUIR", type="primary", use_container_width=True):
        if num_proc and marc_sel != "Selecione...":
            # Pega peso
            peso_base = df_m.loc[df_m['Nome'] == marc_sel, 'Peso'].values[0]
            qtd = len([p for p in num_proc.split(',') if p.strip()])
            
            peso_calc = float(peso_base) + (0.1 * (qtd-1)) if is_correlato else float(peso_base) * qtd
            ganhador = sortear_assessor(df_e, df_h)
            
            st.success(f"Sorteado: {ganhador} (Peso: {peso_calc})")
            st.info("Nota: Para salvar permanentemente na planilha, o Google exige integração via API. Use este sorteio para preencher sua planilha manualmente por enquanto.")
            st.balloons()
        else:
            st.warning("Preencha os campos!")

# Gráfico
if not df_h.empty:
    st.divider()
    st.subheader("📊 Carga da Equipe")
    st.bar_chart(df_h.groupby("Assessor")["Peso_Total"].sum())
