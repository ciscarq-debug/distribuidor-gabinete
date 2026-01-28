import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÕES FIXAS ---
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1btSAJK1M71CTGrtOVnEV4EHmEaF9NGR6nMvpGI6qHt0/edit?usp=sharing"
URL_TUTORIAL = "https://docs.google.com/document/d/1AFeJ16hdow2g1Di1OthFcUPZV6qkDiefKyIbe8v_mCM/edit?usp=sharing"

st.set_page_config(page_title="Distribuidor GAB PRE/GO", layout="wide", page_icon="⚖️")

# Conectando ao Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO DE CARREGAMENTO ROBUSTA ---
@st.cache_data(ttl=10)
def carregar_dados():
    try:
        m = conn.read(spreadsheet=URL_PLANILHA, worksheet="marcadores")
        e = conn.read(spreadsheet=URL_PLANILHA, worksheet="equipe")
        h = conn.read(spreadsheet=URL_PLANILHA, worksheet="distribuicoes")
        
        m.columns = m.columns.str.strip()
        e.columns = e.columns.str.strip()
        if not h.empty: 
            h.columns = h.columns.str.strip()
        
        return m, e, h
    except Exception as ex:
        st.error(f"Erro ao ler planilha: {ex}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- LÓGICA DE SORTEIO ---
def sortear_assessor(df_equipe, df_hist):
    if df_equipe.empty or 'Nome' not in df_equipe.columns:
        return "Erro: Coluna 'Nome' não encontrada"
    
    lista_equipe = df_equipe['Nome'].dropna().tolist()
    
    if not df_hist.empty and 'Assessor' in df_hist.columns:
        cargas = df_hist.groupby('Assessor')['Peso_Total'].sum()
        ranking = {nome: cargas.get(nome, 0.0) for nome in lista_equipe}
        return min(ranking, key=ranking.get)
    
    return lista_equipe[0] if lista_equipe else "Ninguém disponível"

# --- EXECUÇÃO ---
df_m, df_e, df_h = carregar_dados()

st.title("⚖️ Sistema de Distribuição - GAB PRE/GO")

with st.sidebar:
    st.header("Configurações")
    lista_nomes = df_e['Nome'].dropna().tolist() if not df_e.empty else []
    triador = st.selectbox("Triador da Semana", options=lista_nomes if lista_nomes else ["Nenhum"])
    if st.button("🔄 Forçar Atualização"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.link_button("❓ Manual de Instruções", URL_TUTORIAL)

with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        num_proc = st.text_input("Número do(s) Processo(s)", placeholder="Ex: 0600123-45...")
    with col2:
        lista_marc = df_m['Nome'].dropna().tolist() if not df_m.empty else []
        marc_sel = st.selectbox("Marcador / Assunto", options=["Selecione..."] + lista_marc)

    is_correlato = st.checkbox("Tratar como Correlatos?", help="Peso cheio no 1º e +10% nos demais")

    if st.button("🚀 EXECUTAR DISTRIBUIÇÃO", type="primary", use_container_width=True):
        if not num_proc or marc_sel == "Selecione...":
            st.warning("Preencha o número do processo e o marcador.")
        else:
            peso_base = df_m.loc[df_m['Nome'] == marc_sel, 'Peso'].values[0]
            procs = [p.strip() for p in num_proc.split(',') if p.strip()]
            qtd = len(procs)
            
            peso_final = float(peso_base) + (0.10 * (qtd - 1)) if is_correlato else float(peso_base) * qtd
            ganhador = sortear_assessor(df_e, df_h)

            nova_linha = pd.DataFrame({
                "Data": [datetime.now().strftime("%d/%m/%Y %H:%M")],
                "Processos": [num_proc],
                "Assessor": [ganhador],
                "Peso_Total": [float(peso_final)],
                "Tipo": ["Correlato" if is_correlato else "Normal"],
                "Triador": [triador]
            })
            
            try:
                df_atualizado = pd.concat([df_h, nova_linha], ignore_index=True)
                conn.update(spreadsheet=URL_PLANILHA, worksheet="distribuicoes", data=df_atualizado)
                st.success(f"✅ Sorteado: **{ganhador}** | Peso: {peso_final}")
                st.balloons()
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

st.divider()
if not df_h.empty:
    st.subheader("📊 Carga Acumulada")
    chart_data = df_h.groupby("Assessor")["Peso_Total"].sum().sort_values()
    st.bar_chart(chart_data)
    with st.expander("📂 Histórico"):
        st.dataframe(df_h.sort_index(ascending=False), use_container_width=True)
