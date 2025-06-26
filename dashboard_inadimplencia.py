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

if st.button("🔄 Recarregar dados"):
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
    tot_venc = df_venc["Montante em moeda interna"].sum()
    tot_geral = tot_inad + tot_venc

    # NOVO: Soma dos valores onde FrmPgto é "H" ou "R"
    if "FrmPgto" in df_filt.columns:
        soma_frmpgto_HR = df_filt[df_filt["FrmPgto"].isin(["H", "R"])]["Montante em moeda interna"].sum()
    else:
        soma_frmpgto_HR = 0

    st.image(LOGO_URL, width=200)
    st.title("Dashboard de Análise de Inadimplência")
    st.markdown(f"**Exibindo dados para:** Região: `{regiao_sel}` | Divisão: `{divisao_sel}` | Exercício: `{exercicio_sel}`")

    st.markdown("### Indicadores Gerais")
    c1, c2, c3 = st.columns(3)
    c1.metric("Soma bruta planilha", f"R$ {soma_bruta_planilha:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c2.metric("Valor Total Inadimplente", f"R$ {tot_inad:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c3.metric("Venda Antecipada Inadimplente", f"R$ {soma_frmpgto_HR:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # --- NOVO EXPLORADOR DETALHADO SEM GRÁFICOS ---
    def fmt(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    with st.expander("🔍 Venda Antecipada Inadimplente – Detalhamento por Filial e Cliente"):
        if "FrmPgto" in df_filt.columns:
            df_antecipada = df_filt[df_filt["FrmPgto"].isin(["H", "R"])].copy()
            
            # Por Filial
            resumo_filial = (
                df_antecipada.groupby(col_div_princ)["Montante em moeda interna"]
                .sum()
                .reset_index()
                .rename(columns={col_div_princ: 'Filial', 'Montante em moeda interna': 'Venda Antecipada Inadimplente'})
                .sort_values(by='Venda Antecipada Inadimplente', ascending=False)
            )
            resumo_filial_fmt = resumo_filial.copy()
            resumo_filial_fmt['Venda Antecipada Inadimplente'] = resumo_filial_fmt['Venda Antecipada Inadimplente'].apply(fmt)
            st.markdown("**Por Filial:**")
            st.dataframe(resumo_filial_fmt, use_container_width=True)

            # Por Cliente
            if 'Nome 1' in df_antecipada.columns:
                resumo_cli = (
                    df_antecipada.groupby('Nome 1')["Montante em moeda interna"]
                    .sum()
                    .reset_index()
                    .rename(columns={'Nome 1': 'Cliente', 'Montante em moeda interna': 'Venda Antecipada Inadimplente'})
                    .sort_values(by='Venda Antecipada Inadimplente', ascending=False)
                )
                resumo_cli_fmt = resumo_cli.copy()
                resumo_cli_fmt['Venda Antecipada Inadimplente'] = resumo_cli_fmt['Venda Antecipada Inadimplente'].apply(fmt)
                st.markdown("**Por Cliente:**")
                st.dataframe(resumo_cli_fmt, use_container_width=True)
            else:
                st.info("Coluna 'Nome 1' não encontrada na base de dados para o detalhamento por cliente.")
        else:
            st.info("Coluna FrmPgto não encontrada.")

    st.markdown("### Quadro Detalhado de Inadimplência")
    pivot = pd.pivot_table(df_inad, index=["Exercicio", "Faixa"],
                           values="Montante em moeda interna", columns="Prazo",
                           aggfunc="sum", fill_value=0, margins=True, margins_name="Total Geral").reset_index()

    st.dataframe(
        pivot.style.format({col: fmt for col in pivot.columns if col not in ["Exercicio", "Faixa"]}),
        use_container_width=True
    )

    st.markdown("### Inadimplência por Exercício")
    df_outros = df_inad[df_inad['Exercicio'] != '2025']
    df_outros = df_outros.groupby('Exercicio')['Montante em moeda interna'].sum().reset_index()
    df_outros.rename(columns={'Exercicio': 'Categoria', 'Montante em moeda interna': 'Valor'}, inplace=True)

    df_2025 = df_inad[df_inad['Exercicio'] == '2025']
    df_2025 = df_2025.groupby('Faixa')['Montante em moeda interna'].sum().reset_index()
    df_2025 = df_2025[df_2025['Faixa'] != '']
    df_2025['Categoria'] = '2025 - ' + df_2025['Faixa']
    df_2025.rename(columns={'Montante em moeda interna': 'Valor'}, inplace=True)

    df_graf = pd.concat([df_outros, df_2025[['Categoria', 'Valor']]], ignore_index=True)

    if not df_graf.empty:
        color_map = {cat: '#EA4335' for cat in df_outros['Categoria'].unique()}
        cores_2025 = ['#FFC107', '#FF9800', '#F57C00']
        categorias_2025 = sorted(df_2025['Categoria'].unique())
        for i, cat in enumerate(categorias_2025):
            color_map[cat] = cores_2025[i % len(cores_2025)]

        fig_bar = px.bar(df_graf, x='Categoria', y='Valor',
                         text=df_graf['Valor'].apply(lambda x: f'{x/1_000_000:,.1f} M'),
                         color='Categoria', color_discrete_map=color_map)
        fig_bar.update_layout(title='Detalhe por Exercício e Faixa (2025)', showlegend=False, height=400)
        fig_bar.update_traces(textposition='outside')
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Sem dados para gerar o gráfico de barras neste filtro.")

    st.markdown("### Inadimplência por Região (3D Simulado)")
    df_pie = df_inad.groupby('Região')['Montante em moeda interna'].sum().reset_index()
    fig_pie = px.pie(df_pie, names='Região', values='Montante em moeda interna',
                     title='Participação por Região', hole=0.2)
    fig_pie.update_traces(textposition='inside', textinfo='percent+label', pull=[0.05]*len(df_pie))
    fig_pie.update_layout(title_font_size=16, height=600, width=800)
    st.plotly_chart(fig_pie, use_container_width=True)

    with st.expander("Clique para ver o Resumo por Divisão"):
        resumo = df_inad.groupby(col_div_princ)['Montante em moeda interna'].sum().reset_index()
        resumo.rename(columns={col_div_princ: 'Divisão', 'Montante em moeda interna': 'Valor Inadimplente'}, inplace=True)
        resumo = resumo.sort_values(by='Valor Inadimplente', ascending=False)
        resumo['Valor Inadimplente'] = resumo['Valor Inadimplente'].apply(fmt)
        st.dataframe(resumo, use_container_width=True)

    # ------ NOVO BLOCO GRÁFICO AJUSTADO ---------
    with st.expander("Clique para ver o Resumo por Cliente"):
        if 'Nome 1' in df_inad.columns:
            resumo_cli = df_inad.groupby('Nome 1')['Montante em moeda interna'].sum().reset_index()
            resumo_cli.rename(columns={'Nome 1': 'Cliente', 'Montante em moeda interna': 'Valor Inadimplente'}, inplace=True)
            resumo_cli['% do Total'] = resumo_cli['Valor Inadimplente'] / tot_inad * 100
            resumo_cli = resumo_cli.sort_values(by='Valor Inadimplente', ascending=False)
            resumo_cli_fmt = resumo_cli.copy()
            resumo_cli_fmt['Valor Inadimplente'] = resumo_cli_fmt['Valor Inadimplente'].apply(fmt)
            resumo_cli_fmt['% do Total'] = resumo_cli_fmt['% do Total'].apply(lambda x: f"{x:.1f}%")
            st.dataframe(resumo_cli_fmt, use_container_width=True)

            # Top 10 Gráfico em azul-verde e label M/K
            top_n = resumo_cli.head(10)
            def label_mk(valor):
                if valor >= 1_000_000:
                    return f"{valor/1_000_000:.1f}M"
                elif valor >= 1_000:
                    return f"{valor/1_000:.1f}K"
                else:
                    return f"{valor:,.0f}"

            # Cores azul-verde
            colors = [
                "#0099cc", "#33cc99", "#00b386", "#00cc99", "#33cccc",
                "#009966", "#00cc99", "#00b386", "#33cc99", "#0099cc"
            ]
            fig_cli = px.bar(
                top_n.sort_values('Valor Inadimplente'),
                x='Valor Inadimplente',
                y='Cliente',
                orientation='h',
                text=top_n['Valor Inadimplente'].apply(label_mk),
                color_discrete_sequence=colors
            )
            fig_cli.update_layout(
                height=500,
                yaxis_title='',
                xaxis_title='Valor Inadimplente',
                showlegend=False,
                title='Top 10 Clientes Inadimplentes'
            )
            fig_cli.update_traces(textposition='outside')
            st.plotly_chart(fig_cli, use_container_width=True)
        else:
            st.warning("Coluna 'Nome 1' não encontrada na base de dados.")

else:
    st.error("Dados não disponíveis.")
