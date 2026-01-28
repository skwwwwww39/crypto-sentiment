import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
import os
import requests
import feedparser
from datetime import datetime
import re
from collections import Counter

# --- 1. Cyberpunk Design System ---
st.set_page_config(page_title="Terminal: Crypto Sentinel", layout="wide", page_icon="⚡")

st.markdown("""
<style>
    /* 没入感のあるダーク背景 */
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(circle at 50% 0%, #1a0b2e 0%, #000000 60%);
        color: #e0e0e0;
    }
    
    /* グラスモーフィズムカード */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        transition: transform 0.2s;
        height: 100%;
    }
    .glass-card:hover {
        border-color: rgba(0, 229, 255, 0.3);
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.1);
    }

    /* KPI数値 */
    .kpi-value { font-size: 2.2rem; font-weight: 800; color: #fff; line-height: 1.2; }
    .kpi-label { font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 1px; }
    .kpi-sub { font-size: 0.8rem; margin-top: 5px; opacity: 0.8; }
    
    /* ボタン */
    .stButton > button {
        background: linear-gradient(90deg, #240046, #bd00ff);
        border: 1px solid #bd00ff;
        color: white;
        font-weight: bold;
        padding: 12px 25px;
        border-radius: 4px;
        transition: all 0.3s;
        text-transform: uppercase;
        letter-spacing: 2px;
        width: 100%;
    }
    .stButton > button:hover {
        box-shadow: 0 0 20px rgba(189, 0, 255, 0.5);
        background: #bd00ff;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. API Config ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("🚨 SYSTEM HALTED: Missing API Key.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-flash-lite-latest')

# --- 3. Robust Data Fetching (Multi-Source) ---

@st.cache_data(ttl=300)
def get_crypto_price():
    """CoinGeckoから価格と7日分のチャートを取得"""
    try:
        # 価格
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        r = requests.get(url, timeout=5)
        data = r.json()
        price = data['bitcoin']['usd']
        change = data['bitcoin']['usd_24h_change']
        
        # チャート
        chart_url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=7"
        r_chart = requests.get(chart_url, timeout=5)
        chart_data = r_chart.json()
        prices = chart_data['prices'] 
        
        df_chart = pd.DataFrame(prices, columns=['timestamp', 'price'])
        df_chart['timestamp'] = pd.to_datetime(df_chart['timestamp'], unit='ms')
        
        # 移動平均線 (SMA) を計算してプロっぽくする
        df_chart['SMA'] = df_chart['price'].rolling(window=24).mean()
        
        return price, change, df_chart
    except:
        return 0, 0, pd.DataFrame()

@st.cache_data(ttl=3600)
def get_fear_greed_index():
    try:
        url = "https://api.alternative.me/fng/"
        r = requests.get(url, timeout=5)
        data = r.json()
        value = int(data['data'][0]['value'])
        classification = data['data'][0]['value_classification']
        return value, classification
    except:
        return 50, "Neutral"

def get_rss_news_robust(limit=30):
    """
    YahooがダメならCoinDesk、それもダメならCointelegraph...と
    次々にソースを変えて絶対にデータを取ってくる関数
    """
    sources = [
        ("https://finance.yahoo.com/rss/headline?s=BTC-USD", "Yahoo Finance"),
        ("https://www.coindesk.com/arc/outboundfeeds/rss/", "CoinDesk"),
        ("https://cointelegraph.com/rss", "CoinTelegraph"),
        ("https://cryptopotato.com/feed/", "CryptoPotato")
    ]
    
    # ブラウザのふりをするヘッダー
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    for url, source_name in sources:
        try:
            # requestsで生データを取ってからfeedparserに食わせる（ブロック回避）
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                
                if not feed.entries:
                    continue # エントリーが空なら次のソースへ
                    
                news_items = []
                for i, entry in enumerate(feed.entries[:limit]):
                    title = entry.title
                    link = entry.link
                    # 日付処理
                    if 'published' in entry:
                        pub_str = entry.published
                    elif 'updated' in entry:
                        pub_str = entry.updated
                    else:
                        pub_str = str(datetime.now())
                        
                    try:
                        # ざっくり日付パース
                        dt_obj = pd.to_datetime(pub_str).to_pydatetime()
                        # タイムゾーン情報を削除して統一
                        dt_obj = dt_obj.replace(tzinfo=None)
                    except:
                        dt_obj = datetime.now()

                    news_items.append({
                        "id": i, 
                        "text": title, 
                        "date_str": dt_obj.strftime("%Y-%m-%d %H:%M"),
                        "timestamp": dt_obj,
                        "source": source_name, 
                        "link": link
                    })
                
                if news_items:
                    return news_items, source_name # 成功したら即リターン
        except:
            continue
            
    return [], "None" # 全滅

# --- 4. Analytics Modules ---

def analyze_sentiment(news_list):
    if not news_list: return []
    news_block = "\n".join([f"ID {item['id']}: {item['text']}" for item in news_list])
    
    prompt = f"""
    Analyze sentiment of {len(news_list)} crypto headlines.
    Return JSON list: ID|Label|Score
    Label: [Euphoria, Optimism, Positive, Neutral, Negative, Fear, Despair]
    Score: -100 to 100
    
    Headlines:
    {news_block}
    """
    try:
        res = model.generate_content(prompt)
        if not res.text: return []
        
        results = []
        for line in res.text.strip().split("\n"):
            parts = line.split("|")
            if len(parts) == 3:
                try:
                    nid = int(parts[0].replace("ID", "").strip())
                    label = parts[1].strip()
                    score = int(parts[2].strip())
                    for item in news_list:
                        if item['id'] == nid:
                            item['Label'] = label
                            item['Score'] = score
                            results.append(item)
                except: continue
        return results
    except: return []

def extract_keywords(df):
    if df.empty: return []
    text = " ".join(df['text'].tolist()).lower()
    ignore = ['to', 'in', 'for', 'of', 'the', 'on', 'and', 'a', 'is', 'at', 'bitcoin', 'crypto', 'price', 'market', 'btc', 'after', 'as', 'with', 'from', 'by', 'vs', 'new', 'top', 'why', 'will']
    words = re.findall(r'\b\w{3,}\b', text)
    filtered = [w for w in words if w not in ignore and not w.isdigit()]
    return Counter(filtered).most_common(8)

# --- 5. Main Dashboard UI ---

st.title("⚡ TRADER'S COCKPIT: BTC SENTINEL")
st.markdown("REAL-TIME MARKET INTELLIGENCE // AI-POWERED ANALYSIS")

if st.button("🔄 REFRESH DATA FEED", type="primary"):
    with st.spinner("📡 SCANNING MULTIPLE FREQUENCIES..."):
        # Parallel-ish Fetching
        btc_price, btc_change, btc_chart = get_crypto_price()
        fng_val, fng_class = get_fear_greed_index()
        raw_news, source_used = get_rss_news_robust(limit=30)
        
        # AI Analysis
        if raw_news:
            analyzed_data = analyze_sentiment(raw_news)
            df = pd.DataFrame(analyzed_data)
        else:
            df = pd.DataFrame()

    # --- LAYOUT ---
    
    # ROW 1: KPI CARDS
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        price_col = "#00ff99" if btc_change >= 0 else "#ff0055"
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">BTC PRICE</div>
            <div class="kpi-value">${btc_price:,.0f}</div>
            <div class="kpi-sub" style="color:{price_col}">{btc_change:+.2f}% (24h)</div>
        </div>""", unsafe_allow_html=True)
        
    with col2:
        if not df.empty and 'Score' in df.columns:
            score = df['Score'].mean()
            col = "#00ff99" if score > 20 else "#ff0055" if score < -20 else "#bd00ff"
            st.markdown(f"""
            <div class="glass-card">
                <div class="kpi-label">AI SENTIMENT</div>
                <div class="kpi-value" style="color:{col}">{int(score)}</div>
                <div class="kpi-sub">Source: {source_used}</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="glass-card"><div class="kpi-label">AI SENTIMENT</div><div class="kpi-value" style="color:#555">--</div><div class="kpi-sub">NO DATA</div></div>""", unsafe_allow_html=True)

    with col3:
        fng_col = "#00ff99" if fng_val > 50 else "#ff0055"
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">FEAR & GREED</div>
            <div class="kpi-value" style="color:{fng_col}">{fng_val}</div>
            <div class="kpi-sub">{fng_class}</div>
        </div>""", unsafe_allow_html=True)

    with col4:
        count = len(df)
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">SIGNAL DENSITY</div>
            <div class="kpi-value">{count}</div>
            <div class="kpi-sub">News Processed</div>
        </div>""", unsafe_allow_html=True)

    # ROW 2: CHARTS
    c_chart1, c_chart2 = st.columns([2, 1])
    
    with c_chart1:
        st.subheader("📈 Price Action + Trend")
        if not btc_chart.empty:
            fig = go.Figure()
            # Price Line
            fig.add_trace(go.Scatter(x=btc_chart['timestamp'], y=btc_chart['price'], mode='lines', name='Price', line=dict(color='#00e5ff', width=2)))
            # SMA Line (Trend)
            fig.add_trace(go.Scatter(x=btc_chart['timestamp'], y=btc_chart['SMA'], mode='lines', name='MA(24h)', line=dict(color='#bd00ff', width=1, dash='dash')))
            
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#888'),
                margin=dict(l=0, r=0, t=0, b=0), height=350,
                xaxis=dict(showgrid=False), yaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                legend=dict(orientation="h", y=1, x=0)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Price data unavailable.")

    with c_chart2:
        st.subheader("🌊 Sentiment Flow")
        if not df.empty and 'Score' in df.columns:
            df = df.sort_values('timestamp')
            fig = px.area(df, x='timestamp', y='Score', line_shape='spline')
            fig.update_traces(line_color='#00ff99', fillcolor='rgba(0, 255, 153, 0.1)')
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#888'),
                margin=dict(l=0, r=0, t=0, b=0), height=350,
                yaxis=dict(range=[-100, 100], gridcolor='rgba(255,255,255,0.1)'), xaxis=dict(showticklabels=False)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown("<div style='height:350px; display:flex; align-items:center; justify-content:center; border:1px dashed #333; border-radius:10px; color:#555;'>WAITING FOR SIGNALS</div>", unsafe_allow_html=True)

    # ROW 3: ANALYSIS
    c_kw, c_pie = st.columns(2)
    
    with c_kw:
        st.subheader("🗣 Market Narrative")
        if not df.empty:
            keywords = extract_keywords(df)
            if keywords:
                kw_df = pd.DataFrame(keywords, columns=['word', 'count'])
                fig = px.bar(kw_df, x='count', y='word', orientation='h', color='count', color_continuous_scale='Viridis')
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#e0e0e0',
                    yaxis={'categoryorder':'total ascending'}, height=300, margin=dict(t=0,b=0)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Not enough text data for narrative analysis.")
        else:
            st.info("No narrative data.")

    with c_pie:
        st.subheader("🥧 Emotion Ratio")
        if not df.empty and 'Label' in df.columns:
            cmap = {'Euphoria': '#00FF99', 'Optimism': '#00e5ff', 'Positive': '#3498DB', 'Neutral': '#555', 'Negative': '#F1C40F', 'Fear': '#ff5e00', 'Despair': '#ff0055'}
            fig = px.pie(df, names='Label', hole=0.6, color='Label', color_discrete_map=cmap)
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#e0e0e0', height=300, margin=dict(t=0,b=0), showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No emotion data.")

    # ROW 4: FEED
    st.subheader("📋 Intelligence Logs")
    if not df.empty:
        for idx, row in df.iterrows():
            s_col = "#00ff99" if row['Score'] > 0 else "#ff0055" if row['Score'] < 0 else "#888"
            st.markdown(f"""
            <div style="border-left: 3px solid {s_col}; padding-left: 15px; margin-bottom: 10px; background: rgba(255,255,255,0.02);">
                <div style="font-size: 0.8rem; color: #666;">{row['date_str']} | {row['source']}</div>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <a href="{row['link']}" target="_blank" style="color: #eee; font-weight:bold; text-decoration:none; font-size:1rem;">{row['text']}</a>
                    <div style="text-align:right;">
                        <span style="color:{s_col}; font-weight:bold;">{row['Label']}</span> <span style="font-size:0.8rem; color:#666;">({row['Score']})</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("No news feed available at this moment. Please try again later.")

else:
    st.markdown("""
    <div style="text-align:center; padding: 100px; color:#444;">
        <h1>SYSTEM STANDBY</h1>
        <p>Click REFRESH to initialize market scan.</p>
    </div>
    """, unsafe_allow_html=True)