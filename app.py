import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import google.generativeai as genai
import os
import time
import feedparser
import requests
from datetime import datetime
from collections import Counter
import re

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
    }
    .glass-card:hover {
        border-color: rgba(0, 229, 255, 0.3);
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.1);
    }

    /* ネオンテキスト */
    .neon-text-purple { color: #bd00ff; text-shadow: 0 0 10px rgba(189, 0, 255, 0.6); }
    .neon-text-cyan { color: #00e5ff; text-shadow: 0 0 10px rgba(0, 229, 255, 0.6); }
    .neon-text-green { color: #00ff99; text-shadow: 0 0 10px rgba(0, 255, 153, 0.6); }
    .neon-text-red { color: #ff0055; text-shadow: 0 0 10px rgba(255, 0, 85, 0.6); }

    /* KPI数値 */
    .kpi-value { font-size: 2.2rem; font-weight: 800; color: #fff; line-height: 1.2; }
    .kpi-label { font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 1px; }
    
    /* ボタン */
    .stButton > button {
        background: linear-gradient(90deg, #240046, #bd00ff);
        border: 1px solid #bd00ff;
        color: white;
        font-weight: bold;
        padding: 10px 25px;
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

# --- 3. Data Fetching Modules ---

# [A] CoinGecko: BTC Price & Chart (Cache 5 min)
@st.cache_data(ttl=300)
def get_crypto_price():
    try:
        # 価格データの取得
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        r = requests.get(url, timeout=5)
        data = r.json()
        price = data['bitcoin']['usd']
        change = data['bitcoin']['usd_24h_change']
        
        # チャートデータの取得 (7日間)
        chart_url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=7"
        r_chart = requests.get(chart_url, timeout=5)
        chart_data = r_chart.json()
        prices = chart_data['prices'] # [timestamp, price]
        
        df_chart = pd.DataFrame(prices, columns=['timestamp', 'price'])
        df_chart['timestamp'] = pd.to_datetime(df_chart['timestamp'], unit='ms')
        
        return price, change, df_chart
    except:
        return None, None, pd.DataFrame()

# [B] Alternative.me: Fear & Greed Index (Cache 1 hour)
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

# [C] Yahoo Finance RSS: News
def get_rss_news(limit=30): 
    rss_url = "https://finance.yahoo.com/rss/headline?s=BTC-USD"
    try:
        feed = feedparser.parse(rss_url)
        if not feed.entries: return []
        news_items = []
        for i, entry in enumerate(feed.entries[:limit]):
            title = entry.title
            link = entry.link
            published = entry.published if 'published' in entry else datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
            
            # Timestamp for sorting
            try:
                dt_obj = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %z")
            except:
                dt_obj = datetime.now()

            news_items.append({
                "id": i, 
                "text": title, 
                "date_str": dt_obj.strftime("%Y-%m-%d %H:%M"),
                "timestamp": dt_obj,
                "source": "Yahoo Fin", 
                "link": link
            })
        return news_items
    except:
        return []

# --- 4. Analytics Modules ---

def analyze_sentiment(news_list):
    if not news_list: return []
    news_block = "\n".join([f"ID {item['id']}: {item['text']}" for item in news_list])
    
    prompt = f"""
    Analyze sentiment of {len(news_list)} crypto headlines.
    Output JSON list: ID, Label (Euphoria, Optimism, Positive, Neutral, Negative, Fear, Despair), Score (-100 to 100).
    Format: ID|Label|Score
    
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
    """ニュースタイトルから頻出単語を抽出"""
    text = " ".join(df['text'].tolist()).lower()
    # 簡易的なストップワード除去
    ignore = ['to', 'in', 'for', 'of', 'the', 'on', 'and', 'a', 'is', 'at', 'bitcoin', 'crypto', 'price', 'market', 'btc', 'after', 'as', 'with', 'from', 'by']
    words = re.findall(r'\b\w{3,}\b', text)
    filtered = [w for w in words if w not in ignore and not w.isdigit()]
    return Counter(filtered).most_common(10)

# --- 5. Main Dashboard UI ---

st.title("⚡ TRADER'S COCKPIT: BTC SENTINEL")
st.markdown("REAL-TIME MARKET INTELLIGENCE // AI-POWERED ANALYSIS")

if st.button("🔄 REFRESH DATA FEED", type="primary"):
    with st.spinner("📡 ESTABLISHING UPLINK..."):
        # 1. Fetch External Data (Parallel-ish)
        btc_price, btc_change, btc_chart = get_crypto_price()
        fng_val, fng_class = get_fear_greed_index()
        raw_news = get_rss_news(limit=25)
        
        # 2. AI Analysis
        if raw_news:
            analyzed_data = analyze_sentiment(raw_news)
            df = pd.DataFrame(analyzed_data)
        else:
            df = pd.DataFrame()

        # --- LAYOUT CONSTRUCTION ---
        
        # --- ROW 1: KEY MARKET METRICS (4 Columns) ---
        col1, col2, col3, col4 = st.columns(4)
        
        # Card 1: BTC Price
        with col1:
            price_color = "#00ff99" if btc_change and btc_change >= 0 else "#ff0055"
            st.markdown(f"""
            <div class="glass-card">
                <div class="kpi-label">BTC / USD</div>
                <div class="kpi-value">${btc_price:,.0f}</div>
                <div style="color: {price_color}; font-weight:bold;">{btc_change:+.2f}% (24h)</div>
            </div>""", unsafe_allow_html=True)
            
        # Card 2: AI Sentiment Score
        with col2:
            if not df.empty:
                ai_score = df['Score'].mean()
                ai_color = "#00ff99" if ai_score > 0 else "#ff0055"
                st.markdown(f"""
                <div class="glass-card">
                    <div class="kpi-label">AI SENTIMENT</div>
                    <div class="kpi-value" style="color:{ai_color}">{int(ai_score)}</div>
                    <div style="font-size:0.8rem; color:#888;">-100 (Bear) to 100 (Bull)</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown("<div class='glass-card'>NO DATA</div>", unsafe_allow_html=True)

        # Card 3: Fear & Greed (Official)
        with col3:
            fng_color = "#00ff99" if fng_val > 50 else "#ff0055"
            st.markdown(f"""
            <div class="glass-card">
                <div class="kpi-label">FEAR & GREED (OFFICIAL)</div>
                <div class="kpi-value" style="color:{fng_color}">{fng_val}</div>
                <div style="color:{fng_color}">{fng_class}</div>
            </div>""", unsafe_allow_html=True)

        # Card 4: Signal Strength
        with col4:
            count = len(df) if not df.empty else 0
            st.markdown(f"""
            <div class="glass-card">
                <div class="kpi-label">NEWS VOLUME</div>
                <div class="kpi-value">{count}</div>
                <div style="font-size:0.8rem; color:#00e5ff;">Sources Analyzed</div>
            </div>""", unsafe_allow_html=True)

        # --- ROW 2: CHARTS (Price Trend & Sentiment Trend) ---
        c_chart1, c_chart2 = st.columns([2, 1])
        
        with c_chart1:
            st.subheader("📈 BTC Price Action (7 Days)")
            if not btc_chart.empty:
                fig_price = px.line(btc_chart, x='timestamp', y='price', line_shape='spline')
                fig_price.update_traces(line_color='#00e5ff', line_width=3)
                fig_price.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#888',
                    xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                    height=300, margin=dict(l=0, r=0, t=10, b=0)
                )
                st.plotly_chart(fig_price, use_container_width=True)
        
        with c_chart2:
            st.subheader("🌊 Intraday Sentiment Flow")
            if not df.empty:
                # タイムスタンプでソートしてセンチメントの推移を表示
                df_sorted = df.sort_values('timestamp')
                fig_sent_trend = px.line(df_sorted, x='timestamp', y='Score', markers=True, title=None)
                fig_sent_trend.update_traces(line_color='#bd00ff', line_width=2)
                fig_sent_trend.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.3)
                fig_sent_trend.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#888',
                    xaxis=dict(showticklabels=False), yaxis=dict(range=[-100, 100]),
                    height=300, margin=dict(l=0, r=0, t=10, b=0)
                )
                st.plotly_chart(fig_sent_trend, use_container_width=True)

        # --- ROW 3: DEEP DIVE (Keywords & Distribution) ---
        c_deep1, c_deep2 = st.columns(2)
        
        with c_deep1:
            st.subheader("🗣 Market Narrative (Top Keywords)")
            if not df.empty:
                keywords = extract_keywords(df)
                kw_df = pd.DataFrame(keywords, columns=['word', 'count'])
                fig_kw = px.bar(kw_df, x='count', y='word', orientation='h', color='count', color_continuous_scale='Viridis')
                fig_kw.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#e0e0e0',
                    yaxis={'categoryorder':'total ascending'}, height=300
                )
                st.plotly_chart(fig_kw, use_container_width=True)
                
        with c_deep2:
            st.subheader("🥧 Emotion Ratio")
            if not df.empty:
                color_map = {'Euphoria': '#00FF99', 'Optimism': '#00e5ff', 'Positive': '#3498DB', 'Neutral': '#888', 'Negative': '#F1C40F', 'Fear': '#ff5e00', 'Despair': '#ff0055'}
                fig_pie = px.pie(df, names='Label', hole=0.5, color='Label', color_discrete_map=color_map)
                fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#e0e0e0', height=300)
                st.plotly_chart(fig_pie, use_container_width=True)

        # --- ROW 4: RAW INTEL ---
        st.subheader("📋 Raw Intelligence Feed")
        if not df.empty:
            for index, row in df.iterrows():
                score_color = "#00ff99" if row['Score'] > 0 else "#ff0055"
                st.markdown(f"""
                <div style="border-bottom: 1px solid rgba(255,255,255,0.1); padding: 10px 0; display:flex; justify-content:space-between; align-items:center;">
                    <div style="flex-grow:1;">
                        <span style="color:#666; font-size:0.8rem;">{row['date_str']}</span><br>
                        <a href="{row['link']}" style="color:#e0e0e0; text-decoration:none; font-weight:bold; font-size:1.1rem;">{row['text']}</a>
                    </div>
                    <div style="text-align:right; min-width:80px;">
                        <span style="color:{score_color}; font-weight:bold; font-size:1.2rem;">{row['Score']}</span><br>
                        <span style="color:#888; font-size:0.8rem;">{row['Label']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

else:
    # 待機画面
    st.markdown("""
    <div style="text-align:center; padding: 50px; opacity: 0.7;">
        <h1>SYSTEM READY</h1>
        <p>Awaiting operator command to initialize scan...</p>
    </div>
    """, unsafe_allow_html=True)