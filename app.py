import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÕES ---
ID_PLANILHA = "1btSAJK1M71CTGrtOVnEV4EHmEaF9NGR6nMvpGI6qHt0"
URL_BASE = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/gviz/tq?tqx=out:csv&sheet="

st.set_page_config(page_title="Distribuidor GAB PRE/GO", layout="wide", page_icon="⚖️")

# Inicializa o histórico na sessão do navegador (memória temporária)
if 'historico_recente' not in st.session_state:
    st.session_state.historico_recente = []

@st.cache_data(ttl=10)
def carregar_dados():
    try:
        df_m = pd.read_csv(URL_BASE + "marcadores").fillna("")
        df_e = pd.read_csv(URL_BASE + "equipe").fillna("")
        df_c = pd.read_csv(URL_BASE + "config").fillna("")
        return df_m, df_e, df_c
    except Exception as e:
        st.error(f"Erro ao acessar planilha: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def verificar_ativo(row):
    try:
        hoje = datetime.now()
        inicio = pd.to_datetime(row['Inicio_Afastamento'], dayfirst=True)
        fim = pd.to_datetime(row['Fim_Afastamento'], dayfirst=True)
        if pd.notna(inicio) and pd.notna(fim):
            return not (inicio <= hoje <= fim)
        return True
    except:
        return True

# --- INTERFACE ---
df_m, df_e, df_c = carregar_dados()

st.title("⚖️ Distribuidor Inteligente - GAB PRE/GO")

with st.sidebar:
    st.header("⚙️ Controle")
    # Filtra equipe ativa baseada nas datas da planilha
    df_e['Status_Ativo'] = df_e.apply(verificar_ativo, axis=1)
    equipe_disponivel = df_e[df_e['Status_Ativo'] == True]['Nome'].tolist()
    
    triador_atual = st.selectbox("Triador da Semana", options=equipe_disponivel if equipe_disponivel else ["Nenhum Ativo"])
    
    if st.button("🔄 Sincronizar Planilha"):
        st.cache_data.clear()
        st.rerun()

# Área de Sorteio
with st.container(border=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        num_proc = st.text_area("Número do(s) Processo(s)", placeholder="Insira os números separados por vírgula...")
    with col2:
        marcs = df_m['Nome'].tolist() if not df_m.empty else []
        marc_sel = st.selectbox("Marcador / Assunto", options=["Selecione..."] + marcs)
        is_correlato = st.checkbox("Correlatos?")

    if st.button("🚀 EXECUTAR DISTRIBUIÇÃO", type="primary", use_container_width=True):
        if num_proc and marc_sel != "Selecione...":
            # Filtro de Especialidade (Regra do Vazio)
            espec_exigida = df_m.loc[df_m['Nome'] == marc_sel, 'Especialidade'].values[0]
            if espec_exigida == "":
                candidatos = equipe_disponivel
            else:
                candidatos = df_e[(df_e['Status_Ativo'] == True) & (df_e['Especialidade'] == espec_exigida)]['Nome'].tolist()

            if not candidatos:
                st.error("Nenhum assessor disponível para esta especialidade hoje.")
            else:
                # Sorteio Simples (Já que não lemos histórico acumulado)
                import random
                ganhador = random.choice(candidatos)
                
                # Registro no Histórico da Sessão
                novo_registro = {
                    "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Processo": num_proc[:30] + "..." if len(num_proc) > 30 else num_proc,
                    "Marcador": marc_sel,
                    "Sorteado": ganhador
                }
                st.session_state.historico_recente.insert(0, novo_registro)
                st.session_state.historico_recente = st.session_state.historico_recente[:10]
                
                st.balloons()
                st.subheader(f"✅ Sorteado: :blue[{ganhador}]")
        else:
            st.warning("Preencha todos os campos.")

# Tabela de Histórico Recente
st.divider()
st.subheader("📋 Últimas 10 Distribuições (Sessão Atual)")
if st.session_state.historico_recente:
    st.table(pd.DataFrame(st.session_state.historico_recente))
else:
    st.info("Nenhuma distribuição realizada nesta sessão.")
