# 📊 Dashboard Inadimplência
Este projeto exibe um painel interativo com informações sobre inadimplência, baseado em um arquivo Excel hospedado no GitHub.

## Funcionalidades
- Cálculo dinâmico de dias de atraso e classificação por faixa
- Classificação por exercício fiscal (ano)
- KPIs com valores totais inadimplentes e a vencer
- Quadro detalhado: Curto Prazo, Longo Prazo, Total Geral por exercício

## Como executar localmente
```bash
# Clone o repositório
git clone https://github.com/rodneirac/BIINADIMSPX.git
cd BIINADIMSPX

# (Opcional) Ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate  # Windows

# Instale dependências
pip install -r requirements.txt

# Rode o Streamlit
streamlit run dashboard_inadimplencia.py
```

## Deploy no Streamlit Cloud
1. Acesse https://streamlit.io/cloud
2. Conecte ao GitHub e escolha o repositório `BIINADIMSPX`
3. Escolha o arquivo `dashboard_inadimplencia.py`
4. Clique em **Deploy**

## Estrutura esperada
```
├── dashboard_inadimplencia.py
├── INADIMATUAL.XLSX
├── logo.png
├── requirements.txt
└── README.md
```