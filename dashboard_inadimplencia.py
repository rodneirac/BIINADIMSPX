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

def classifica_atraso(dias):
    if dias < 0:
        return "À vencer"
    elif dias <= 30:
        return "Até 30 dias"
    elif dias <= 60:
        return "entre 31 e 60 dias"
    else:
        return "mais de 61 dias"

def classifica_prazo(dias):
    if dias < 0:
        return "À vencer"
    elif dias <= 60:
        return "Curto Prazo"
    else:
        return "Longo Prazo"

# --- INTERFACE ---
st.image(LOGO_URL, width=200)
st.title("Dashboard Inadimplência")

df = load_data(URL_DADOS)

if not df.empty:
    hoje = pd.Timestamp.today()
    df["Dias de atraso"] = (hoje - df["Vencimento líquido"]).dt.days
    df["Exercicio"] = df.apply(lambda row: classifica_exercicio(row["Data do documento"], row["Dias de atraso"]), axis=1)
    df["Faixa atraso"] = df["Dias de atraso"].apply(classifica_atraso)
    df["Prazo"] = df["Dias de atraso"].apply(classifica_prazo)

    agrupado = df[df["Dias de atraso"] >= 0].groupby(["Exercicio", "Prazo"]).agg({"Montante em moeda interna": "sum"}).unstack(fill_value=0)
    agrupado.columns = [col[1] for col in agrupado.columns]
    agrupado["Total Geral"] = agrupado.sum(axis=1)
    agrupado = agrupado.reset_index()
    agrupado = agrupado.sort_values(by="Exercicio", ascending=False)

    st.markdown("### Quadro de Inadimplência por Exercício e Prazo")
    st.table(agrupado.style.format({
        "Curto Prazo": lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "Longo Prazo": lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "Total Geral": lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    }).set_properties(**{"text-align": "center"}))
else:
    st.warning("Dados não disponíveis ou planilha vazia.")
