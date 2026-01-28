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
        # Lê as abas
        m = conn.read(spreadsheet=URL_PLANILHA, worksheet="marcadores")
        e = conn.read(spreadsheet=URL_PLANILHA, worksheet="equipe")
        h = conn.read(spreadsheet=URL_PLANILHA, worksheet="distribuicoes")
        
        # Limpa espaços nos nomes das colunas (evita erro de 'Nome ' vs 'Nome')
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
        return "Erro: Coluna 'Nome' não encontrada na aba equipe"
    
    lista_equipe = df_equipe['Nome'].dropna().tolist()
    
    if not df_hist.empty and 'Assessor' in df_hist.columns:
        # Soma a carga de cada um
        cargas = df_hist.groupby('Assessor')['Peso_Total'].sum()
        ranking = {nome: cargas.get(nome, 0.0) for nome in lista_equipe}
        # Retorna quem tem menos peso acumulado
        return min(ranking, key=ranking.get)
    
    # Se histórico vazio, pega o primeiro da lista
    return lista_equipe[0]

# --- EXECUÇÃO ---
df_m, df_e, df_h = carregar_dados()

st.title("⚖️ Sistema de Distribuição - GAB PRE/GO")

# Interface Lateral
with st.sidebar:
    st.header("Configurações")
    lista_nomes = df_e['Nome'].dropna().tolist() if not df_e.empty else []
    triador = st.selectbox("Triador da Semana", options=lista_nomes if lista_nomes else ["Nenhum"])
    
    if st.button("🔄 Forçar Atualização"):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    st.link_button("❓ Manual de Instruções", URL_TUTORIAL)

# Área de Trabalho
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
            st.warning("Por favor, preencha o número do processo e o marcador.")
        else:
            # Pega o peso do marcador selecionado
            peso_base = df_m.loc[df_m['Nome'] == marc_sel, 'Peso'].values[0]
            # Conta quantos processos foram colados (separados por vírgula)
            procs = [p.strip() for p in num_proc.split(',') if p.strip()]
            qtd = len(procs)
            
            # Cálculo do peso total
            if is_correlato:
                peso_final = float(peso_base) + (0.10 * (qtd - 1))
            else:
                peso_final = float(peso_base) * qtd

            # Sorteio automático
            ganhador = sortear_assessor(df_e, df_h)

            # Gravação dos dados
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
                
                st.success(f"✅ Sorteado: **{ganh
