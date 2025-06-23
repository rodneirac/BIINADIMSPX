import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from io import BytesIO

# --- URLs E CONSTANTES DO GITHUB ---
ARQUIVO_DADOS = "INADIMATUAL.XLSX"
OWNER = "rodneirac"
REPO = "BIINADIMSPX"

URL_DADOS = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/{ARQUIVO_DADOS}"
LOGO_URL = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/logo.png"

@st.cache_data(ttl=3600)
def load_data(url):
    response = requests.get(url)
    df = pd.read_excel(BytesIO(response.content), engine="openpyxl")
    df["Data do documento"] = pd.to_datetime(df["Data do documento"], errors="coerce")
    df["Vencimento líquido"] = pd.to_datetime(df["Vencimento líquido"], errors="coerce")
    return df

def classifica_exercicio(data, dias_atraso):
    if data <= pd.Timestamp("2021-12-31"):
        return "2021(Acumulado)"
    elif data <= pd.Timestamp("2022-12-31"):
        return "2022"
    elif data <= pd.Timestamp("2023-12-31"):
        return "2023"
    elif data <= pd.Timestamp("2024-12-31"):
        return "2024"
    elif data <= pd.Timestamp("2025-12-31"):
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
    hoje = pd.Timestamp.today()
    df["Dias de atraso"] = (hoje - df["Vencimento líquido"]).dt.days
    df["Exercicio"] = df.apply(lambda row: classifica_exercicio(row["Data do documento"], row["Dias de atraso"]), axis=1)

    agrupado = df[df["Dias de atraso"] >= 0].groupby(["Exercicio"]).agg({"Montante em moeda interna": "sum"}).reset_index()
    
    # Formatação visual com pandas Styler
    styled = agrupado.style.format({"Montante em moeda interna": lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")}) \
        .set_properties(**{"text-align": "center"}) \
        .bar(subset=["Montante em moeda interna"], color='#5DADE2')

    st.markdown("### Quadro de Inadimplência por Exercício (Visual Estilizado)")
    st.dataframe(styled, use_container_width=True)
else:
    st.warning("Dados não disponíveis ou planilha vazia.")
