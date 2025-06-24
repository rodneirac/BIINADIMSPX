import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from io import StringIO

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
    return df

@st.cache_data(ttl=3600)
def load_region_data(url):
    response = requests.get(url)
    df = pd.read_excel(BytesIO(response.content), engine="openpyxl")
    return df

# --- CARREGAMENTO INICIAL DOS DADOS ---
df_original = load_data(URL_DADOS)
df_regiao = load_region_data(URL_REGIAO)


# --- CÓDIGO DE DIAGNÓSTICO DE COLUNAS ---
st.subheader("Informações de Diagnóstico de Colunas")
st.markdown("Por favor, envie um print desta seção para resolver o erro `KeyError`.")

st.markdown("**1. Colunas do arquivo principal (`INADIMATUAL.XLSX`):**")
st.code(f"{list(df_original.columns)}")

st.markdown("**2. Colunas do arquivo de regiões (`REGIAO.xlsx`):**")
st.code(f"{list(df_regiao.columns)}")

st.info("O app foi interrompido aqui para análise das colunas. Assim que você me enviar o print, eu ajusto o código.")
st.stop()
# --- FIM DO DIAGNÓSTICO ---


# O restante do código não será executado por causa do st.stop()
# ...
