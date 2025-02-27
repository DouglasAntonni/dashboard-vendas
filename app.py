import streamlit as st 
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Dashboard de Vendas", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
html, body {
    font-family: 'Roboto', sans-serif;
    scroll-behavior: smooth;
    background-color: #121212;
    color: #e0e0e0;
}
.reportview-container {
    background: linear-gradient(135deg, #232526, #414345);
    padding: 2rem;
    transition: background-color 0.3s ease;
}
.sidebar .sidebar-content {
    background: #1e1e1e;
    padding: 1rem;
    border-right: 1px solid #414345;
    border-radius: 8px;
    box-shadow: 1px 1px 5px rgba(0,0,0,0.5);
}
h1, h2, h3, h4, h5, h6 {
    color: #ffffff;
    font-weight: 700;
}
h2, h3 {
    border-bottom: 2px solid #ffffff;
    padding-bottom: 0.3rem;
}
[data-testid="stMetric"] {
    background: #FF6347;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    transition: transform 0.2s ease-in-out;
    padding: 1rem;
    color: #fff;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-3px);
}
div.stButton > button {
    background-color: #FF6347;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    cursor: pointer;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    transition: background-color 0.3s ease, transform 0.2s ease;
}
div.stButton > button:hover {
    background-color: #FF4500;
    transform: translateY(-2px);
}
@media (max-width: 768px) {
    .reportview-container {
         padding: 1rem;
    }
    h1 {
         font-size: 2rem;
         text-align: center;
    }
    [data-testid="stMetric"] {
         font-size: 0.9rem;
         padding: 0.5rem;
    }
}
</style>
""", unsafe_allow_html=True)

# Função de carregamento dos dados
@st.cache_data
def load_data():
    try:
        df_vendas1 = pd.read_excel("Vendas.xlsx")
        df_vendas2 = pd.read_excel("Vendas_2T.xlsx")
        df_vendas = pd.concat([df_vendas1, df_vendas2], ignore_index=True)
        df_vendas["Date"] = pd.to_datetime(df_vendas["Date"], errors="coerce")
        df_vendas["mes"] = df_vendas["Date"].dt.strftime("%Y-%m")
        df_vendas["faturamento"] = df_vendas["Quantity"] * df_vendas["Price"]
        
        df_consultores = pd.read_excel("Consultores.xlsx")
        if {"IdSeller", "Seller"}.issubset(df_consultores.columns):
            df_vendas = df_vendas.merge(df_consultores[["IdSeller", "Seller"]], on="IdSeller", how="left")
        else:
            st.warning("Colunas 'IdSeller' e/ou 'Seller' não encontradas em Consultores.xlsx")
        
        df_lojas = pd.read_excel("Lojas.xlsx")
        if {"IdStore", "Store"}.issubset(df_lojas.columns):
            df_vendas = df_vendas.merge(df_lojas[["IdStore", "Store"]], on="IdStore", how="left")
        else:
            st.warning("Colunas 'IdStore' e/ou 'Store' não encontradas em Lojas.xlsx")
        
        df_metas = pd.read_excel("Metas.xlsx")
        df_metas["Date"] = pd.to_datetime(df_metas["Date"], errors="coerce")
        df_metas["mes"] = df_metas["Date"].dt.strftime("%Y-%m")
        
    except Exception as e:
        st.error(f"Erro ao carregar arquivos: {e}")
        return None, None, None, None
    return df_vendas, df_consultores, df_lojas, df_metas

with st.spinner("Carregando dados..."):
    df_vendas, df_consultores, df_lojas, df_metas = load_data()
if df_vendas is None:
    st.stop()

# Cria dicionário de metas e associa à tabela de vendas
metas_dict = {}
if df_metas is not None and not df_metas.empty:
    metas_dict = df_metas.groupby(["IdStore", "mes"])["RevenueTarget"].sum().to_dict()
df_vendas["meta"] = df_vendas.set_index(["IdStore", "mes"]).index.map(lambda x: metas_dict.get(x, 0))

# Sidebar com filtros
with st.sidebar:
    st.markdown("## Painel de Filtros")
    with st.expander("Filtros Avançados", expanded=True):
        faturamento_filtrado = df_vendas["faturamento"].sum()
        meta_total_filtrada = df_vendas["meta"].sum() if "meta" in df_vendas.columns else 0
        percentual_meta = (faturamento_filtrado / meta_total_filtrada * 100) if meta_total_filtrada > 0 else 0
        st.progress(min(percentual_meta / 100, 1.0))
        st.caption(f"Atingimento da Meta: {percentual_meta:.2f}%")
        
        col1, col2 = st.columns(2)
        with col1:
            selected_lojas = st.selectbox("Selecione a Loja", 
                                          options=["Todas"] + sorted(df_vendas["Store"].dropna().unique()),
                                          key="selected_lojas")
        with col2:
            selected_meses = st.selectbox("Selecione o Mês", 
                                          options=["Todos"] + sorted(df_vendas["mes"].dropna().unique()),
                                          key="selected_meses")
        
        if st.session_state.get("selected_lojas", "Todas") != "Todas":
            consultores_disponiveis = sorted(df_vendas[df_vendas["Store"] == st.session_state["selected_lojas"]]["Seller"].dropna().unique())
        else:
            consultores_disponiveis = sorted(df_vendas["Seller"].dropna().unique())
            
        selected_consultor = st.selectbox("Selecione o Consultor", 
                                          options=["Todos"] + consultores_disponiveis,
                                          key="selected_consultor")
        
        min_date = df_vendas["Date"].min().date()
        max_date = df_vendas["Date"].max().date()
        selected_date_range = st.date_input("Período", [min_date, max_date],
                                            key="selected_date_range")
        
        search_term = st.text_input("Busca rápida", placeholder="Digite loja ou consultor...", 
                                    key="search_term")

# Aplicação dos filtros com máscara booleana para maior performance
with st.spinner("Aplicando Filtros..."):
    lojas = st.session_state.get("selected_lojas", "Todas")
    meses = st.session_state.get("selected_meses", "Todos")
    consultor = st.session_state.get("selected_consultor", "Todos")
    date_range = st.session_state.get("selected_date_range", [min_date, max_date])
    termo_busca = st.session_state.get("search_term", "")
    
    mask = pd.Series(True, index=df_vendas.index)
    if lojas != "Todas":
        mask &= (df_vendas["Store"] == lojas)
    if meses != "Todos":
        mask &= (df_vendas["mes"] == meses)
    if consultor != "Todos":
        mask &= (df_vendas["Seller"] == consultor)
    if isinstance(date_range, list) and len(date_range) == 2:
        start_date, end_date = date_range
        mask &= (df_vendas["Date"].dt.date >= start_date) & (df_vendas["Date"].dt.date <= end_date)
    if termo_busca:
        mask &= (df_vendas["Seller"].str.contains(termo_busca, case=False, na=False) |
                 df_vendas["Store"].str.contains(termo_busca, case=False, na=False))
    df_filtered = df_vendas[mask]
    if df_filtered.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")

# Cabeçalho e principais métricas
st.title("Dashboard de Vendas")
st.subheader("Análise de Faturamento, Evolução Mensal, Metas e Outras Métricas")
total_faturamento = df_filtered["faturamento"].sum()
total_vendas = df_filtered.shape[0]
total_quantidade = df_filtered["Quantity"].sum()
ticket_medio = total_faturamento / total_vendas if total_vendas > 0 else 0
if not df_filtered.empty:
    df_meta_filtered = df_filtered.groupby(["Store", "mes"]).agg(meta=("meta", "max")).reset_index()
    meta_total = df_meta_filtered["meta"].sum()
else:
    meta_total = 0
atingimento_perc = (total_faturamento / meta_total * 100) if meta_total > 0 else None

st.markdown("## Principais Métricas")
col1, col2, col3 = st.columns(3)
col1.metric("Faturamento Total", f"R$ {total_faturamento:,.2f}")
col2.metric("Número de Vendas", f"{total_vendas}")
col3.metric("Quantidade Vendida", f"{total_quantidade}")
col4, col5, col6 = st.columns(3)
col4.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")
col5.metric("Meta Total", f"R$ {meta_total:,.2f}")
col6.metric("Atingimento", f"{atingimento_perc:.2f}%" if atingimento_perc is not None else "N/A")

# Métricas adicionais e rankings
st.markdown("## Métricas Adicionais")
col7, col8, col9 = st.columns(3)
avg_quantity = total_quantidade / total_vendas if total_vendas > 0 else 0
store_revenue = df_filtered.groupby("Store")["faturamento"].sum().reset_index()
if not store_revenue.empty:
    best_store_row = store_revenue.loc[store_revenue["faturamento"].idxmax()]
    best_store_name = best_store_row["Store"]
    best_store_value = best_store_row["faturamento"]
else:
    best_store_name = "N/A"
    best_store_value = 0
seller_revenue = df_filtered.groupby("Seller")["faturamento"].sum().reset_index()
if not seller_revenue.empty:
    best_seller_row = seller_revenue.loc[seller_revenue["faturamento"].idxmax()]
    best_seller_name = best_seller_row["Seller"]
    best_seller_value = best_seller_row["faturamento"]
else:
    best_seller_name = "N/A"
    best_seller_value = 0

col7.metric("Média Qtd/Venda", f"{avg_quantity:.2f}")
col8.metric("Melhor Loja", f"{best_store_name} (R$ {best_store_value:,.2f})")
col9.metric("Melhor Consultor", f"{best_seller_name} (R$ {best_seller_value:,.2f})")

# Gráfico: Evolução do Faturamento Mensal
monthly_rev = df_filtered.groupby("mes")["faturamento"].sum().reset_index().sort_values("mes")
fig = px.line(monthly_rev, x="mes", y="faturamento", markers=True,
              title="Evolução do Faturamento Mensal",
              labels={"mes": "Mês/Ano", "faturamento": "Faturamento (R$)"},
              color_discrete_sequence=["#3498db"])
fig.update_traces(line=dict(color="#3498db"), marker=dict(color="#3498db"))
fig.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=50, b=20))
st.plotly_chart(fig, use_container_width=True)

# Gráfico: Faturamento por Loja
store_rev = df_filtered.groupby("Store")["faturamento"].sum().reset_index().sort_values("faturamento", ascending=False)
fig_store = px.bar(store_rev, x="Store", y="faturamento",
                   title="Faturamento por Loja",
                   labels={"faturamento": "Faturamento (R$)"},
                   color_discrete_sequence=["#2ecc71"])
fig_store.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=50, b=20))
st.plotly_chart(fig_store, use_container_width=True)

# Gráfico: Faturamento por Consultor
seller_rev = df_filtered.groupby("Seller")["faturamento"].sum().reset_index().sort_values("faturamento", ascending=False)
fig_seller = px.bar(seller_rev, x="Seller", y="faturamento",
                    title="Faturamento por Consultor",
                    labels={"faturamento": "Faturamento (R$)"},
                    color_discrete_sequence=["#e74c3c"])
fig_seller.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=50, b=20))
st.plotly_chart(fig_seller, use_container_width=True)

# Gráfico: Distribuição de Quantidade Vendida
fig_hist = px.histogram(df_filtered, x="Quantity", nbins=30,
                        title="Distribuição de Quantidade Vendida",
                        labels={"Quantity": "Quantidade"},
                        color_discrete_sequence=["#9b59b6"])
fig_hist.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=50, b=20))
st.plotly_chart(fig_hist, use_container_width=True)

# Comparação: Faturamento Real x Meta por Loja (por mês)
st.subheader("Comparação: Faturamento Real x Meta por Loja (por mês)")
df_resumo = df_filtered.groupby(["Store", "mes"]).agg(
    faturamento_real=("faturamento", "sum"),
    meta=("meta", "max")
).reset_index()
if not df_resumo.empty:
    fig_comparacao = px.bar(df_resumo, x="Store", y=["faturamento_real", "meta"], 
                            barmode="group", 
                            title="Faturamento Real vs Meta",
                            labels={"value": "Valor (R$)", "variable": "Tipo"})
    st.plotly_chart(fig_comparacao, use_container_width=True)
else:
    st.info("Sem dados suficientes para exibir o gráfico de comparação.")

# Ranking de Vendas por Vendedor
st.subheader("Ranking de Vendas por Vendedor")
df_ranking_seller = df_filtered.groupby("Seller").agg(
    total_sales=("faturamento", "sum"),
    total_quantity=("Quantity", "sum"),
    numero_vendas=("Seller", "count")
).reset_index().rename(columns={"numero_vendas": "Número de Vendas"})
df_ranking_seller = df_ranking_seller.sort_values(by="total_sales", ascending=False)
st.dataframe(df_ranking_seller.head(20))
fig_ranking_seller = px.bar(df_ranking_seller.head(10), x="Seller", y="total_sales", 
                            title="Top 10 Vendedores por Faturamento",
                            labels={"total_sales": "Faturamento (R$)"}, 
                            color="total_sales", color_continuous_scale="Blues")
fig_ranking_seller.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=50, b=20))
st.plotly_chart(fig_ranking_seller, use_container_width=True)


# Análise Sazonal: Distribuição do Faturamento por Mês
st.subheader("Análise Sazonal: Distribuição do Faturamento por Mês")
if not df_filtered.empty:
    df_filtered["month_name"] = df_filtered["Date"].dt.strftime("%b")
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    df_filtered["month_name"] = pd.Categorical(df_filtered["month_name"], categories=month_order, ordered=True)
    fig_season = px.box(df_filtered, x="month_name", y="faturamento",
                        title="Distribuição do Faturamento por Mês",
                        labels={"month_name": "Mês", "faturamento": "Faturamento (R$)"},
                        category_orders={"month_name": month_order},
                        color_discrete_sequence=["#8e44ad"])
    fig_season.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig_season, use_container_width=True)
else:
    st.info("Sem dados para análise sazonal.")

# Tabela Detalhada das Vendas com opção de download em CSV
st.subheader("Detalhamento das Vendas")
colunas_exibicao = ["Date", "Seller", "Store", "Quantity", "Price", "faturamento"]
df_detalhado = df_filtered[colunas_exibicao].dropna(subset=["Date"]).sort_values(by="Date", ascending=False)
st.dataframe(df_detalhado.head(20))
st.download_button("Download CSV", data=df_detalhado.to_csv(index=False).encode("utf-8"), 
                   file_name="vendas_detalhado.csv", mime="text/csv")