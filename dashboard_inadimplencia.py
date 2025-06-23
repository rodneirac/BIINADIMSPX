# 1. IMPORTS
import streamlit as st
import pandas as pd
import numpy as np  # Importado para a vetorização
from datetime import datetime
import requests
from io import BytesIO
import locale

# 2. CONFIGURAÇÕES INICIAIS DA PÁGINA E LOCALIDADE
st.set_page_config(layout="wide")
try:
    # Configura a localidade para o formato brasileiro (essencial para a formatação de moeda)
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    st.warning("Localidade 'pt_BR.UTF-8' não encontrada. A formatação de números pode usar o padrão americano.")

# 3. CONSTANTES E FUNÇÕES
ARQUIVO_DADOS = "INADIMATUAL.XLSX"
OWNER = "rodneirac"
REPO = "BIINADIMSPX"

URL_DADOS = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/{ARQUIVO_DADOS}"
LOGO_URL = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/logo.png"

# FUNÇÃO DE CARREGAMENTO DE DADOS MAIS ROBUSTA
@st.cache_data(ttl=3600)
def load_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Lança um erro para status HTTP ruins (4xx ou 5xx)
        df = pd.read_excel(BytesIO(response.content), engine="openpyxl")
        
        # Converte colunas de data, tratando erros
        df["Data do documento"] = pd.to_datetime(df["Data do documento"], errors="coerce")
        df["Vencimento líquido"] = pd.to_datetime(df["Vencimento líquido"], errors="coerce")
        
        # Remove linhas onde a conversão de data falhou, se necessário
        df.dropna(subset=["Data do documento", "Vencimento líquido"], inplace=True)
        
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Erro de conexão ao buscar os dados: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao ler o arquivo Excel: {e}")
        return pd.DataFrame()

# A função de exercício é complexa, mantemos o .apply que é mais legível neste caso
def classifica_exercicio(row):
    data = row["Data do documento"]
    dias_atraso = row["Dias de atraso"]
    
    # Usando o ano do documento para simplificar a lógica
    ano = data.year
    if ano < 2022:
        return "2021(Acumulado)"
    elif ano < 2025:
        return str(ano)
    elif ano == 2025:
        if dias_atraso <= 30:
            return "2025 - Até 30 dias"
        elif dias_atraso <= 60:
            return "2025 - entre 31 e 60 dias"
        else:
            return "2025 - mais de 61 dias"
    else:
        return "Fora do período"

# --- INTERFACE ---
st.image(LOGO_URL, width=200)
st.title("Dashboard Inadimplência")

df = load_data(URL_DADOS)

if not df.empty:
    # --- PROCESSAMENTO DE DADOS OTIMIZADO ---
    hoje = pd.Timestamp.today()
    df["Dias de atraso"] = (hoje - df["Vencimento líquido"]).dt.days

    # CLASSIFICAÇÃO VETORIZADA (MUITO MAIS RÁPIDA)
    condicoes_atraso = [
        df["Dias de atraso"] < 0,
        df["Dias de atraso"]
