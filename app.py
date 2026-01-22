import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Distribuidor Gabinete", layout="wide")

# --- BLOQUEIO DE SEGURANÇA (SENHA) ---
# Troque "gabinete2024" pela senha que você quiser
senha_digitada = st.text_input("🔒 Digite a senha de acesso:", type="password")
if senha_digitada != "gabinete2024":
    st.info("Aguardando senha para liberar o sistema...")
    st.stop()

# --- CONFIGURAÇÃO DE ARQUIVOS ---
ARQUIVO_ASSESSORES = "dados_equipe.csv"
ARQUIVO_MARCADORES = "dados_marcadores.csv"

# --- FUNÇÕES ---
def carregar_marcadores():
    if not os.path.exists(ARQUIVO_MARCADORES):
        dados = {
            "Nome do Marcador": ["Ex: Embargos", "Ex: Apelação Criminal"],
            "Peso": [1, 5],
            "Categoria": ["Cível", "Criminal"]
        }
        df = pd.DataFrame(dados)
        df.to_csv(ARQUIVO_MARCADORES, index=False)
    else:
        df = pd.read_csv(ARQUIVO_MARCADORES)
    return df

def carregar_assessores():
    if not os.path.exists(ARQUIVO_ASSESSORES):
        dados = {
            "Nome": ["Assessor A", "Assessor B"],
            "Saldo Pontos": [0, 0],
            "Especialidades": ["TODAS", "TODAS"],
            "Inicio Ferias": [None, None]
        }
        df = pd.DataFrame(dados)
        df.to_csv(ARQUIVO_ASSESSORES, index=False)
    else:
        df = pd.read_csv(ARQUIVO_ASSESSORES)
        df['Inicio Ferias'] = pd.to_datetime(df['Inicio Ferias'], errors='coerce').dt.date
    return df

def salvar_arquivo(df, nome_arquivo):
    df.to_csv(nome_arquivo, index=False)

def verificar_disponibilidade(assessor_row, categoria_processo):
    hoje = date.today()
    ferias = assessor_row['Inicio Ferias']
    especialidades = assessor_row['Especialidades']
    
    # Regra de Férias (5 dias)
    if pd.notnull(ferias):
        dias_para_ferias = (ferias - hoje).days
        if dias_para_ferias <= 0: return False, "Em Férias/Licença"
        if dias_para_ferias <= 5: return False, f"Bloqueio Pré-Férias ({dias_para_ferias} dias restam)"

    # Regra de Especialidade
    if especialidades != "TODAS":
        if categoria_processo not in especialidades:
             return False, f"Não atende {categoria_processo}"
    return True, "Apto"

# --- INTERFACE ---
st.title("⚖️ Sistema de Distribuição de Processos")

df_marcadores = carregar_marcadores()
df_assessores = carregar_assessores()

with st.sidebar:
    st.header("⚙️ Configurações")
    tab1, tab2 = st.tabs(["👥 Equipe", "📂 Marcadores"])
    
    with tab1:
        st.caption("Ajuste férias e especialidades")
        df_assessores_editado = st.data_editor(
            df_assessores,
            num_rows="dynamic",
            column_config={
                "Inicio Ferias": st.column_config.DateColumn("Início Férias"),
                "Saldo Pontos": st.column_config.NumberColumn("Saldo", disabled=True),
                "Especialidades": st.column_config.TextColumn("Especialidades (Use 'TODAS' ou vírgulas)")
            },
            key="editor_equipe"
        )
        if st.button("Salvar Equipe"):
            salvar_arquivo(df_assessores_editado, ARQUIVO_ASSESSORES)
            st.success("Salvo!")
            st.rerun()

    with tab2:
        st.caption("Tipos de Processos e Pesos")
        df_marcadores_editado = st.data_editor(
            df_marcadores,
            num_rows="dynamic",
            column_config={
                "Peso": st.column_config.NumberColumn("Peso", min_value=1, max_value=20),
                "Categoria": st.column_config.SelectboxColumn("Categoria", options=["Cível", "Criminal", "Trabalhista", "Administrativo", "Constitucional", "Tributário", "Família"])
            },
            key="editor_marcadores"
        )
        if st.button("Salvar Marcadores"):
            salvar_arquivo(df_marcadores_editado, ARQUIVO_MARCADORES)
            st.success("Salvo!")
            st.rerun()
            
    st.divider()
    if st.button("⚠️ Zerar Saldos (Novo Mês)"):
        df_assessores['Saldo Pontos'] = 0
        salvar_arquivo(df_assessores, ARQUIVO_ASSESSORES)
        st.warning("Saldos zerados.")
        st.rerun()

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Nova Distribuição")
    lista_opcoes = df_marcadores['Nome do Marcador'].unique()
    processo_selecionado = st.selectbox("Selecione o Tipo:", lista_opcoes)
    
    if len(df_marcadores) > 0:
        dados_proc = df_marcadores[df_marcadores['Nome do Marcador'] == processo_selecionado].iloc[0]
        peso_atual = int(dados_proc['Peso'])
        cat_atual = dados_proc['Categoria']
        st.info(f"Categoria: {cat_atual} | Peso: {peso_atual}")
    
    num_processo = st.text_input("Número / ID (Opcional)")

    if st.button("🚀 Distribuir", type="primary"):
        candidatos = []
        log = []
        for index, row in df_assessores.iterrows():
            apto, motivo = verificar_disponibilidade(row, cat_atual)
            if apto: candidatos.append(index)
            else: log.append(f"{row['Nome']}: {motivo}")
        
        if not candidatos:
            st.error("Ninguém disponível!")
            with st.expander("Ver motivos"):
                for l in log: st.write(l)
        else:
            df_aptos = df_assessores.loc[candidatos]
            idx_vencedor = df_aptos['Saldo Pontos'].idxmin()
            nome_vencedor = df_assessores.at[idx_vencedor, 'Nome']
            
            df_assessores.at[idx_vencedor, 'Saldo Pontos'] += peso_atual
            salvar_arquivo(df_assessores, ARQUIVO_ASSESSORES)
            
            st.balloons()
            st.success(f"ENTREGAR PARA: **{nome_vencedor}**")
            st.caption(f"Saldo atualizado do assessor: {df_assessores.at[idx_vencedor, 'Saldo Pontos']}")

with col2:
    st.subheader("Placar Atual")
    df_view = df_assessores.sort_values(by="Saldo Pontos")
    st.dataframe(
        df_view,
        column_config={"Saldo Pontos": st.column_config.ProgressColumn("Carga", format="%d pts", min_value=0, max_value=int(df_view["Saldo Pontos"].max() + 10))},
        use_container_width=True,
        hide_index=True
    )