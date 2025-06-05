import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import os
import plotly.graph_objects as go
from datetime import datetime

# Sempre primeiro
st.set_page_config(layout="wide", page_title="Dashboard de Despesas Semanal")

USERNAME = st.secrets["USERNAME"]
PASSWORD = st.secrets["PASSWORD"]

# Estado da sessão
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'login_attempted' not in st.session_state:
    st.session_state.login_attempted = False

# Função de login
def login():
    st.title("🔐 Login")
    with st.form("login_form"):
        user = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            if user.strip() == USERNAME and password.strip() == PASSWORD:
                st.session_state.logged_in = True
                st.rerun()  # Força a atualização da página
            else:
                st.session_state.login_attempted = True
                st.rerun()  # Força a atualização para mostrar o erro

    if st.session_state.login_attempted and not st.session_state.logged_in:
        st.error("Usuário ou senha incorretos.")

# Renderização condicional
if not st.session_state.logged_in:
    login()
    st.stop()

data_dir = "tabela_origem"

current_date = datetime.now().date()
formatted_date = current_date.strftime("%m/%Y")

data_frames = [
    pd.read_csv(os.path.join(data_dir, file), delimiter=";")
    for file in os.listdir(data_dir)
    if file.endswith(".csv")
]
data = pd.concat(data_frames)

data.columns = data.columns.str.replace("'", "").str.strip()

def convert_to_numeric(value):
    if isinstance(value, str):
        value = value.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
    try:
        return float(value)
    except:
        return 0.0

data['VALOR TOTAL CONTA'] = data['VALOR TOTAL CONTA'].apply(convert_to_numeric)
data['ORÇAMENTO'] = data['ORÇAMENTO'].apply(convert_to_numeric)
data['VALOR'] = data['VALOR'].apply(convert_to_numeric)

def format_currency(value):
    return f'R$ {value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

st.image("assets/logo claro.png", width=200)
st.title(f"Dashboard de Despesas - {formatted_date}")

with st.expander("Filtros", expanded=True):
    nome_conta_ordenados = sorted(data['NOME CONTA'].unique())
    selected_nome_conta = st.multiselect(
        "Nome da Conta",
        options=nome_conta_ordenados,
        default=nome_conta_ordenados
    )

filtered_data = data[data["NOME CONTA"].isin(selected_nome_conta)]

orcamento_por_conta = filtered_data.groupby('NOME CONTA')['ORÇAMENTO'].mean().reset_index()
despesas_por_conta = filtered_data.groupby('NOME CONTA')['VALOR'].sum().reset_index()
despesas_por_conta = despesas_por_conta.sort_values('VALOR', ascending=True)
contas_ordenadas = despesas_por_conta['NOME CONTA'].tolist()

totals = {}
for conta in contas_ordenadas:
    despesa = despesas_por_conta.loc[despesas_por_conta['NOME CONTA'] == conta, 'VALOR'].iloc[0]
    orcamento = orcamento_por_conta.loc[orcamento_por_conta['NOME CONTA'] == conta, 'ORÇAMENTO'].iloc[0]
    totals[conta] = despesa + orcamento

differences = {}
colors = {}
for conta in contas_ordenadas:
    val = despesas_por_conta.loc[despesas_por_conta['NOME CONTA'] == conta, 'VALOR'].iloc[0]
    orc = orcamento_por_conta.loc[orcamento_por_conta['NOME CONTA'] == conta, 'ORÇAMENTO'].iloc[0]
    differences[conta] = orc - val
    colors[conta] = 'red' if val >= orc else 'blue'

fig1 = go.Figure()
fig1.add_trace(
    go.Bar(
        x=despesas_por_conta['NOME CONTA'],
        y=[(val/totals[conta])*100 if totals[conta] > 0 else 0 
           for conta, val in zip(despesas_por_conta['NOME CONTA'], despesas_por_conta['VALOR'])],
        name='Despesas',
        text=[format_currency(val) for val in despesas_por_conta['VALOR']],
        textposition='inside',
        marker_color=[colors[conta] for conta in despesas_por_conta['NOME CONTA']],
        customdata=[format_currency(differences[conta]) for conta in despesas_por_conta['NOME CONTA']],
        hovertemplate=(
            "<b>Despesas: </b>R$ %{text}<br>"
            "<b>Conta: </b>%{x}<br>"
            "<b>Orçamento: </b>%{customdata}<br>"
            "<extra></extra>"
        )
    )
)
fig1.add_trace(
    go.Bar(
        x=orcamento_por_conta['NOME CONTA'],
        y=[(val/totals[conta])*100 if totals[conta] > 0 else 0 
           for conta, val in zip(orcamento_por_conta['NOME CONTA'], orcamento_por_conta['ORÇAMENTO'])],
        name='Orçamento',
        text=[format_currency(val) for val in orcamento_por_conta['ORÇAMENTO']],
        textposition='inside',
        marker_color='orange',
        hovertemplate=(
            "<b>Orçamento: </b>R$ %{text}<br>"
            "<b>Conta: </b>%{x}<br>"
            "<extra></extra>"
        )
    )
)
fig1.update_layout(
    title="Despesas x Orçamento por Conta",
    height=600,
    width=1200,
    barmode='stack'
)
st.plotly_chart(fig1, use_container_width=True)

ORC_MENSAL = 158256
despesas_por_mes = filtered_data.groupby('MES/ANO')['VALOR'].sum().reset_index()
despesas_por_mes['DATA_ORDEM'] = pd.to_datetime(despesas_por_mes['MES/ANO'], format='%m/%Y')
despesas_por_mes = despesas_por_mes.sort_values('DATA_ORDEM')
meses_ordenados = despesas_por_mes['MES/ANO'].tolist()

differences_mes = {}
colors_mes = {}
for mes in meses_ordenados:
    valor = despesas_por_mes.loc[despesas_por_mes['MES/ANO'] == mes, 'VALOR'].iloc[0]
    differences_mes[mes] = ORC_MENSAL - valor
    colors_mes[mes] = 'red' if differences_mes[mes] < 0 else 'blue'

fig2 = go.Figure()
fig2.add_trace(
    go.Bar(
        x=meses_ordenados,
        y=despesas_por_mes['VALOR'],
        name='Despesas Totais por Mês',
        text=[format_currency(val) for val in despesas_por_mes['VALOR']],
        textposition='inside',
        customdata=[format_currency(differences_mes[mes]) for mes in meses_ordenados],
        hovertemplate=(
            "<b>Despesas: </b>R$ %{text}<br>"
            "<b>Mês: </b>%{x}<br>"
            "<b>Diferença do Orçamento: </b>%{customdata}<br>"
            "<extra></extra>"
        ),
        marker_color=[colors_mes[mes] for mes in despesas_por_mes['MES/ANO']],
    )
)
fig2.add_trace(
    go.Bar(
        x=meses_ordenados,
        y=[ORC_MENSAL] * len(meses_ordenados),
        name='Orçamento Total (R$ 158.256,00)',
        text=[format_currency(ORC_MENSAL) for _ in meses_ordenados],
        textposition='inside',
        marker_color='orange',
        hovertemplate="<b>Orçamento Total Mensal: </b>R$ %{y:,.2f}<extra></extra>",
    )
)
fig2.update_layout(
    title='Despesas por Mês X Orçamento Total por Mês',
    height=600,
    width=1200,
    barmode='stack'
)
st.plotly_chart(fig2, use_container_width=True)
