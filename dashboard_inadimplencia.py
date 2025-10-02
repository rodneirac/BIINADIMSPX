import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO
import time

st.set_page_config(layout="wide", page_title="Dashboard Inadimplência")

# --- CONFIGURAÇÃO DAS FONTES DE DADOS ---
OWNER = "rodneirac"
REPO = "BIINADIMSPX"
ARQUIVO_REGIAO = "REGIAO.xlsx"
URL_REGIAO = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/{ARQUIVO_REGIAO}"
LOGO_URL = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/logo.png"

ID_PLANILHA_GOOGLE = "1APYc9xkFeFkYuRRuhfi2DhJWw2RA9ddx"
URL_DADOS = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA_GOOGLE}/export?format=xlsx"

ID_PLANILHA_HIST = "1xxLuMIudxIIvqe_9so3I3LYiEubvaRIM"
URL_HIST = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA_HIST}/export?format=xlsx"
# --- FIM DA CONFIGURAÇÃO ---

def label_mk(valor):
    if valor >= 1_000_000:
        return f"{valor/1_000_000:.1f}M"
    elif valor >= 1_000:
        return f"{valor/1_000:.1f}K"
    else:
        return f"{valor:,.0f}"

if 'last_reload' not in st.session_state:
    st.session_state['last_reload'] = None

if 'show_last_10_days' not in st.session_state:
    st.session_state['show_last_10_days'] = False

@st.cache_data(ttl=3600)
def load_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        df = pd.read_excel(BytesIO(response.content), engine="openpyxl")
        df["Data do documento"] = pd.to_datetime(df["Data do documento"], errors="coerce")
        df["Vencimento líquido"] = pd.to_datetime(df["Vencimento líquido"], errors="coerce")
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_region_data(url):
    response = requests.get(url)
    df = pd.read_excel(BytesIO(response.content), engine="openpyxl")
    return df

@st.cache_data(ttl=3600)
def load_hist_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        df = pd.read_excel(BytesIO(response.content), engine="openpyxl")
        df["Data do documento"] = pd.to_datetime(df["Data do documento"], errors="coerce")
        df["Vencimento líquido"] = pd.to_datetime(df["Vencimento líquido"], errors="coerce")
        return df
    except:
        return pd.DataFrame()

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
    ano_atual_str = str(datetime.now().year)
    if exercicio == ano_atual_str:
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
    
    divisoes_sem_regiao = df_merged[df_merged['Região'].isnull()][col_div_princ].unique().tolist()
    
    soma_apos_merge = df_merged["Montante em moeda interna"].sum()
    if abs(soma_bruta_planilha - soma_apos_merge) > 1:
        st.warning(f"Soma após merge: R$ {soma_apos_merge:,.2f} difere do bruto: R$ {soma_bruta_planilha:,.2f}")

    df_merged["Exercicio"] = df_merged["Data do documento"].apply(classifica_exercicio)
    
    lista_exercicios = sorted(df_merged['Exercicio'].unique())
    lista_divisoes = sorted(df_merged[col_div_princ].unique())

    st.sidebar.title("Filtros")
    regiao_sel = st.sidebar.selectbox("Selecione a Região:", ["TODAS AS REGIÕES"] + sorted(df_merged['Região'].fillna('Não definida').unique()))
    
    with st.sidebar.expander("Selecione a(s) Divisão(ões)", expanded=False):
        divisao_keys = [f"divisao_{div}" for div in lista_divisoes]
        for key in divisao_keys:
            if key not in st.session_state:
                st.session_state[key] = True

        def marcar_todas_divisoes():
            for key in divisao_keys:
                st.session_state[key] = True

        def desmarcar_todas_divisoes():
            for key in divisao_keys:
                st.session_state[key] = False

        col1_div, col2_div = st.columns(2)
        col1_div.button("Marcar Todas", on_click=marcar_todas_divisoes, use_container_width=True, key='marcar_div')
        col2_div.button("Desmarcar Todas", on_click=desmarcar_todas_divisoes, use_container_width=True, key='desmarcar_div')

        for divisao in lista_divisoes:
            st.checkbox(divisao, key=f"divisao_{divisao}")

    divisao_sel = [divisao for divisao in lista_divisoes if st.session_state.get(f"divisao_{divisao}", True)]
    
    with st.sidebar.expander("Selecione o(s) Exercício(s)", expanded=False):
        exercicio_keys = [f"exercicio_{ex}" for ex in lista_exercicios]
        for key in exercicio_keys:
            if key not in st.session_state:
                st.session_state[key] = True

        def marcar_todos_exercicios():
            for key in exercicio_keys:
                st.session_state[key] = True

        def desmarcar_todos_exercicios():
            for key in exercicio_keys:
                st.session_state[key] = False

        col1_ex, col2_ex = st.columns(2)
        col1_ex.button("Marcar Todos", on_click=marcar_todos_exercicios, use_container_width=True, key='marcar_ex')
        col2_ex.button("Desmarcar Todos", on_click=desmarcar_todos_exercicios, use_container_width=True, key='desmarcar_ex')

        for exercicio in lista_exercicios:
            st.checkbox(exercicio, key=f"exercicio_{exercicio}")

    exercicio_sel = [exercicio for exercicio in lista_exercicios if st.session_state.get(f"exercicio_{exercicio}", True)]

    df_merged['Região'].fillna('Não definida', inplace=True)
    df_filt = df_merged.copy()

    if regiao_sel != "TODAS AS REGIÕES":
        df_filt = df_filt[df_filt['Região'] == regiao_sel]
    
    if divisao_sel:
        df_filt = df_filt[df_filt[col_div_princ].isin(divisao_sel)]
    else:
        df_filt = df_filt.iloc[0:0]
    
    if exercicio_sel:
        df_filt = df_filt[df_filt['Exercicio'].isin(exercicio_sel)]
    else: 
        df_filt = df_filt.iloc[0:0]

    hoje = datetime.now()
    df_filt["Dias de atraso"] = (hoje - df_filt["Vencimento líquido"]).dt.days

    if st.session_state.get('show_last_10_days', False):
        st.success("Filtro aplicado: Exibindo apenas inadimplência com vencimento nos últimos 10 dias.")
        df_filt = df_filt[df_filt["Dias de atraso"].between(1, 10)]

    df_filt["Faixa"] = df_filt.apply(lambda row: classifica_faixa(row["Exercicio"], row["Dias de atraso"]), axis=1)
    df_filt["Prazo"] = df_filt["Dias de atraso"].apply(classifica_prazo)

    df_inad = df_filt[df_filt["Dias de atraso"] >= 1].copy()

    regra_tipo_cobranca = {
        'COBRANÇA JURÍDICA':  ['060', '60', '005', '5', '888'],
        'COBRANÇA BANCÁRIA':   ['237', '341C', '033', '001'],
        'CARTEIRA':           ['999'],
        'PERMUTA':            ['096', '96'],
        'COBRANÇA PROTESTADO': ['087', '87'],
        'ANÁLISE PROCESSO':   ['007', '7', '020', '20', '022', '22'],
        'COBR. TERCERIZADA':  ['899'],
        'DIVERSOS':           ['991', '026', '26', '990', '006', '6', '']
    }
    
    if not df_inad.empty:
        mapa_banco_para_tipo = {banco: tipo for tipo, bancos in regra_tipo_cobranca.items() for banco in bancos}
        df_inad['Tipo de Cobrança Desc'] = df_inad['Banco da empresa'].astype(str).map(mapa_banco_para_tipo)
        df_inad['Tipo de Cobrança Desc'].fillna('DIVERSOS', inplace=True)

        resumo_cli_status = df_inad.groupby('Nome 1').agg(
            Tipos_de_Cobranca=('Tipo de Cobrança Desc', lambda x: ', '.join(x.unique()))
        ).reset_index()

        ordem_gravidade = [
            'COBRANÇA JURÍDICA', 'COBRANÇA PROTESTADO', 'ANÁLISE PROCESSO', 'COBR. TERCERIZADA',
            'COBRANÇA BANCÁRIA', 'CARTEIRA', 'PERMUTA', 'DIVERSOS'
        ]
        mapa_gravidade_simbolo = {
            'COBRANÇA JURÍDICA': '🔴', 'COBRANÇA PROTESTADO': '🔴', 'ANÁLISE PROCESSO': '🟡', 
            'COBR. TERCERIZADA': '🟡', 'COBRANÇA BANCÁRIA': '🔵', 'CARTEIRA': '🔵', 'PERMUTA': '⚪', 'DIVERSOS': '⚪'
        }

        def definir_gravidade(tipos_string):
            for tipo in ordem_gravidade:
                if tipo in tipos_string:
                    return mapa_gravidade_simbolo[tipo]
            return '⚪'

        resumo_cli_status['Status'] = resumo_cli_status['Tipos_de_Cobranca'].apply(definir_gravidade)
        mapa_cliente_status = pd.Series(resumo_cli_status.Status.values, index=resumo_cli_status['Nome 1']).to_dict()
        df_inad['Status'] = df_inad['Nome 1'].map(mapa_cliente_status)

    lista_status = ['🔴', '🟡', '🔵', '⚪']
    with st.sidebar.expander("Selecione o(s) Status", expanded=False):
        status_keys = [f"status_{s}" for s in lista_status]
        for key in status_keys:
            if key not in st.session_state:
                st.session_state[key] = True

        def marcar_todos_status():
            for key in status_keys:
                st.session_state[key] = True

        def desmarcar_todos_status():
            for key in status_keys:
                st.session_state[key] = False

        col1_stat, col2_stat = st.columns(2)
        col1_stat.button("Marcar Todos", on_click=marcar_todos_status, use_container_width=True, key='marcar_stat')
        col2_stat.button("Desmarcar Todos", on_click=desmarcar_todos_status, use_container_width=True, key='desmarcar_stat')
        
        for status in lista_status:
            st.checkbox(status, key=f"status_{status}")

    status_sel = [status for status in lista_status if st.session_state.get(f"status_{status}", True)]
    
    if not df_inad.empty and status_sel:
        df_inad = df_inad[df_inad['Status'].isin(status_sel)]

    st.sidebar.markdown("---")
    st.sidebar.markdown("#### Atualização de Dados")
    if st.sidebar.button("🔄 Recarregar dados"):
        st.cache_data.clear()
        st.session_state['last_reload'] = time.strftime("%d/%m/%Y %H:%M:%S")
        st.session_state['show_last_10_days'] = False
        st.rerun()

    if st.sidebar.button("🗓️ Inadimplentes dos últimos 10 dias"):
        st.session_state['show_last_10_days'] = True
        st.rerun()

    if st.sidebar.button("🧹 Limpar Filtro de Data"):
        st.session_state['show_last_10_days'] = False
        st.rerun()

    st.sidebar.caption("Clique para buscar os dados mais recentes.")
    if st.session_state['last_reload']:
        st.sidebar.success(f"Dados recarregados em {st.session_state['last_reload']}")
    
    tot_inad = df_inad["Montante em moeda interna"].sum()
    if "FrmPgto" in df_filt.columns:
        soma_frmpgto_HR = df_inad[df_inad["FrmPgto"].isin(["H", "R"])]["Montante em moeda interna"].sum()
    else:
        soma_frmpgto_HR = 0

    st.image(LOGO_URL, width=200)
    st.title("Dashboard de Análise de Inadimplência")
    
    texto_divisao = "Todas" if len(divisao_sel) == len(lista_divisoes) else ', '.join(divisao_sel) if divisao_sel else "Nenhuma"
    texto_exercicio = "Todos" if len(exercicio_sel) == len(lista_exercicios) else ', '.join(exercicio_sel) if exercicio_sel else "Nenhum"
    st.markdown(f"**Exibindo dados para:** Região: {regiao_sel} | Divisão(ões): {texto_divisao} | Exercício(s): {texto_exercicio}")

    if divisoes_sem_regiao:
        st.warning(f"""
        **Atenção: As seguintes divisões não foram encontradas no arquivo de mapeamento e foram agrupadas como 'Não definida':**
        
        {', '.join(divisoes_sem_regiao)}
        
        *Para corrigir, adicione estas divisões ao seu arquivo `REGIAO.xlsx` no GitHub.*
        """)

    st.markdown("### Indicadores Gerais")
    c1, c2, c3 = st.columns(3)
    c1.metric("Vlr Total Inadimplente", f"R$ {soma_bruta_planilha:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c2.metric("Vlr Inadimplente (Filtro Atual)", f"R$ {tot_inad:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c3.metric("Venda Antecipada Inadimplente", f"R$ {soma_frmpgto_HR:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    def fmt(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    with st.expander("🔍 Venda Antecipada Inadimplente – Detalhamento por Filial e Cliente"):
        if "FrmPgto" in df_inad.columns:
            df_antecipada = df_inad[df_inad["FrmPgto"].isin(["H", "R"])].copy()
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
    if not df_inad.empty:
        pivot = pd.pivot_table(df_inad, index=["Exercicio", "Faixa"],
                                values="Montante em moeda interna", columns="Prazo",
                                aggfunc="sum", fill_value=0, margins=True, margins_name="Total Geral").reset_index()
        st.dataframe(
            pivot.style.format({col: fmt for col in pivot.columns if col not in ["Exercicio", "Faixa"]}),
            use_container_width=True
        )
    else:
        st.warning("Nenhum dado de inadimplência encontrado para os filtros selecionados.")


    st.markdown("### Inadimplência por Exercício")
    ano_atual_str = str(datetime.now().year)
    
    df_outros = df_inad[df_inad['Exercicio'] != ano_atual_str]
    df_outros = df_outros.groupby('Exercicio')['Montante em moeda interna'].sum().reset_index()
    df_outros.rename(columns={'Exercicio': 'Categoria', 'Montante em moeda interna': 'Valor'}, inplace=True)

    df_2025 = df_inad[df_inad['Exercicio'] == ano_atual_str]
    
    if not df_2025.empty:
        df_2025 = df_2025.groupby('Faixa')['Montante em moeda interna'].sum().reset_index()
        df_2025 = df_2025[df_2025['Faixa'] != '']
        df_2025['Categoria'] = f'{ano_atual_str} - ' + df_2025['Faixa'].astype(str)
        df_2025.rename(columns={'Montante em moeda interna': 'Valor'}, inplace=True)
        df_graf = pd.concat([df_outros, df_2025[['Categoria', 'Valor']]], ignore_index=True)
    else:
        df_graf = df_outros

    if not df_graf.empty:
        color_map = {cat: '#EA4335' for cat in df_outros['Categoria'].unique()}
        
        if not df_2025.empty:
            cores_2025 = ['#FFC107', '#FF9800', '#F57C00']
            categorias_2025 = sorted(df_2025['Categoria'].unique())
            for i, cat in enumerate(categorias_2025):
                color_map[cat] = cores_2025[i % len(cores_2025)]

        fig_bar = px.bar(df_graf, x='Categoria', y='Valor',
                            text=df_graf['Valor'].apply(lambda x: f'{x/1_000_000:,.1f} M' if x >= 1_000_000 else f'{x/1_000:,.1f} K'),
                            color='Categoria', color_discrete_map=color_map)
        fig_bar.update_layout(title=f'Detalhe por Exercício e Faixa ({ano_atual_str})', showlegend=False, height=400)
        fig_bar.update_traces(textposition='outside')
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Sem dados para gerar o gráfico de barras neste filtro.")

    df_filt['Banco da empresa'] = df_filt['Banco da empresa'].fillna('').astype(str).str.strip()
    resultado = []
    for tipo, bancos in regra_tipo_cobranca.items():
        if tipo == 'DIVERSOS':
            mask = df_filt['Banco da empresa'].isin(bancos) | (df_filt['Banco da empresa'] == '')
        else:
            mask = df_filt['Banco da empresa'].isin(bancos)
        soma = df_filt.loc[mask, 'Montante em moeda interna'].sum()
        resultado.append({'Tipo de Cobrança': tipo, 'Valor': soma})
    df_tipo_cobranca = pd.DataFrame(resultado)
    df_tipo_cobranca = df_tipo_cobranca.sort_values('Valor', ascending=False)
    df_tipo_cobranca['label_mk'] = df_tipo_cobranca['Valor'].apply(label_mk)
    fig_cobranca = px.bar(
        df_tipo_cobranca,
        x='Valor',
        y='Tipo de Cobrança',
        orientation='h',
        text='label_mk',
        color_discrete_sequence=['#800020']
    )
    fig_cobranca.update_layout(
        showlegend=False,
        height=400,
        title='',
        xaxis_title="Valor (R$)",
        yaxis_title="Tipo de Cobrança"
    )
    fig_cobranca.update_traces(textposition='outside')
    st.markdown("## Inadimplência por Tipo de Cobrança")
    st.plotly_chart(fig_cobranca, use_container_width=True)

    st.markdown("### Inadimplência por Região (3D Simulado)")
    df_pie = df_inad.groupby('Região')['Montante em moeda interna'].sum().reset_index()
    if not df_pie.empty:
      fig_pie = px.pie(df_pie, names='Região', values='Montante em moeda interna',
                        title='Participação por Região', hole=0.2)
      fig_pie.update_traces(textposition='inside', textinfo='percent+label', pull=[0.05]*len(df_pie))
      fig_pie.update_layout(title_font_size=16, height=600, width=800)
      st.plotly_chart(fig_pie, use_container_width=True)
    else:
      st.info("Sem dados para o gráfico de participação por Região.")

    with st.expander("Clique para ver o Resumo por Divisão"):
        resumo = df_inad.groupby(col_div_princ)['Montante em moeda interna'].sum().reset_index()
        resumo.rename(columns={col_div_princ: 'Divisão', 'Montante em moeda interna': 'Valor Inadimplente'}, inplace=True)
        resumo = resumo.sort_values(by='Valor Inadimplente', ascending=False)
        resumo['Valor Inadimplente'] = resumo['Valor Inadimplente'].apply(fmt)
        st.dataframe(resumo, use_container_width=True, hide_index=True)

    with st.expander("Clique para ver o Resumo por Cliente"):
        if 'Nome 1' in df_inad.columns and not df_inad.empty:
            
            resumo_cli = df_inad.groupby('Nome 1').agg(
                Valor_Inadimplente=('Montante em moeda interna', 'sum'),
                Tipos_de_Cobranca=('Tipo de Cobrança Desc', lambda x: ', '.join(x.unique())),
                Status=('Status', 'first') # Pega o status que já calculamos
            ).reset_index()

            resumo_cli.rename(columns={'Nome 1': 'Cliente'}, inplace=True)
            
            if tot_inad > 0:
                resumo_cli['% do Total'] = resumo_cli['Valor_Inadimplente'] / tot_inad * 100
            else:
                resumo_cli['% do Total'] = 0
                
            resumo_cli = resumo_cli.sort_values(by='Valor_Inadimplente', ascending=False)
            
            resumo_cli_fmt = resumo_cli.copy()
            resumo_cli_fmt['Valor Inadimplente'] = resumo_cli_fmt['Valor_Inadimplente'].apply(fmt)
            resumo_cli_fmt['% do Total'] = resumo_cli_fmt['% do Total'].apply(lambda x: f"{x:.2f}%")
            resumo_cli_fmt.rename(columns={'Tipos_de_Cobranca': 'Tipos de Cobrança'}, inplace=True)
            
            st.dataframe(
                resumo_cli_fmt[['Status', 'Cliente', 'Valor Inadimplente', 'Tipos de Cobrança', '% do Total']], 
                use_container_width=True,
                hide_index=True
            )
            
            top_n = resumo_cli.head(10).sort_values('Valor_Inadimplente')
            top_n['label_mk'] = top_n['Valor_Inadimplente'].apply(label_mk)
            fig_cli = px.bar(
                top_n,
                x='Valor_Inadimplente',
                y='Cliente',
                orientation='h',
                text='label_mk',
                color_discrete_sequence=["#0074D9"]
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
            
        elif 'Nome 1' not in df_inad.columns:
            st.warning("Coluna 'Nome 1' não encontrada na base de dados.")
        else:
            st.info("Nenhum cliente inadimplente para exibir.")


    # ==== GRAFICOS DE GAUGE USANDO HISTÓRICO DO GOOGLE DRIVE ====
    def gauge_chart(percent, title):
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = percent,
            number = {'suffix': "%"},
            title = {'text': title},
            gauge = {
                'axis': {'range': [0, 100]},
                'bar': {'color': "#24292F"},
                'steps' : [
                    {'range': [0, 50], 'color': "#B03A2E"},
                    {'range': [50, 80], 'color': "#F7DC6F"},
                    {'range': [80, 100], 'color': "#1ABC9C"},
                ],
            }
        ))
        fig.update_layout(margin=dict(l=20, r=20, t=60, b=20), height=300)
        return fig

    if not df_inad.empty:
      df_hist = load_hist_data(URL_HIST)
      valor_quitado = 0
      valor_novos_inad = 0
      perc_recuperado = 0
      perc_novos_inad = 0

      if not df_hist.empty:
          id_cols = ["Tipo de documento", "Referência", "Conta", "Divisão", "Banco da empresa", "Vencimento líquido"]
          df_inad["ID"] = df_inad[id_cols].astype(str).agg("_".join, axis=1)
          if "ID" not in df_hist.columns:
              df_hist["ID"] = df_hist[id_cols].astype(str).agg("_".join, axis=1)
          
          antigos = set(df_hist["ID"])
          novos = set(df_inad["ID"])
          quitados = antigos - novos
          novos_inad = novos - antigos
          valor_quitado = df_hist[df_hist["ID"].isin(quitados)]["Montante em moeda interna"].sum()
          valor_novos_inad = df_inad[df_inad["ID"].isin(novos_inad)]["Montante em moeda interna"].sum()
          total_antigo = df_hist["Montante em moeda interna"].sum()
          total_novo = df_inad["Montante em moeda interna"].sum()
          perc_recuperado = (valor_quitado / total_antigo * 100) if total_antigo else 0
          perc_novos_inad = (valor_novos_inad / total_novo * 100) if total_novo else 0

      st.markdown("### Indicadores Dinâmicos de Inadimplência (Comparativo com a última versão dos dados)")
      c1, c2 = st.columns(2)
      with c1:
          st.plotly_chart(gauge_chart(perc_recuperado, "Recuperação de Inadimplentes"), use_container_width=True)
          st.markdown(f"**Valor Recuperado:** R$ {valor_quitado:,.2f}")
      with c2:
          st.plotly_chart(gauge_chart(perc_novos_inad, "Novos Inadimplentes"), use_container_width=True)
          st.markdown(f"**Valor Novos Inadimplentes:** R$ {valor_novos_inad:,.2f}")
