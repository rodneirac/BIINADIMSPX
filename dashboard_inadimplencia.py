
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
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

def classifica_exercicio(data):
    if data <= pd.Timestamp("2021-12-31"):
        return "2021(Acumulado)"
    elif data <= pd.Timestamp("2022-12-31"):
        return "2022"
    elif data <= pd.Timestamp("2023-12-31"):
        return "2023"
    elif data <= pd.Timestamp("2024-12-31"):
        return "2024"
    elif data <= pd.Timestamp("2025-12-31"):
        return "2025"
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
    df["Exercicio"] = df["Data do documento"].apply(classifica_exercicio)
    df["Dias de atraso"] = (hoje - df["Vencimento líquido"]).dt.days
    df["Faixa atraso"] = df["Dias de atraso"].apply(classifica_atraso)
    df["Prazo"] = df["Dias de atraso"].apply(classifica_prazo)

    st.sidebar.header("Filtros")
    exercicios = sorted(df["Exercicio"].unique())
    prazo_opts = sorted(df["Prazo"].unique())

    exercicio_sel = st.sidebar.multiselect("Filtrar por Exercício", exercicios, default=exercicios)
    prazo_sel = st.sidebar.multiselect("Filtrar por Prazo", prazo_opts, default=prazo_opts)

    df_filtrado = df[
        df["Exercicio"].isin(exercicio_sel) &
        df["Prazo"].isin(prazo_sel)
    ]

    total_valor = df_filtrado["Montante em moeda interna"].sum()

    st.markdown("### Indicadores Gerais")
    st.metric("Valor Total (R$)", f"{total_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.markdown("---")
    st.subheader("Distribuição por Exercício e Prazo")

    agrupado = df_filtrado.groupby(["Exercicio", "Prazo"]).agg({"Montante em moeda interna": "sum"}).reset_index()
    fig = px.bar(agrupado, x="Exercicio", y="Montante em moeda interna", color="Prazo", barmode="group",
                 text_auto=True, labels={"Montante em moeda interna": "Valor (R$)"})
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Dados não disponíveis ou planilha vazia.")
