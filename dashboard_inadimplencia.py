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

def classifica_faixa(exercicio, dias):
    if exercicio == "2025":
        if dias <= 30:
            return "Até 30 dias"
        elif dias <= 60:
            return "entre 31 e 60 dias"
        else:
            return "mais de 61 dias"
    else:
        return ""

def classifica_prazo(dias):
    if dias <= 60:
        return "Curto Prazo"
    else:
        return "Longo Prazo"

st.image(LOGO_URL, width=200)
st.title("Dashboard Inadimplência")

df = load_data(URL_DADOS)

if not df.empty:
    hoje = pd.Timestamp.today()
    df["Dias de atraso"] = (hoje - df["Vencimento líquido"]).dt.days
    df["Exercicio"] = df["Data do documento"].apply(classifica_exercicio)
    df["Faixa"] = df.apply(lambda row: classifica_faixa(row["Exercicio"], row["Dias de atraso"]), axis=1)
    df["Prazo"] = df["Dias de atraso"].apply(classifica_prazo)

    total_inad = df[df["Dias de atraso"] >= 0]["Montante em moeda interna"].sum()
    total_vencer = df[df["Dias de atraso"] < 0]["Montante em moeda interna"].sum()
    total_geral = total_inad + total_vencer

    st.markdown("### Indicadores Gerais (Cards)")
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
                <div style='background-color:#f0f2f6; padding:15px; border-radius:8px; text-align:center;'>
                    <h4>Valor Total Inadimplente (R$)</h4>
                    <p style='font-size:20px; font-weight:bold;'>{total_inad/1_000_000:,.0f} MM</p>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
                <div style='background-color:#f0f2f6; padding:15px; border-radius:8px; text-align:center;'>
                    <h4>Valor Total À Vencer (R$)</h4>
                    <p style='font-size:20px; font-weight:bold;'>{total_vencer/1_000_000:,.0f} MM</p>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
                <div style='background-color:#f0f2f6; padding:15px; border-radius:8px; text-align:center;'>
                    <h4>Valor Total Contas a Receber (R$)</h4>
                    <p style='font-size:20px; font-weight:bold;'>{total_geral/1_000_000:,.0f} MM</p>
                </div>
            """, unsafe_allow_html=True)

    df = df[df["Exercicio"] != "Fora do período"]

    pivot = pd.pivot_table(
        df,
        index=["Exercicio", "Faixa"],
        values="Montante em moeda interna",
        columns="Prazo",
        aggfunc="sum",
        fill_value=0,
        margins=True,
        margins_name="Total Geral"
    ).reset_index()

    def format_currency(v):
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    st.markdown("### Quadro de Inadimplência por Exercício e Prazo")
    st.dataframe(
        pivot.style.format({
            col: format_currency for col in pivot.columns if col not in ["Exercicio", "Faixa"]
        }).set_properties(**{"text-align": "center"}),
        use_container_width=True
    )
else:
    st.warning("Dados não disponíveis ou planilha vazia.")
