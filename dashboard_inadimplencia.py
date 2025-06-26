import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from io import BytesIO

st.set_page_config(layout="wide", page_title="Dashboard Inadimplência")

OWNER = "rodneirac"
REPO = "BIINADIMSPX"
ARQUIVO_DADOS = "INADIMATUAL.XLSX"
ARQUIVO_REGIAO = "REGIAO.xlsx"

URL_DADOS = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/{ARQUIVO_DADOS}"
URL_REGIAO = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/{ARQUIVO_REGIAO}"
LOGO_URL = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/logo.png"

if st.button("\U0001F504 Recarregar dados"):
    st.cache_data.clear()
    st.rerun()

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

def get_division_column_name(df):
    if 'Divisao' in df.columns:
        return 'Divisao'
    elif 'Divisão' in df.columns:
        return 'Divisão'
    else:
        return None

def classifica_exercicio(data):
    if pd.isnull(data):
        return "Sem data"
    ano = data.year
    if ano <= 2021: return "2021(Acumulado)"
    elif ano == 2022: return "2022"
    elif ano == 2023: return "2023"
    elif ano == 2024: return "2024"
    elif ano == 2025: return "2025"
    else: return "Futuro"

def classifica_faixa(exercicio, dias):
    if exercicio == "2025":
        if dias <= 30: return "Até 30 dias"
        elif dias <= 60: return "entre 31 e 60 dias"
        else: return "mais de 61 dias"
    return ""

def classifica_prazo(dias):
    if dias <= 60: return "Curto Prazo"
    else: return "Longo Prazo"

def format_moeda(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

df_original = load_data(URL_DADOS)
df_regiao = load_region_data(URL_REGIAO)

if not df_original.empty and not df_regiao.empty:
    soma_bruta_planilha = df_original["Montante em moeda interna"].sum()

    col_div_princ = get_division_column_name(df_original)
    col_div_regiao = get_division_column_name(df_regiao)

    if not col_div_princ or not col_div_regiao:
        st.error("Erro Crítico: Coluna de divisão não encontrada.")
        st.stop()

    df_original[col_div_princ] = df_original[col_div_princ].astype(str)
    df_regiao[col_div_regiao] = df_regiao[col_div_regiao].astype(str)

    df_regiao = df_regiao.drop_duplicates(subset=[col_div_regiao])
    df_merged = pd.merge(df_original, df_regiao, on=col_div_princ, how="left")

    df_merged["Exercicio"] = df_merged["Data do documento"].apply(classifica_exercicio)

    st.sidebar.title("Filtros")
    regiao_sel = st.sidebar.selectbox("Selecione a Região:", ["TODAS AS REGIÕES"] + sorted(df_merged['Região'].fillna('Não definida').unique()))
    divisao_sel = st.sidebar.selectbox("Selecione a Divisão:", ["TODAS AS DIVISÕES"] + sorted(df_merged[col_div_princ].unique()))
    exercicio_sel = st.sidebar.selectbox("Selecione o Exercício:", ["TODOS OS EXERCÍCIOS"] + sorted(df_merged['Exercicio'].unique()))

    df_filt = df_merged.copy()
    if regiao_sel != "TODAS AS REGIÕES":
        df_filt = df_filt[df_filt['Região'] == regiao_sel]
    if divisao_sel != "TODAS AS DIVISÕES":
        df_filt = df_filt[df_filt[col_div_princ] == divisao_sel]
    if exercicio_sel != "TODOS OS EXERCÍCIOS":
        df_filt = df_filt[df_filt['Exercicio'] == exercicio_sel]

    hoje = datetime.now()
    df_filt["Dias de atraso"] = (hoje - df_filt["Vencimento líquido"]).dt.days
    df_filt["Faixa"] = df_filt.apply(lambda row: classifica_faixa(row["Exercicio"], row["Dias de atraso"]), axis=1)
    df_filt["Prazo"] = df_filt["Dias de atraso"].apply(classifica_prazo)

    df_inad = df_filt[df_filt["Dias de atraso"] >= 1].copy()
    df_venc = df_filt[df_filt["Dias de atraso"] <= 0].copy()

    tot_inad = df_inad["Montante em moeda interna"].sum()
    tot_venda_antec = df_inad[df_inad['FrmPgto'].isin(['H', 'R'])]["Montante em moeda interna"].sum()
    tot_geral = tot_inad + df_venc["Montante em moeda interna"].sum()

    st.image(LOGO_URL, width=200)
    st.title("Dashboard de Análise de Inadimplência")
    st.markdown(f"**Exibindo dados para:** Região: `{regiao_sel}` | Divisão: `{divisao_sel}` | Exercício: `{exercicio_sel}`")

    st.markdown("### Indicadores Gerais")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Soma bruta planilha", format_moeda(soma_bruta_planilha))
    c2.metric("Valor Total Inadimplente", format_moeda(tot_inad))
    c3.metric("Venda Antecipada Inadimplente", format_moeda(tot_venda_antec))
    c4.metric("Valor Total Contas a Receber", format_moeda(tot_geral))

    # Resumo por cliente e top 10 já incluso acima

    with st.expander("Resumo por Divisão"):
        df_div = df_inad.groupby(col_div_princ)["Montante em moeda interna"].sum().reset_index()
        df_div.rename(columns={"Montante em moeda interna": "Valor"}, inplace=True)
        df_div["Valor"] = df_div["Valor"].apply(format_moeda)
        st.dataframe(df_div, use_container_width=True)

    st.markdown("### Gráfico por Exercício e Faixa")
    df_ex = df_inad.copy()
    df_ex["Categoria"] = df_ex.apply(lambda row: row["Exercicio"] + (" - " + row["Faixa"] if row["Faixa"] else ""), axis=1)
    df_graf = df_ex.groupby("Categoria")["Montante em moeda interna"].sum().reset_index()
    df_graf.rename(columns={"Montante em moeda interna": "Valor"}, inplace=True)
    fig_cat = px.bar(df_graf, x="Categoria", y="Valor", text=df_graf["Valor"].apply(lambda x: f"{x/1_000_000:.1f}M"), color="Categoria")
    fig_cat.update_layout(showlegend=False, height=400)
    fig_cat.update_traces(textposition="outside")
    st.plotly_chart(fig_cat, use_container_width=True)

    st.markdown("### Participação por Região")
    df_pie = df_inad.groupby("Região")["Montante em moeda interna"].sum().reset_index()
    fig_pie = px.pie(df_pie, names="Região", values="Montante em moeda interna", hole=0.3)
    fig_pie.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("### Quadro por Prazo e Faixa")
    pivot = pd.pivot_table(df_inad, index=["Exercicio", "Faixa"], columns="Prazo", values="Montante em moeda interna", aggfunc="sum", fill_value=0)
    pivot = pivot.reset_index()
    for col in pivot.columns:
        if col not in ["Exercicio", "Faixa"]:
            pivot[col] = pivot[col].apply(format_moeda)
    st.dataframe(pivot, use_container_width=True)
else:
    st.error("Dados não disponíveis.")
