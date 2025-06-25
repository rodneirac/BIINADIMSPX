import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image
from datetime import datetime

# Logo
logo = Image.open("logo_supermix.png")
st.set_page_config(layout="wide")
st.image(logo, width=120)

st.markdown("""<h1 style='font-size: 36px;'>Dashboard de Análise de Inadimplência</h1>""", unsafe_allow_html=True)

# Função para carregar dados
def carregar_dados():
    url = "https://raw.githubusercontent.com/rodnei0/dashboard_inadimplencia/main/INADIMATUAL.CSV"
    df = pd.read_csv(url, sep=";", decimal=",", encoding='latin1')
    df["Data Vencimento"] = pd.to_datetime(df["Data Vencimento"], errors='coerce')
    df = df[df["Data Vencimento"] < pd.to_datetime("today")]
    df["Montante em moeda interna"] = df["Montante em moeda interna"].astype(float)
    return df

# Botão de recarregar dados
if st.button("🔄 Recarregar dados"):
    st.cache_data.clear()
    st.rerun()

# Carrega dados com cache
df_base = st.cache_data(ttl=3600)(carregar_dados)()
df = df_base.copy()

# Preparando colunas e agrupamentos
df["Exercicio"] = df["Ano Vencimento"].astype(str)
df.loc[df["Exercicio"] == "2021", "Exercicio"] = "2021(Acumulado)"
df["Faixa"] = df["Faixa Atraso"].fillna("")

# Filtros
col_reg, col_div, col_ano = st.sidebar.columns(1), st.sidebar.columns(1), st.sidebar.columns(1)
regiao_sel = st.sidebar.selectbox("Selecione a Região:", ["TODAS AS REGIÕES"] + sorted(df['Região'].dropna().unique()))
divisao_sel = st.sidebar.selectbox("Selecione a Divisão:", ["TODAS AS DIVISÕES"] + sorted(df['Divisao'].dropna().unique()))
exercicio_sel = st.sidebar.selectbox("Selecione o Exercício:", ["TODOS OS EXERCÍCIOS"] + sorted(df['Exercicio'].unique()))

# Aplica os filtros
if regiao_sel != "TODAS AS REGIÕES":
    df = df[df['Região'] == regiao_sel]
if divisao_sel != "TODAS AS DIVISÕES":
    df = df[df['Divisao'] == divisao_sel]
if exercicio_sel != "TODOS OS EXERCÍCIOS":
    df = df[df['Exercicio'] == exercicio_sel]

# KPIs
total_inad = df["Montante em moeda interna"].sum()
total_curto = df[df["Faixa"] == "Até 30 dias"]["Montante em moeda interna"].sum()
total_longo = df[~df["Faixa"].isin(["Até 30 dias"])] ["Montante em moeda interna"].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Valor Total Inadimplente", f"R$ {total_inad:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
col2.metric("Valor Total Curto Prazo", f"R$ {total_curto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
col3.metric("Valor Total a Vencer", "R$ 0,00")
col4.metric("Valor Total Contas a Receber", f"R$ {(total_inad):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

# Quadro Detalhado
st.markdown("## Quadro Detalhado de Inadimplência")
df_quadro = df.copy()
df_quadro = df_quadro.groupby(["Exercicio", "Faixa"]).agg({"Montante em moeda interna": "sum"}).reset_index()
df_quadro["Curto Prazo"] = df_quadro.apply(lambda x: x["Montante em moeda interna"] if x["Faixa"] == "Até 30 dias" else 0, axis=1)
df_quadro["Longo Prazo"] = df_quadro.apply(lambda x: x["Montante em moeda interna"] if x["Faixa"] != "Até 30 dias" else 0, axis=1)
df_quadro_final = df_quadro.groupby("Exercicio").agg({"Curto Prazo": "sum", "Longo Prazo": "sum"}).reset_index()
df_quadro_final["Total Geral"] = df_quadro_final["Curto Prazo"] + df_quadro_final["Longo Prazo"]
df_quadro_final.loc[len(df_quadro_final)] = ["Total Geral"] + df_quadro_final[["Curto Prazo", "Longo Prazo", "Total Geral"]].sum().tolist()

st.dataframe(df_quadro_final.style.format({
    "Curto Prazo": "R$ {:,.2f}",
    "Longo Prazo": "R$ {:,.2f}",
    "Total Geral": "R$ {:,.2f}"
}), use_container_width=True)

# Gráfico de barras
st.markdown("## Inadimplência por Exercício")
df_bar = df.groupby("Exercicio")["Montante em moeda interna"].sum().reset_index().sort_values("Exercicio")
fig_bar = px.bar(df_bar, x="Exercicio", y="Montante em moeda interna", 
                 labels={"Montante em moeda interna": "Valor (R$)"},
                 text_auto='.2s',
                 color_discrete_sequence=["#e74c3c"])
fig_bar.update_layout(height=400)
st.plotly_chart(fig_bar, use_container_width=True)

# Gráfico de pizza
st.markdown("## Inadimplência por Região (3D Simulado)")
df_pizza = df.groupby("Região")["Montante em moeda interna"].sum().reset_index()
fig_pie = px.pie(df_pizza, values="Montante em moeda interna", names="Região", hole=0.3, height=600, width=800)
fig_pie.update_traces(textinfo='percent+label', pull=[0.05]*len(df_pizza))
st.plotly_chart(fig_pie, use_container_width=True)

# Resumo por Divisão (expansivo)
with st.expander("Clique para ver o Resumo por Divisão"):
    df_div = df.groupby("Divisao")["Montante em moeda interna"].sum().reset_index().sort_values(by="Montante em moeda interna", ascending=False)
    st.dataframe(df_div.style.format({"Montante em moeda interna": "R$ {:,.2f}"}), use_container_width=True)
