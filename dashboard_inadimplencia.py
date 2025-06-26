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

    soma_apos_merge = df_merged["Montante em moeda interna"].sum()
    if abs(soma_bruta_planilha - soma_apos_merge) > 1:
        st.warning(f"Soma após merge: R$ {soma_apos_merge:,.2f} difere do bruto: R$ {soma_bruta_planilha:,.2f}")

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
    c1.metric("Soma bruta planilha", f"R$ {soma_bruta_planilha:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c2.metric("Valor Total Inadimplente", f"R$ {tot_inad:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c3.metric("Venda Antecipada Inadimplente", f"R$ {tot_venda_antec:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c4.metric("Valor Total Contas a Receber", f"R$ {tot_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    with st.expander("Clique para ver o Resumo por Cliente"):
        if 'Nome 1' in df_inad.columns:
            resumo_cli = df_inad.groupby('Nome 1')['Montante em moeda interna'].sum().reset_index()
            resumo_cli.rename(columns={'Nome 1': 'Cliente', 'Montante em moeda interna': 'Valor Inadimplente'}, inplace=True)
            resumo_cli['Representatividade'] = resumo_cli['Valor Inadimplente'] / tot_inad
            resumo_cli = resumo_cli.sort_values(by='Valor Inadimplente', ascending=False)
            resumo_cli['Valor Inadimplente'] = resumo_cli['Valor Inadimplente'].apply(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            resumo_cli['% sobre Total'] = resumo_cli['Representatividade'].apply(lambda x: f"{x:.1%}")
            st.dataframe(resumo_cli[['Cliente', 'Valor Inadimplente', '% sobre Total']], use_container_width=True)

            top10 = df_inad.groupby('Nome 1')['Montante em moeda interna'].sum().reset_index()
            top10.rename(columns={'Nome 1': 'Cliente', 'Montante em moeda interna': 'Valor'}, inplace=True)
            top10 = top10.sort_values(by='Valor', ascending=False).head(10)
            top10['Texto'] = top10['Valor'].apply(lambda x: f"{x/1_000_000:.1f}M" if x >= 1_000_000 else (f"{x/1_000:.0f}K" if x >= 1_000 else f"{x:,.0f}"))
            fig_top10 = px.bar(top10, y='Cliente', x='Valor', text='Texto', orientation='h', color_discrete_sequence=['#2C3E50'])
            fig_top10.update_traces(textposition="outside")
            fig_top10.update_layout(title='Top 10 Clientes Inadimplentes', showlegend=False, height=500)
            st.plotly_chart(fig_top10, use_container_width=True)
        else:
            st.warning("Coluna 'Nome 1' (cliente) não encontrada na base de dados.")
