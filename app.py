import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Distribuição GAB PRE/GO", layout="wide")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #004b87; color: white; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DO ESTADO (BANCO DE DADOS TEMPORÁRIO) ---
if 'marcardores' not in st.session_state:
    st.session_state.marcardores = pd.DataFrame(columns=['Marcador', 'Peso'])
if 'equipe' not in st.session_state:
    st.session_state.equipe = pd.DataFrame(columns=['Nome', 'Especialidades', 'Saldo'])
if 'ferias' not in st.session_state:
    st.session_state.ferias = {}
if 'historico' not in st.session_state:
    st.session_state.historico = pd.DataFrame(columns=['Data', 'Processo', 'Marcador', 'Assessor', 'Peso Real'])
if 'triador_atual' not in st.session_state:
    st.session_state.triador_atual = None

# --- FUNÇÕES AUXILIARES ---
def calcular_bloqueio_ferias(nome_assessor):
    if nome_assessor not in st.session_state.ferias:
        return False
    f = st.session_state.ferias[nome_assessor]
    if f['inicio'] is None or f['fim'] is None:
        return False
    
    hoje = datetime.now().date()
    # Cálculo de 3 dias úteis antes
    dias_contados = 0
    temp_date = f['inicio']
    while dias_contados < 3:
        temp_date -= timedelta(days=1)
        if temp_date.weekday() < 5: # Segunda a Sexta
            dias_contados += 1
    
    data_inicio_bloqueio = temp_date
    return data_inicio_bloqueio <= hoje <= f['fim']

# --- TELA DE LOGIN ---
def login():
    st.title("🔐 Acesso Restrito")
    senha = st.text_input("Digite a senha do Gabinete:", type="password")
    if senha == "prego2026":
        st.session_state.autenticado = True
        st.rerun()
    elif senha != "":
        st.error("Senha incorreta.")

if 'autenticado' not in st.session_state:
    login()
    st.stop()

# --- BARRA LATERAL (CONFIGURAÇÕES E PROCESSOS) ---
with st.sidebar:
    st.title("⚙️ Configurações")
    aba_cfg = st.tabs(["Marcadores", "Equipe", "Férias"])

    # ABA 1: MARCADORES
    with aba_cfg[0]:
        with st.form("form_marcadores"):
            nome_m = st.text_input("Nome do Marcador")
            peso_m = st.number_input("Peso (Horas)", min_value=0.25, step=0.25)
            if st.form_submit_button("Salvar Marcador"):
                nova_linha = pd.DataFrame({'Marcador': [nome_m], 'Peso': [peso_m]})
                st.session_state.marcardores = pd.concat([st.session_state.marcardores, nova_linha], ignore_index=True)
        st.dataframe(st.session_state.marcardores, use_container_width=True)

    # ABA 2: EQUIPE
    with aba_cfg[1]:
        nome_e = st.text_input("Nome do Assessor")
        if st.button("Cadastrar Assessor"):
            if nome_e and nome_e not in st.session_state.equipe['Nome'].values:
                nova_eq = pd.DataFrame({'Nome': [nome_e], 'Especialidades': [[]], 'Saldo': [0.0]})
                st.session_state.equipe = pd.concat([st.session_state.equipe, nova_eq], ignore_index=True)
        
        for idx, row in st.session_state.equipe.iterrows():
            with st.expander(f"Especialidades: {row['Nome']}"):
                escolhas = []
                for m in st.session_state.marcardores['Marcador']:
                    is_checked = m in row['Especialidades']
                    if st.checkbox(m, value=is_checked, key=f"check_{row['Nome']}_{m}"):
                        escolhas.append(m)
                st.session_state.equipe.at[idx, 'Especialidades'] = escolhas

    # ABA 3: FÉRIAS
    with aba_cfg[2]:
        for nome in st.session_state.equipe['Nome']:
            st.write(f"**{nome}**")
            col1, col2 = st.columns(2)
            with col1:
                ini = st.date_input("Início", key=f"ini_{nome}", value=st.session_state.ferias.get(nome, {}).get('inicio', None))
            with col2:
                fim = st.date_input("Fim", key=f"fim_{nome}", value=st.session_state.ferias.get(nome, {}).get('fim', None))
            
            if st.button("Limpar", key=f"btn_{nome}"):
                st.session_state.ferias[nome] = {'inicio': None, 'fim': None}
            else:
                st.session_state.ferias[nome] = {'inicio': ini, 'fim': fim}
            st.divider()

    st.markdown("---")
    st.title("📄 Processos")
    num_proc = st.text_input("Número (até 26 caracteres)", max_chars=26)
    data_proc = st.date_input("Data", format="DD/MM/YYYY")
    marcador_sel = st.selectbox("Marcador", options=st.session_state.marcardores['Marcador'].tolist())

    if st.button("🚀 Distribuir"):
        # 1. Filtro de Férias
        disponiveis = [n for n in st.session_state.equipe['Nome'] if not calcular_bloqueio_ferias(n)]
        
        if not disponiveis:
            st.error("Não há assessores disponíveis (todos em férias ou bloqueio).")
        else:
            # 2. Válvula de Escape: Quem é o mais carregado do gabinete?
            assessor_mais_carregado = st.session_state.equipe.sort_values(by='Saldo', ascending=False).iloc[0]['Nome']
            
            # 3. Filtrar especialistas para o marcador
            especialistas = []
            for n in disponiveis:
                specs = st.session_state.equipe[st.session_state.equipe['Nome'] == n]['Especialidades'].values[0]
                if marcador_sel in specs:
                    especialistas.append(n)
            
            # Se o especialista for o mais carregado ou se não houver especialista disponível
            if not especialistas or (len(especialistas) == 1 and especialistas[0] == assessor_mais_carregado):
                selecao_final = disponiveis # Abre para todos
                motivo = "Válvula de Escape ativada ou sem especialista específico."
            else:
                selecao_final = especialistas
                motivo = "Distribuição entre especialistas."

            # 4. Escolher quem tem o menor saldo entre os selecionados
            ranking = st.session_state.equipe[st.session_state.equipe['Nome'].isin(selecao_final)].sort_values(by='Saldo')
            vencedor = ranking.iloc[0]['Nome']
            
            # 5. Calcular Peso (Regra do Triador)
            peso_base = st.session_state.marcardores[st.session_state.marcardores['Marcador'] == marcador_sel]['Peso'].values[0]
            peso_final = peso_base * 2 if vencedor == st.session_state.triador_atual else peso_base
            
            # 6. Atualizar Saldo e Histórico
            idx_venc = st.session_state.equipe[st.session_state.equipe['Nome'] == vencedor].index
            st.session_state.equipe.at[idx_venc[0], 'Saldo'] += peso_final
            
            novo_hist = pd.DataFrame({
                'Data': [data_proc.strftime("%d/%m/%y")],
                'Processo': [num_proc],
                'Marcador': [marcador_sel],
                'Assessor': [vencedor],
                'Peso Real': [peso_final]
            })
            st.session_state.historico = pd.concat([novo_hist, st.session_state.historico], ignore_index=True)
            st.success(f"✅ DISTRIBUÍDO: Entregar para {vencedor} ({motivo})")

# --- PAINEL PRINCIPAL ---
st.header("⚖️ Distribuição de Processos GAB PRE/GO")

# Destaque do Triador
with st.container():
    st.info("⚡ **GESTÃO DE TRIAGEM**")
    st.session_state.triador_atual = st.selectbox(
        "Quem é o triador da semana? (Desoneração de 50%)", 
        options=st.session_state.equipe['Nome'].tolist(),
        index=0 if st.session_state.triador_atual is None and not st.session_state.equipe.empty else None
    )

st.divider()

col_graf, col_hist = st.columns([1, 1])

with col_graf:
    st.subheader("📊 Pote de Horas (Saldo Atual)")
    if not st.session_state.equipe.empty:
        df_grafico = st.session_state.equipe.sort_values(by='Saldo', ascending=True)
        st.bar_chart(data=df_grafico, x='Nome', y='Saldo', color='#004b87')
    else:
        st.write("Cadastre a equipe para ver o gráfico.")

with col_hist:
    st.subheader("📜 Últimas Distribuições")
    st.dataframe(st.session_state.historico.head(10), use_container_width=True)

# Rodapé informando bloqueios ativos
st.divider()
st.subheader("📅 Status da Equipe")
cols = st.columns(len(st.session_state.equipe['Nome']) if not st.session_state.equipe.empty else 1)
for i, nome in enumerate(st.session_state.equipe['Nome']):
    em_ferias = calcular_bloqueio_ferias(nome)
    status = "🔴 Bloqueado/Férias" if em_ferias else "🟢 Disponível"
    if nome == st.session_state.triador_atual:
        status = "⭐ Triador"
    cols[i].metric(nome, f"{st.session_state.equipe.iloc[i]['Saldo']}h", status)
