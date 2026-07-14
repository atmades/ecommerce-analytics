"""
Price Gallery — product cards with images and price history
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from google.cloud import bigquery
import requests

st.set_page_config(
    page_title="Price Gallery",
    page_icon="🛍️",
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
def load_price_ranking():
    client = get_bq_client()
    query = f"""
    SELECT
        product_id,
        product_name,
        category_name,
        COUNT(*) as price_versions,
        MIN(price_ars) as start_price,
        MAX(price_ars) as current_price,
        ROUND((MAX(price_ars) - MIN(price_ars)) / MIN(price_ars) * 100, 1) as growth_pct
    FROM `{PROJECT}.dataset_marts.mart_price_history`
    GROUP BY 1, 2, 3
    HAVING COUNT(*) > 1
    ORDER BY growth_pct DESC
    LIMIT 30
    """
    return client.query(query).to_dataframe()

@st.cache_data(ttl=3600)
def load_product_history(product_id: str):
    client = get_bq_client()
    query = f"""
    SELECT price_version, valid_from, price_ars,
           price_delta_ars, price_change_pct, price_change_direction
    FROM `{PROJECT}.dataset_marts.mart_price_history`
    WHERE product_id = '{product_id}'
    ORDER BY valid_from
    """
    return client.query(query).to_dataframe()

@st.cache_data(ttl=21600)
def get_ml_token() -> str | None:
    try:
        if "mercadolibre" not in st.secrets:
            return None
        response = requests.post(
            "https://api.mercadolibre.com/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": st.secrets["mercadolibre"]["client_id"],
                "client_secret": st.secrets["mercadolibre"]["client_secret"],
            },
            timeout=10
        )
        if response.status_code == 200:
            return response.json()["access_token"]
    except Exception:
        pass
    return None

@st.cache_data(ttl=86400)
def get_product_image(product_id: str) -> str | None:
    try:
        token = get_ml_token()
        if not token:
            return None
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"https://api.mercadolibre.com/products/{product_id}",
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            pictures = response.json().get("pictures", [])
            if pictures:
                return pictures[0]["url"]
    except Exception:
        pass
    return None

def waterfall_chart(df: pd.DataFrame, product_name: str):
    labels = ["Start"] + [
        f"v{int(r.price_version)}" for _, r in df.iterrows() if r.price_version > 1
    ]
    values = [df.iloc[0]['price_ars']] + [
        r.price_delta_ars for _, r in df.iterrows() if r.price_version > 1
    ]
    measures = ["absolute"] + ["relative"] * (len(values) - 1)
    colors = ["#2a78d6"] + [
        "#e34948" if v > 0 else "#1baf7a" for v in values[1:]
    ]

    fig = go.Figure(go.Waterfall(
        name="Price",
        orientation="v",
        measure=measures,
        x=labels,
        y=values,
        connector=dict(line=dict(color="#555", width=1, dash="dot")),
        increasing=dict(marker=dict(color="#e34948")),
        decreasing=dict(marker=dict(color="#1baf7a")),
        totals=dict(marker=dict(color="#2a78d6")),
        texttemplate="%{y:,.0f}",
        textposition="outside",
    ))
    fig.update_layout(
        height=220,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.06)',
                   tickformat=',.0f', tickfont=dict(size=10)),
        xaxis=dict(showgrid=False, tickfont=dict(size=10)),
    )
    return fig

@st.cache_data(ttl=3600)
def load_price_drops():
    client = get_bq_client()
    query = f"""
    SELECT
        product_id,
        product_name,
        category_name,
        COUNT(*) as price_versions,
        MAX(price_ars) as peak_price,
        MIN(price_ars) as current_price,
        ROUND((MIN(price_ars) - MAX(price_ars)) / MAX(price_ars) * 100, 1) as drop_pct
    FROM `{PROJECT}.dataset_marts.mart_price_history`
    GROUP BY 1, 2, 3
    HAVING COUNT(*) > 1
      AND MIN(price_ars) < MAX(price_ars)
    ORDER BY drop_pct ASC
    """
    return client.query(query).to_dataframe()

# ── Page ─────────────────────────────────────────────────────────────────────

st.title("🛍️ Price Gallery")
st.caption("Top products by price growth — with images and waterfall price history")
st.info(
    "⚠️ Showing products from 5 categories only (Accesorios para Vehículos, Agro, "
    "Alimentos y Bebidas, Animales y Mascotas, Antigüedades y Colecciones). "
    "To track all 32 MercadoLibre categories, increase MAX_CATEGORIES in load_mercadolibre.py."
)

with st.spinner("Loading products..."):
    df = load_price_ranking()

if df.empty:
    st.warning("No products with multiple price versions yet. Check back after more daily runs.")
    st.stop()

cols = st.columns(3)

for i, row in df.iterrows():
    col = cols[i % 3]
    with col:
        with st.container(border=True):
            img_url = get_product_image(row['product_id'])
            if img_url:
                st.image(img_url, width=300)
            else:
                st.markdown(
                    "<div style='height:140px;background:var(--surface-1);"
                    "display:flex;align-items:center;justify-content:center;"
                    "border-radius:8px;color:gray'>No image</div>",
                    unsafe_allow_html=True
                )

            name = row['product_name']
            short_name = name[:50] + "..." if len(name) > 50 else name
            st.markdown(f"**{short_name}**")
            st.caption(row['category_name'])

            c1, c2 = st.columns(2)
            with c1:
                st.metric(
                    "Current price",
                    f"{row['current_price']:,.0f} ARS",
                )
            with c2:
                st.metric(
                    "Growth",
                    f"+{row['growth_pct']}%",
                    delta=f"+{row['current_price'] - row['start_price']:,.0f} ARS",
                )

            df_hist = load_product_history(row['product_id'])
            if len(df_hist) > 1:
                st.plotly_chart(
                    waterfall_chart(df_hist, row['product_name']),
                    use_container_width=True,
                    key=f"wf_{row['product_id']}"
                )


st.divider()
st.subheader("📉 Price drops")

with st.spinner("Loading price drops..."):
    df_drops = load_price_drops()

if df_drops.empty:
    st.info("No price drops detected yet.")
else:
    for _, row in df_drops.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.markdown(f"**{row['product_name'][:70]}**")
                st.caption(row['category_name'])
            with c2:
                st.metric("Peak price", f"{row['peak_price']:,.0f} ARS")
            with c3:
                st.metric("Now", f"{row['current_price']:,.0f} ARS",
                         delta=f"{row['drop_pct']}%")