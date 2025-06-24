import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from io import BytesIO

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(layout="wide", page_title="Dashboard Inadimplência")

# --- URLs E CONSTANTES DO GITHUB ---
OWNER = "rodneirac"
REPO = "BIINADIMSPX"
ARQUIVO_DADOS = "INADIMATUAL.XLSX"
ARQUIVO_REGIAO = "REGIAO.xlsx"

URL_DADOS = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/{ARQUIVO_DADOS}"
URL_REGIAO = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/{ARQUIVO_REGIAO}"
LOGO_URL = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/logo.png"

# --- FUNÇÕES DE CARREGAMENTO DE DADOS ---
@st.cache_data(ttl=3600)
def load_data(url):
    response = requests.get(url)
    df = pd.read_excel(BytesIO(response.content), engine="openpyxl")
    df["Data do documento"] = pd.to_datetime(df["Data do documento"], errors="coerce")
    df["Vencimento líquido"] = pd.to_datetime(df["Vencimento líquido"], errors="coerce")
    return df

@st.cache_data(ttl=3600)
def load_region_data(url):
    response = requests.get(url)
    df = pd.read_excel(BytesIO(response.content), engine="openpyxl")
    return df

# --- FUNÇÃO AUXILIAR PARA ENCONTRAR NOME DA COLUNA ---
def get_division_column_name(df):
    if 'Divisao' in df.columns:
        return 'Divisao'
    elif 'Divisão' in df.columns:
        return 'Divisão'
    else:
        return None

# --- FUNÇÕES DE CLASSIFICAÇÃO ---
def classifica_exercicio(data):
    if pd.isnull(data):
        return "Sem data"
    ano = data.year
    if ano <= 2021: return "2021 ou anterior"
    elif ano == 2022: return "2022"
    elif ano == 2023: return "2023"
    elif ano == 2024: return "2024"
    elif ano == 2025: return "2025"
    else: return "Futuro"

def classifica_faixa(dias):
    if dias <= 30: return "Até 30 dias"
    elif dias <= 60: return "31 a 60 dias"
    elif dias <= 180: return "61 a 180 dias"
    elif dias <= 365: return "181 a 365 dias"
    else: return "Acima de 365 dias"

def classifica_prazo(dias):
    if dias <= 60: return "Curto Prazo"
    else: return "Longo Prazo"

# --- CARREGAMENTO E PROCESSAMENTO DOS DADOS ---
df_original = load_data(URL_DADOS)
df_regiao = load_region_data(URL_REGIAO)

if not df_original.empty and not df_regiao.empty:
    coluna_divisao_principal = get_division_column_name(df_original)
    coluna_divisao_regiao = get_division_column_name(df_regiao)

    if not coluna_divisao_principal or not coluna_divisao_regiao:
        st.error("Erro Crítico: A coluna de divisão não foi encontrada em um dos arquivos.")
        st.stop()

    df_original[coluna_divisao_principal] = df_original[coluna_divisao_principal].astype(str)
    df_regiao[coluna_divisao_regiao] = df_regiao[coluna_divisao_regiao].astype(str)

    df_regiao.rename(columns={coluna_divisao_regiao: coluna_divisao_principal}, inplace=True)
    df = pd.merge(df_original, df_regiao, on=coluna_divisao_principal, how="left")
    df['Região'] = df['Região'].fillna('Não definida')

    # Filtros
    st.sidebar.title("Filtros")
    lista_regioes = sorted(df['Região'].unique())
    regiao_selecionada = st.sidebar.selectbox("Selecione a Região:", ["TODAS AS REGIÕES"] + lista_regioes)
    lista_divisoes = sorted(df[coluna_divisao_principal].unique())
    divisao_selecionada = st.sidebar.selectbox("Selecione a Divisão:", ["TODAS AS DIVISÕES"] + lista_divisoes)

    df_filtrado = df.copy()
    if regiao_selecionada != "TODAS AS REGIÕES":
        df_filtrado = df_filtrado[df_filtrado['Região'] == regiao_selecionada]
    if divisao_selecionada != "TODAS AS DIVISÕES":
        df_filtrado = df_filtrado[df_filtrado[coluna_divisao_principal] == divisao_selecionada]

    # Cálculos de atraso
    hoje = datetime.now()
    df_filtrado["Dias de atraso"] = (hoje - df_filtrado["Vencimento líquido"]).dt.days
    df_filtrado["Exercicio"] = df_filtrado["Data do documento"].apply(classifica_exercicio)
    df_filtrado["Faixa"] = df_filtrado["Dias de atraso"].apply(classifica_faixa)
    df_filtrado["Prazo"] = df_filtrado["Dias de atraso"].apply(classifica_prazo)

    # Total bruto e conferência
    total_bruto = df_filtrado["Montante em moeda interna"].sum()
    df_inad = df_filtrado[df_filtrado["Dias de atraso"] >= 1].copy()
    df_vencer = df_filtrado[df_filtrado["Dias de atraso"] <= 0].copy()
    total_inad = df_inad["Montante em moeda interna"].sum()
    total_vencer = df_vencer["Montante em moeda interna"].sum()
    total_geral = total_inad + total_vencer

    # Título
    st.image(LOGO_URL, width=200)
    st.title("Dashboard de Análise de Inadimplência")
    st.markdown(f"**Exibindo dados para:** Região: `{regiao_selecionada}` | Divisão: `{divisao_selecionada}`")

    # Indicadores
    st.markdown("### Indicadores Gerais")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Valor Total Bruto (conferência)", f"R$ {total_bruto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col2.metric("Valor Total Inadimplente", f"R$ {total_inad:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col3.metric("Valor Total à Vencer", f"R$ {total_vencer:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col4.metric("Valor Total Contas a Receber", f"R$ {total_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # Quadro detalhado
    st.markdown("### Quadro Detalhado de Inadimplência")
    pivot = pd.pivot_table(df_inad, index=["Exercicio", "Faixa"],
                           values="Montante em moeda interna", columns="Prazo",
                           aggfunc="sum", fill_value=0, margins=True, margins_name="Total Geral").reset_index()
    def format_currency(v): 
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    st.dataframe(
        pivot.style.format({col: format_currency for col in pivot.columns if col not in ["Exercicio", "Faixa"]}),
        use_container_width=True
    )

    # Resumo por divisão
    with st.expander("Clique para ver o Resumo por Divisão"):
        resumo_divisao = df_inad.groupby(coluna_divisao_principal)['Montante em moeda interna'].sum().reset_index()
        resumo_divisao.rename(columns={coluna_divisao_principal: 'Divisão', 'Montante em moeda interna': 'Valor Inadimplente'}, inplace=True)
        resumo_divisao = resumo_divisao.sort_values(by='Valor Inadimplente', ascending=False).reset_index(drop=True)
        resumo_divisao['Valor Inadimplente'] = resumo_divisao['Valor Inadimplente'].apply(format_currency)
        st.dataframe(resumo_divisao, use_container_width=True)

    # Gráfico pizza 3D simulado
    st.markdown("### Inadimplência por Região (3D Simulado)")
    inad_por_regiao = df_inad.groupby('Região')['Montante em moeda interna'].sum().reset_index()
    fig_regiao = px.pie(
        inad_por_regiao,
        names='Região',
        values='Montante em moeda interna',
        title='Participação por Região',
        hole=0.2
    )
    fig_regiao.update_traces(
        textposition='inside',
        textinfo='percent+label',
        pull=[0.05] * len(inad_por_regiao)
    )
    fig_regiao.update_layout(title_font_size=16, height=400)
    st.plotly_chart(fig_regiao, use_container_width=True)

else:
    st.error("Dados não disponíveis.")
