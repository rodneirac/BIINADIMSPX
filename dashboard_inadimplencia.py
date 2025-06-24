import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from io import StringIO # Importa StringIO para o diagnóstico

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
    if 'Nome do cliente' in df.columns:
        df['Nome do cliente'] = df['Nome do cliente'].astype(str)
    if 'Divisão' in df.columns:
        df['Divisão'] = df['Divisão'].fillna('N/D') # Preenche Divisões vazias
    df["Data do documento"] = pd.to_datetime(df["Data do documento"], errors="coerce")
    df["Vencimento líquido"] = pd.to_datetime(df["Vencimento líquido"], errors="coerce")
    return df

@st.cache_data(ttl=3600)
def load_region_data(url):
    response = requests.get(url)
    df = pd.read_excel(BytesIO(response.content), engine="openpyxl")
    return df

# --- FUNÇÕES DE CLASSIFICAÇÃO ---
def classifica_exercicio(data):
    if data <= pd.Timestamp("2021-12-31"): return "2021(Acumulado)"
    elif data <= pd.Timestamp("2022-12-31"): return "2022"
    elif data <= pd.Timestamp("2023-12-31"): return "2023"
    elif data <= pd.Timestamp("2024-12-31"): return "2024"
    elif data <= pd.Timestamp("2025-12-31"): return "2025"
    else: return "Fora do período"

def classifica_faixa(exercicio, dias):
    if exercicio == "2025":
        if dias <= 30: return "Até 30 dias"
        elif dias <= 60: return "entre 31 e 60 dias"
        else: return "mais de 61 dias"
    return ""

def classifica_prazo(dias):
    if dias <= 60: return "Curto Prazo"
    else: return "Longo Prazo"

# --- CARREGAMENTO INICIAL DOS DADOS ---
df_original = load_data(URL_DADOS)
df_regiao = load_region_data(URL_REGIAO)

# --- Processamento e Junção dos Dados ---
if not df_original.empty and not df_regiao.empty:
    df = pd.merge(df_original, df_regiao, on="Divisão", how="left")
    df['Região'] = df['Região'].fillna('Não definida')

    st.sidebar.title("Filtros")
    lista_regioes = sorted(df['Região'].unique())
    opcoes_filtro = ["TODAS AS REGIÕES"] + lista_regioes
    regiao_selecionada = st.sidebar.selectbox("Selecione a Região:", options=opcoes_filtro)

    if regiao_selecionada == "TODAS AS REGIÕES":
        df_filtrado = df.copy()
    else:
        df_filtrado = df[df['Região'] == regiao_selecionada].copy()

    st.image(LOGO_URL, width=200)
    st.title("Dashboard de Análise de Inadimplência")
    st.markdown(f"**Exibindo dados para:** `{regiao_selecionada}`")

    hoje = pd.Timestamp.today()
    df_filtrado["Dias de atraso"] = (hoje - df_filtrado["Vencimento líquido"]).dt.days
    df_filtrado["Exercicio"] = df_filtrado["Data do documento"].apply(classifica_exercicio)
    df_filtrado["Faixa"] = df_filtrado.apply(lambda row: classifica_faixa(row["Exercicio"], row["Dias de atraso"]), axis=1)
    df_filtrado["Prazo"] = df_filtrado["Dias de atraso"].apply(classifica_prazo)
    
    df_inad = df_filtrado[df_filtrado["Dias de atraso"] >= 0].copy()
    df_vencer = df_filtrado[df_filtrado["Dias de atraso"] < 0].copy()

    if df_inad.empty:
        st.warning(f"Não há dados de inadimplência para a seleção '{regiao_selecionada}'.")
        st.stop()
    
    # ... (código dos cards e gráficos - sem alterações) ...
    total_inad = df_inad["Montante em moeda interna"].sum()
    total_vencer = df_vencer["Montante em moeda interna"].sum()
    total_geral = total_inad + total_vencer
    st.markdown("### Indicadores Gerais")
    col1, col2, col3 = st.columns(3)
    col1.metric("Valor Total Inadimplente", f"R$ {total_inad/1_000_000:,.1f} MM")
    col2.metric("Valor Total à Vencer", f"R$ {total_vencer/1_000_000:,.1f} MM")
    col3.metric("Valor Total Contas a Receber", f"R$ {total_geral/1_000_000:,.1f} MM")
    st.markdown("<hr>", unsafe_allow_html=True)
    graf_col1, graf_col2 = st.columns(2)
    # ... (código dos gráficos)

    # --- RESUMOS RECOLHÍVEIS ---
    st.markdown("<hr>", unsafe_allow_html=True)
    
    with st.expander("Clique para ver o Resumo por Divisão"):
        st.markdown("##### Inadimplência Agregada por Divisão")
        resumo_divisao = df_inad.groupby('Divisão').agg(
            Valor_Inadimplente=('Montante em moeda interna', 'sum'),
            Qtde_Clientes=('Nome do cliente', 'nunique'),
            Qtde_Titulos=('Montante em moeda interna', 'count')
        ).reset_index()
        
        # --- NOVO CÓDIGO DE DIAGNÓSTICO ---
        st.subheader("Informações de Diagnóstico (Resumo por Divisão)")
        st.markdown("Por favor, envie um print desta seção.")
        
        st.markdown("**1. Primeiras 5 linhas do DataFrame `resumo_divisao`:**")
        st.dataframe(resumo_divisao.head())
        
        st.markdown("**2. Informações sobre os tipos de dados (`.info()`):**")
        buffer = StringIO()
        resumo_divisao.info(buf=buffer)
        s = buffer.getvalue()
        st.text(s)
        
        st.info("O app foi interrompido aqui para análise do erro.")
        st.stop() # Interrompe a execução para evitar o erro

        # A linha que causa o erro está desativada abaixo
        # st.dataframe(resumo_divisao, use_container_width=True)

    # (O restante do código não será executado por causa do st.stop())
else:
    st.error("Dados não disponíveis.")
