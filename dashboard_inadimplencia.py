import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from io import BytesIO

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
    # Garante que colunas de identificação sejam tratadas como texto (string)
    if 'Divisao' in df.columns: # Correção: Usa 'Divisao' sem acento
        df['Divisao'] = df['Divisao'].astype(str)
    if 'Nome do cliente' in df.columns:
        df['Nome do cliente'] = df['Nome do cliente'].astype(str)
    df["Data do documento"] = pd.to_datetime(df["Data do documento"], errors="coerce")
    df["Vencimento líquido"] = pd.to_datetime(df["Vencimento líquido"], errors="coerce")
    return df

@st.cache_data(ttl=3600)
def load_region_data(url):
    response = requests.get(url)
    df = pd.read_excel(BytesIO(response.content), engine="openpyxl")
    # Garante que a coluna de junção seja texto
    if 'Divisão' in df.columns: # Aqui o nome original é 'Divisão' com acento
        df['Divisão'] = df['Divisão'].astype(str)
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
    
    # --- CORREÇÃO APLICADA AQUI ---
    # Renomeia a coluna no df_regiao para corresponder ao df_original
    if 'Divisão' in df_regiao.columns:
        df_regiao.rename(columns={'Divisão': 'Divisao'}, inplace=True)

    # A junção agora funciona com o nome de coluna correto e unificado
    df = pd.merge(df_original, df_regiao, on="Divisao", how="left")
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
    
    total_inad = df_inad["Montante em moeda interna"].sum()
    total_vencer = df_vencer["Montante em moeda interna"].sum()
    total_geral = total_inad + total_vencer

    st.markdown("### Indicadores Gerais")
    col1, col2, col3 = st.columns(3)
    col1.metric("Valor Total Inadimplente", f"R$ {total_inad/1_000_000:,.1f} MM")
    col2.metric("Valor Total à Vencer", f"R$ {total_vencer/1_000_000:,.1f} MM")
    col3.metric("Valor Total Contas a Receber", f"R$ {total_geral/1_000_000:,.1f} MM")

    st.markdown("<hr>", unsafe_allow_html=True)
    
    # ... (O código dos gráficos permanece o mesmo e deve funcionar agora) ...

    # --- RESUMOS RECOLHÍVEIS ---
    st.markdown("<hr>", unsafe_allow_html=True)
    
    with st.expander("Clique para ver o Resumo por Divisão"):
        st.markdown("##### Inadimplência Agregada por Divisão")
        # Correção: usa 'Divisao' sem acento no groupby
        resumo_divisao = df_inad.groupby('Divisao').agg(
            Valor_Inadimplente=('Montante em moeda interna', 'sum'),
            Qtde_Clientes=('Nome do cliente', 'nunique'),
            Qtde_Titulos=('Montante em moeda interna', 'count')
        ).reset_index()
        total_inad_resumo = resumo_divisao['Valor_Inadimplente'].sum()
        if total_inad_resumo > 0:
            resumo_divisao['Representatividade (%)'] = (resumo_divisao['Valor_Inadimplente'] / total_inad_resumo) * 100
        else:
            resumo_divisao['Representatividade (%)'] = 0
        resumo_divisao = resumo_divisao.sort_values(by='Valor_Inadimplente', ascending=False)
        
        # Construção Manual da Tabela
        header_cols = st.columns((2, 2, 1, 1, 2))
        header_cols[0].markdown("**Divisão**")
        header_cols[1].markdown("**Valor Inadimplente**")
        header_cols[2].markdown("**Qt. Clientes**")
        header_cols[3].markdown("**Qt. Títulos**")
        header_cols[4].markdown("**Representatividade**")
        
        for _, row in resumo_divisao.iterrows():
            row_cols = st.columns((2, 2, 1, 1, 2))
            # Correção: usa 'Divisao' sem acento para buscar o dado da linha
            row_cols[0].write(row['Divisao'])
            row_cols[1].write(f"R$ {row['Valor_Inadimplente']:,.2f}")
            row_cols[2].write(row['Qtde_Clientes'])
            row_cols[3].write(row['Qtde_Titulos'])
            row_cols[4].write(f"{row['Representatividade (%)']:.2f}%")

    with st.expander("Clique para ver o Resumo por Cliente"):
        st.markdown("##### Maiores Devedores (Top 20 Clientes)")
        resumo_cliente = df_inad.groupby('Nome do cliente').agg(
            Valor_Inadimplente=('Montante em moeda interna', 'sum'),
            Qtde_Titulos=('Montante em moeda interna', 'count')
        ).reset_index()
        total_inad_resumo_cli = resumo_cliente['Valor_Inadimplente'].sum()
        if total_inad_resumo_cli > 0:
            resumo_cliente['Representatividade (%)'] = (resumo_cliente['Valor_Inadimplente'] / total_inad_resumo_cli) * 100
        else:
            resumo_cliente['Representatividade (%)'] = 0
        resumo_cliente = resumo_cliente.sort_values(by='Valor_Inadimplente', ascending=False).head(20)

        # Construção Manual da Tabela
        header_cols_cli = st.columns((4, 2, 1, 2))
        header_cols_cli[0].markdown("**Nome do Cliente**")
        header_cols_cli[1].markdown("**Valor Inadimplente**")
        header_cols_cli[2].markdown("**Qt. Títulos**")
        header_cols_cli[3].markdown("**Representatividade**")

        for _, row in resumo_cliente.iterrows():
            row_cols_cli = st.columns((4, 2, 1, 2))
            row_cols_cli[0].write(row['Nome do cliente'])
            row_cols_cli[1].write(f"R$ {row['Valor_Inadimplente']:,.2f}")
            row_cols_cli[2].write(row['Qtde_Titulos'])
            row_cols_cli[3].write(f"{row['Representatividade (%)']:.2f}%")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### Quadro Detalhado de Inadimplência")
    pivot = pd.pivot_table(df_inad, index=["Exercicio", "Faixa"], values="Montante em moeda interna", columns="Prazo", aggfunc="sum", fill_value=0, margins=True, margins_name="Total Geral").reset_index()
    def format_currency(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    st.dataframe(pivot.style.format({col: format_currency for col in pivot.columns if col not in ["Exercicio", "Faixa"]}).set_properties(**{"text-align": "center"}), use_container_width=True)

else:
    st.error("Dados não disponíveis.")
