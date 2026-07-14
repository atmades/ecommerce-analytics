import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google.cloud import bigquery

st.set_page_config(
    page_title="MercadoLibre Price Tracker",
    page_icon="📊",
    layout="wide",
)

PROJECT = "notificationtest-2ce7b"

def get_bq_client():
    if "gcp_credentials" in st.secrets:
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_info(
            dict(st.secrets["gcp_credentials"]),
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return bigquery.Client(
            credentials=credentials,
            project=st.secrets["gcp_credentials"]["project_id"]
        )
    return bigquery.Client()

@st.cache_data(ttl=3600)
def load_price_history():
    client = get_bq_client()
    return client.query(f"""
        SELECT product_name, category_name, price_ars, prev_price_ars,
               price_delta_ars, price_change_pct, price_change_direction,
               valid_from, valid_to, is_current, price_version
        FROM `{PROJECT}.dataset_marts.mart_price_history`
        ORDER BY product_name, valid_from
    """).to_dataframe()

@st.cache_data(ttl=3600)
def load_price_ranking():
    client = get_bq_client()
    return client.query(f"""
        SELECT product_name, category_name,
               COUNT(*) as price_versions,
               MIN(price_ars) as start_price,
               MAX(price_ars) as peak_price,
               ROUND((MAX(price_ars) - MIN(price_ars)) / MIN(price_ars) * 100, 1) as total_growth_pct
        FROM `{PROJECT}.dataset_marts.mart_price_history`
        GROUP BY 1, 2
        HAVING COUNT(*) > 1
        ORDER BY total_growth_pct DESC
    """).to_dataframe()

st.title("📊 MercadoLibre Argentina — Price Tracker")
st.caption("SCD Type 2 price tracking · Data updated daily via API · Built with dbt + BigQuery + Airflow")

with st.spinner("Loading data..."):
    df_prices = load_price_history()
    df_ranking = load_price_ranking()

# ── Metrics ──
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Products tracked", len(df_prices['product_name'].unique()))
with col2:
    st.metric("Price changes detected", len(df_prices[df_prices['price_version'] > 1]))
with col3:
    max_growth = df_ranking['total_growth_pct'].max() if not df_ranking.empty else 0
    st.metric("Max price growth", f"+{max_growth}%")

# ── Top products bar chart ──
st.markdown("#### Top products by price growth")
fig1 = px.bar(
    df_ranking.head(10),
    x="total_growth_pct",
    y="product_name",
    orientation='h',
    color="total_growth_pct",
    color_continuous_scale=["#378ADD", "#e34948"],
    labels={"total_growth_pct": "Growth %", "product_name": ""},
    text="total_growth_pct",
)
fig1.update_traces(texttemplate="+%{text}%", textposition="outside")
fig1.update_layout(
    height=400,
    coloraxis_showscale=False,
    yaxis=dict(autorange="reversed"),
    margin=dict(l=0, r=60, t=20, b=20),
)
st.plotly_chart(fig1, use_container_width=True)

# ── Product detail ──
st.markdown("#### Price history by product")

products_with_changes = df_ranking['product_name'].tolist()
all_products = df_prices['product_name'].unique().tolist()

show_all = st.checkbox("Show all products (including single-version)", value=False)
product_list = all_products if show_all else products_with_changes

selected = st.selectbox("Select product", product_list)

df_p = df_prices[df_prices['product_name'] == selected].copy()
df_p['valid_from'] = pd.to_datetime(df_p['valid_from']).dt.date
df_p = df_p.sort_values('valid_from')

if len(df_p) < 2:
    st.info("Only 1 price record — no changes detected yet. Check back after next daily run.")
else:
    # ── Dual axis chart ──
    labels = df_p.apply(
        lambda r: f"{r['valid_from'].strftime('%d.%m')} (v{int(r['price_version'])})", axis=1
    ).tolist()


    fig2 = go.Figure()

    fig2.add_trace(go.Scatter(
        x=labels,
        y=df_p['price_ars'],
        mode='lines+markers',
        name='Price ARS',
        line=dict(color='#2a78d6', width=2),
        marker=dict(size=10, color='#2a78d6',
                    line=dict(color='#1a1a19', width=2)),
        hovertemplate='%{x}<br><b>%{y:,.0f} ARS</b><extra></extra>',
        fill='tozeroy',
        fillcolor='rgba(42,120,214,0.08)',
        yaxis='y1',
    ))

    fig2.add_trace(go.Bar(
        x=labels,
        y=df_p['price_change_pct'],
        name='Change %',
        marker_color='rgba(227,73,72,0.6)',
        hovertemplate='%{x}<br><b>+%{y:.1f}%</b><extra></extra>',
        yaxis='y2',
    ))

    fig2.update_layout(
        height=360,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=60, t=30, b=10),
        xaxis=dict(
            type='category',
            showgrid=False,
            tickfont=dict(size=12),
        ),
        yaxis=dict(
            title=dict(text='Price ARS', font=dict(color='#2a78d6')),
            tickfont=dict(color='#2a78d6', size=11),
            tickformat=',.0f',
            gridcolor='rgba(255,255,255,0.06)',
            showgrid=True,
        ),
        yaxis2=dict(
            title=dict(text='Change %', font=dict(color='#e34948')),
            tickfont=dict(color='#e34948', size=11),
            overlaying='y',
            side='right',
            tickformat='+.1f',
            showgrid=False,
            rangemode='tozero',
        ),
        legend=dict(
            orientation='h', y=1.12, x=0,
            font=dict(size=12),
            bgcolor='rgba(0,0,0,0)',
        ),
        hovermode='x unified',
    )
    st.plotly_chart(fig2, use_container_width=True)




    # fig2 = go.Figure()

    # # Y1 — цена ARS
    # fig2.add_trace(go.Scatter(
    #     x=labels,
    #     y=df_p['price_ars'],
    #     mode='lines+markers',
    #     name='Price ARS',
    #     line=dict(color='#2a78d6', width=2),
    #     marker=dict(size=8, color='#2a78d6'),
    #     hovertemplate='%{x}<br>Price: %{y:,.0f} ARS<extra></extra>',
    #     yaxis='y1',
    # ))

    # # Y2 — изменение в %
    # fig2.add_trace(go.Bar(
    #     x=labels,
    #     y=df_p['price_change_pct'],
    #     name='Change %',
    #     marker_color='#e34948',
    #     opacity=0.6,
    #     hovertemplate='%{x}<br>Change: +%{y:.1f}%<extra></extra>',
    #     yaxis='y2',
    # ))

    # fig2.update_layout(
    #     height=350,
    #     margin=dict(l=0, r=60, t=20, b=20),
    #     xaxis=dict(title='Date', type='category'),
    #     yaxis=dict(
    #         title=dict(text='Price ARS', font=dict(color='#2a78d6')),
    #         tickfont=dict(color='#2a78d6'),
    #         tickformat=',.0f',
    #     ),
    #     yaxis2=dict(
    #         title=dict(text='Change %', font=dict(color='#e34948')),
    #         tickfont=dict(color='#e34948'),
    #         overlaying='y',
    #         side='right',
    #         tickformat='+.1f',
    #         showgrid=False,
    #     ),
    #     legend=dict(orientation='h', y=1.1),
    #     hovermode='x unified',
    # )
    # st.plotly_chart(fig2, use_container_width=True)

    

# ── Detail table ──
st.dataframe(
    df_p[['price_version','valid_from','price_ars',
          'price_delta_ars','price_change_pct','price_change_direction','is_current']]
    .rename(columns={
        'price_version':'Version', 'valid_from':'Date', 'price_ars':'Price ARS',
        'price_delta_ars':'Delta ARS', 'price_change_pct':'Change %',
        'price_change_direction':'Direction', 'is_current':'Current',
    }),
    use_container_width=True,
    hide_index=True,
)

# ── Category breakdown ──
st.markdown("#### Price volatility by category")
df_cat = df_ranking.groupby('category_name').agg(
    products=('product_name','count'),
    avg_growth=('total_growth_pct','mean'),
    max_growth=('total_growth_pct','max'),
).reset_index().sort_values('avg_growth', ascending=False)

fig3 = px.scatter(
    df_cat,
    x='products',
    y='avg_growth',
    size='max_growth',
    color='category_name',
    labels={'products':'Products with price changes','avg_growth':'Avg growth %','category_name':'Category'},
    height=300,
)
fig3.update_layout(margin=dict(l=0,r=0,t=20,b=20), showlegend=True)
st.plotly_chart(fig3, use_container_width=True)