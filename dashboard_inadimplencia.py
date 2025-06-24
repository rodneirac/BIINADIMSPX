import streamlit as st
import pandas as pd
import requests
import plotly.express as px
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
    """Carrega os dados do Excel a partir de uma URL, fazendo o cache do resultado."""
    response = requests.get(url)
    df = pd.read_excel(BytesIO(response.content), engine="openpyxl")
    df["Data do documento"] = pd.to_datetime(df["Data do documento"], errors="coerce")
    df["Vencimento líquido"] = pd.to_datetime(df["Vencimento líquido"], errors="coerce")
    return df

def classifica_exercicio(data):
    """Classifica o registro com base no ano da data do documento."""
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
    """Classifica a faixa de atraso para o exercício de 2025."""
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
    """Classifica o prazo como Curto ou Longo com base nos dias de atraso."""
    if dias <= 60:
        return "Curto Prazo"
    else:
        return "Longo Prazo"

# --- Início da Interface do Streamlit ---

st.image(LOGO_URL, width=200)
st.title("Dashboard Inadimplência")

df = load_data(URL_DADOS)

if not df.empty:
    hoje = pd.Timestamp.today()
    df["Dias de atraso"] = (hoje - df["Vencimento líquido"]).dt.days
    df["Exercicio"] = df["Data do documento"].apply(classifica_exercicio)
    df["Faixa"] = df.apply(lambda row: classifica_faixa(row["Exercicio"], row["Dias de atraso"]), axis=1)
    df["Prazo"] = df["Dias de atraso"].apply(classifica_prazo)

    df_inad = df[df["Dias de atraso"] >= 0]
    df_vencer = df[df["Dias de atraso"] < 0]

    total_inad = df_inad["Montante em moeda interna"].sum()
    total_vencer = df_vencer["Montante em moeda interna"].sum()
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

    st.markdown("---")

    # --- INÍCIO DA SEÇÃO DO GRÁFICO DE BARRAS (VERSÃO ATUALIZADA) ---
    st.markdown("### Detalhamento da Inadimplência por Exercício e Faixa (2025)")

    if not df_inad.empty:
        # 1. Preparar dados para anos ANTERIORES a 2025 (total por ano)
        df_outros_anos = df_inad[df_inad['Exercicio'] != '2025'].copy()
        inad_outros_anos = df_outros_anos.groupby('Exercicio')['Montante em moeda interna'].sum().reset_index()
        inad_outros_anos.rename(columns={'Exercicio': 'Categoria', 'Montante em moeda interna': 'Valor'}, inplace=True)

        # 2. Preparar dados para 2025, detalhados por FAIXA
        df_2025 = df_inad[df_inad['Exercicio'] == '2025'].copy()
        inad_2025_por_faixa = df_2025.groupby('Faixa')['Montante em moeda interna'].sum().reset_index()
        # Remove faixas vazias, caso existam
        inad_2025_por_faixa = inad_2025_por_faixa[inad_2025_por_faixa['Faixa'] != '']
        # Adiciona '2025 - ' ao nome da faixa para clareza no gráfico
        inad_2025_por_faixa['Categoria'] = '2025 - ' + inad_2025_por_faixa['Faixa']
        inad_2025_por_faixa.rename(columns={'Montante em moeda interna': 'Valor'}, inplace=True)

        # 3. Combinar os dataframes para o gráfico final
        df_grafico = pd.concat([inad_outros_anos, inad_2025_por_faixa[['Categoria', 'Valor']]], ignore_index=True)
        df_grafico = df_grafico.sort_values('Categoria')

        # 4. Criar o mapa de cores
        # Cor padrão vermelha para os anos anteriores
        color_map = {cat: '#EA4335' for cat in inad_outros_anos['Categoria'].unique()}
        # Cores diferentes para as faixas de 2025
        cores_2025 = ['#FFC107', '#FF9800', '#F57C00'] # Tons de Amarelo/Laranja
        categorias_2025 = sorted(inad_2025_por_faixa['Categoria'].unique())
        for i, cat in enumerate(categorias_2025):
            color_map[cat] = cores_2025[i % len(cores_2025)] # Atribui as cores

        # 5. Criar e exibir o gráfico
        fig = px.bar(
            df_grafico,
            x='Categoria',
            y='Valor',
            text=df_grafico['Valor'].apply(lambda x: f'{x/1_000_000:,.1f} M'),
            title='Inadimplência por Exercício (com detalhamento para 2025)',
            color='Categoria',
            color_discrete_map=color_map
        )
        fig.update_layout(
            xaxis_title="Exercício / Faixa de Atraso em 2025",
            yaxis_title="Valor Total Inadimplente (R$)",
            showlegend=False,
            uniformtext_minsize=8,
            uniformtext_mode='hide'
        )
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("Não há dados de inadimplência para gerar o gráfico.")
    # --- FIM DA SEÇÃO DO GRÁFICO DE BARRAS ---

    st.markdown("---")

    # --- Tabela Pivot ---
    pivot = pd.pivot_table(
        df_inad,
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
