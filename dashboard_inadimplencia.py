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
    # As conversões de tipo serão feitas de forma robusta mais tarde
    df["Data do documento"] = pd.to_datetime(df["Data do documento"], errors="coerce")
    df["Vencimento líquido"] = pd.to_datetime(df["Vencimento líquido"], errors="coerce")
    return df

@st.cache_data(ttl=3600)
def load_region_data(url):
    response = requests.get(url)
    df = pd.read_excel(BytesIO(response.content), engine="openpyxl")
    return df

# --- FUNÇÃO AUXILIAR PARA ENCONTRAR NOME DA COLUNA ---
def get_division_column_name(df):
    if 'Divisao' in df.columns:
        return 'Divisao'
    elif 'Divisão' in df.columns:
        return 'Divisão'
    else:
        return None

# --- FUNÇÕES DE CLASSIFICAÇÃO ---
def classifica_exercicio(data):
    if data <= pd.Timestamp("2021-12-31"): return "2021(Acumulado)"
    elif data <= pd.Timestamp("2022-12-31"): return "2022"
    elif data <= pd.Timestamp("2023-12-31"): return "2023"
    elif data <= pd.Timestamp("2024-12-31"): return "2024"
    elif data <= pd.Timestamp("2025-12-31"): return "2025"
    else: return "Fora do período"
# ... (outras funções de classificação) ...
def classifica_faixa(exercicio, dias):
    if exercicio == "2025":
        if dias <= 30: return "Até 30 dias"
        elif dias <= 60: return "entre 31 e 60 dias"
        else: return "mais de 61 dias"
    return ""
def classifica_prazo(dias):
    if dias <= 60: return "Curto Prazo"
    else: return "Longo Prazo"

# --- CARREGAMENTO E PROCESSAMENTO ROBUSTO DOS DADOS ---
df_original = load_data(URL_DADOS)
df_regiao = load_region_data(URL_REGIAO)

if not df_original.empty and not df_regiao.empty:
    # 1. Encontra dinamicamente o nome da coluna de divisão em cada arquivo
    coluna_divisao_principal = get_division_column_name(df_original)
    coluna_divisao_regiao = get_division_column_name(df_regiao)

    if not coluna_divisao_principal or not coluna_divisao_regiao:
        st.error("Erro Crítico: A coluna 'Divisao' ou 'Divisão' não foi encontrada em um dos arquivos fonte. Verifique seus arquivos Excel.")
        st.stop()

    # 2. Garante que as colunas sejam do tipo texto para a junção
    df_original[coluna_divisao_principal] = df_original[coluna_divisao_principal].astype(str)
    df_regiao[coluna_divisao_regiao] = df_regiao[coluna_divisao_regiao].astype(str)
    if 'Nome do cliente' in df_original.columns:
        df_original['Nome do cliente'] = df_original['Nome do cliente'].astype(str)

    # 3. Renomeia a coluna no arquivo de região para corresponder ao arquivo principal
    df_regiao.rename(columns={coluna_divisao_regiao: coluna_divisao_principal}, inplace=True)

    # 4. Faz a junção usando o nome de coluna correto e unificado
    df = pd.merge(df_original, df_regiao, on=coluna_divisao_principal, how="left")
    df['Região'] = df['Região'].fillna('Não definida')

    # --- BARRA LATERAL (SIDEBAR) COM FILTROS ---
    st.sidebar.title("Filtros")
    lista_regioes = sorted(df['Região'].unique())
    opcoes_filtro = ["TODAS AS REGIÕES"] + lista_regioes
    regiao_selecionada = st.sidebar.selectbox("Selecione a Região:", options=opcoes_filtro)

    if regiao_selecionada == "TODAS AS REGIÕES":
        df_filtrado = df.copy()
    else:
        df_filtrado = df[df['Região'] == regiao_selecionada].copy()

    # --- Início da Interface Principal ---
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
    
    # ... (O código dos gráficos permanece o mesmo) ...

    # --- RESUMO SIMPLES POR DIVISÃO ---
    st.markdown("<hr>", unsafe_allow_html=True)
    with st.expander("Clique para ver o Resumo por Divisão"):
        st.markdown("##### Inadimplência Agregada por Divisão")
        
        # Usa a variável com o nome correto da coluna
        resumo_divisao = df_inad.groupby(coluna_divisao_principal)['Montante em moeda interna'].sum().reset_index()
        resumo_divisao.rename(columns={coluna_divisao_principal: 'Divisão', 'Montante em moeda interna': 'Valor Inadimplente'}, inplace=True)
        resumo_divisao = resumo_divisao.sort_values(by='Valor Inadimplente', ascending=False)
        
        st.dataframe(resumo_divisao, use_container_width=True)
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    st.markdown("### Quadro Detalhado de Inadimplência")
    pivot = pd.pivot_table(df_inad, index=["Exercicio", "Faixa"], values="Montante em moeda interna", columns="Prazo", aggfunc="sum", fill_value=0, margins=True, margins_name="Total Geral").reset_index()
    def format_currency(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    st.dataframe(pivot.style.format({col: format_currency for col in pivot.columns if col not in ["Exercicio", "Faixa"]}).set_properties(**{"text-align": "center"}), use_container_width=True)

else:
    st.error("Dados não disponíveis.")
