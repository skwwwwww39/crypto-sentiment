import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
import os
import requests
from datetime import datetime, timezone
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
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .glass-card:hover {
        border-color: rgba(0, 229, 255, 0.3);
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.1);
        transform: translateY(-2px);
    }

    /* KPI数値 */
    .kpi-value { font-size: 2.2rem; font-weight: 800; color: #fff; line-height: 1.2; }
    .kpi-label { font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 1px; }
    .kpi-sub { font-size: 0.8rem; margin-top: 5px; opacity: 0.8; }
    
    /* ボタン */
    .stButton > button {
        background: linear-gradient(90deg, #bd00ff, #240046);
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
# 指定のLiteモデルを使用
model = genai.GenerativeModel('gemini-flash-lite-latest')

# --- 3. Data Fetching (CryptoCompare) ---

@st.cache_data(ttl=300)
def get_crypto_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        r = requests.get(url, timeout=5)
        data = r.json()
        price = data['bitcoin']['usd']
        change = data['bitcoin']['usd_24h_change']
        
        chart_url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=7"
        r_chart = requests.get(chart_url, timeout=5)
        chart_data = r_chart.json()
        df_chart = pd.DataFrame(chart_data['prices'], columns=['timestamp', 'price'])
        df_chart['timestamp'] = pd.to_datetime(df_chart['timestamp'], unit='ms', utc=True)
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

def get_real_market_news(limit=25):
    url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if "Data" not in data: 
            return []
        news_items = []
        for i, item in enumerate(data["Data"][:limit]):
            title = item.get("title", "")
            source = item.get("source_info", {}).get("name", "CryptoCompare")
            url = item.get("url", "#")
            published_on = item.get("published_on", 0)

            # ✅ UTCで一貫したtimestampに（小さな改善）
            dt_obj = datetime.fromtimestamp(published_on, tz=timezone.utc)
            date_str = dt_obj.strftime("%Y-%m-%d %H:%M UTC")

            news_items.append({
                "id": i, "text": title, "date_str": date_str,
                "timestamp": dt_obj, "source": source, "link": url
            })
        return news_items
    except Exception as e:
        st.error(f"API Error: {e}")
        return []

# --- 4. Analytics Modules ---

def analyze_sentiment(news_list):
    if not news_list: 
        return []
    
    results = []
    # バッチ処理（10件ずつ処理してエラーを防ぐ）
    batch_size = 10
    
    for i in range(0, len(news_list), batch_size):
        batch = news_list[i:i+batch_size]
        news_block = "\n".join([f"ID {item['id']}: {item['text']}" for item in batch])
        
        prompt = f"""
        Analyze sentiment of these {len(batch)} crypto headlines.
        Return ONLY a list in this exact format: ID|Label|Score
        Label must be one of: [Euphoria, Optimism, Positive, Neutral, Negative, Fear, Despair]
        Score is integer from -100 to 100.
        Do not use markdown.
        
        Headlines:
        {news_block}
        """
        try:
            res = model.generate_content(prompt)
            if not res.text: 
                continue
            
            # 正規表現で強力にパースする
            for line in res.text.strip().split("\n"):
                match = re.search(r'(\d+)\s*\|\s*([A-Za-z]+)\s*\|\s*(-?\d+)', line)
                if match:
                    nid = int(match.group(1))
                    label = match.group(2)
                    score = int(match.group(3))
                    
                    # 該当するニュースアイテムを探して結果に追加
                    found_item = None
                    for item in news_list:
                        if item['id'] == nid:
                            found_item = item.copy()  # コピーを作成
                            found_item['Label'] = label
                            found_item['Score'] = score
                            break
                    
                    if found_item:
                        results.append(found_item)

        except Exception as e:
            print(f"Batch Error: {e}")
            continue
            
    return results

def extract_keywords(df):
    if df.empty: 
        return []
    text = " ".join(df['text'].tolist()).lower()
    ignore = ['to', 'in', 'for', 'of', 'the', 'on', 'and', 'a', 'is', 'at', 'bitcoin', 'crypto', 'price', 'market', 'btc', 'after', 'as', 'with', 'from', 'by', 'vs', 'new', 'top', 'why', 'will', 'news', 'analysis', 'live', '-', '|', 'cryptocurrency', 'says', 'update', 'daily']
    words = re.findall(r'\b\w{3,}\b', text)
    filtered = [w for w in words if w not in ignore and not w.isdigit()]
    return Counter(filtered).most_common(8)

# --- 5. Main Dashboard UI ---

st.title("⚡ TRADER'S COCKPIT: BTC SENTINEL")
st.markdown("REAL-TIME MARKET INTELLIGENCE // CRYPTOCOMPARE API FEED")

if st.button("🔄 REFRESH DATA FEED", type="primary"):
    with st.spinner("📡 ESTABLISHING SECURE UPLINK..."):
        # Parallel-ish Fetching
        btc_price, btc_change, btc_chart = get_crypto_price()
        fng_val, fng_class = get_fear_greed_index()
        raw_news = get_real_market_news(limit=25)
        
        # AI Analysis
        df = pd.DataFrame()
        if raw_news:
            analyzed_data = analyze_sentiment(raw_news)
            if analyzed_data:
                df = pd.DataFrame(analyzed_data)
            else:
                # AIが失敗してもニュースは表示する
                df = pd.DataFrame(raw_news)
                st.warning("AI Analysis partially failed due to traffic. Showing Raw Data.")

    # --- LAYOUT CONSTRUCTION ---
    
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
                <div class="kpi-sub">Market Mood</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="glass-card"><div class="kpi-label">AI SENTIMENT</div><div class="kpi-value">--</div><div class="kpi-sub">ANALYZING...</div></div>""", unsafe_allow_html=True)

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
            <div class="kpi-sub">Packets Processed</div>
        </div>""", unsafe_allow_html=True)

    # ROW 2: CHARTS
    c_chart1, c_chart2 = st.columns([2, 1])
    
    with c_chart1:
        st.subheader("📈 Price Action + Trend")
        if not btc_chart.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=btc_chart['timestamp'], y=btc_chart['price'],
                mode='lines', name='Price',
                line=dict(color='#00e5ff', width=2)
            ))
            if 'SMA' in btc_chart.columns:
                fig.add_trace(go.Scatter(
                    x=btc_chart['timestamp'], y=btc_chart['SMA'],
                    mode='lines', name='MA(24h)',
                    line=dict(color='#bd00ff', width=1, dash='dash')
                ))
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#888'), margin=dict(l=0, r=0, t=0, b=0), height=350,
                xaxis=dict(showgrid=False), yaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                legend=dict(orientation="h", y=1, x=0)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Price data unavailable.")

    with c_chart2:
        st.subheader("🌊 Sentiment Flow")
        if not df.empty and 'Score' in df.columns and 'timestamp' in df.columns:
            # ✅ 修正案1 + 小さな改善（UTC変換 / NaT除外 / ソート / 重複timestamp除去）
            chart_df = df.copy()

            # timestampを確実にdatetime(UTC)へ（失敗はNaT）
            chart_df['timestamp'] = pd.to_datetime(chart_df['timestamp'], utc=True, errors='coerce')

            # 必要列が欠けている行を落とす
            chart_df = chart_df.dropna(subset=['timestamp', 'Score'])

            # 時系列で右に進むようにソート（古い→新しい）
            chart_df = chart_df.sort_values(by='timestamp', ascending=True)

            # 同一timestampが複数あると縦線が出やすいので、最後の1件に統一（任意だが効く）
            chart_df = chart_df.drop_duplicates(subset=['timestamp'], keep='last')

            # ✅ splineをやめてlinearに（左に戻る/自己交差の主因を排除）
            fig = px.area(chart_df, x='timestamp', y='Score', line_shape='linear')

            fig.update_traces(line_color='#00ff99', fillcolor='rgba(0, 255, 153, 0.1)')
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#888'), margin=dict(l=0, r=0, t=0, b=0), height=350,
                yaxis=dict(range=[-100, 100], gridcolor='rgba(255,255,255,0.1)'),
                xaxis=dict(showticklabels=False)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sentiment data available.")

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
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#e0e0e0', yaxis={'categoryorder':'total ascending'},
                    height=300, margin=dict(t=0,b=0)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Insufficient text for analysis.")
        else:
            st.info("No narrative data.")

    with c_pie:
        st.subheader("🥧 Emotion Ratio")
        if not df.empty and 'Label' in df.columns:
            cmap = {
                'Euphoria': '#00FF99', 'Optimism': '#00e5ff', 'Positive': '#3498DB',
                'Neutral': '#555', 'Negative': '#F1C40F', 'Fear': '#ff5e00', 'Despair': '#ff0055'
            }
            fig = px.pie(df, names='Label', hole=0.6, color='Label', color_discrete_map=cmap)
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', font_color='#e0e0e0',
                height=300, margin=dict(t=0,b=0), showlegend=True
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No emotion data.")

    # ROW 4: FEED
    st.subheader("📋 Intelligence Logs")
    if not df.empty:
        # ログは「新しい順」が見やすいので、グラフとは逆に降順で表示する
        if 'timestamp' in df.columns:
            df_log = df.copy()
            df_log['timestamp'] = pd.to_datetime(df_log['timestamp'], utc=True, errors='coerce')
            df_log = df_log.sort_values(by='timestamp', ascending=False)
        else:
            df_log = df
             
        for idx, row in df_log.iterrows():
            s_col = "#00ff99" if row.get('Score', 0) > 0 else "#ff0055" if row.get('Score', 0) < 0 else "#888"
            date_display = row.get('date_str', 'Recent')
            st.markdown(f"""
            <div style="border-left: 3px solid {s_col}; padding-left: 15px; margin-bottom: 10px; background: rgba(255,255,255,0.02);">
                <div style="font-size: 0.8rem; color: #666;">{date_display} | {row.get('source','-')}</div>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <a href="{row.get('link','#')}" target="_blank" style="color: #eee; font-weight:bold; text-decoration:none; font-size:1rem;">{row.get('text','')}</a>
                    <div style="text-align:right;">
                        <span style="color:{s_col}; font-weight:bold;">{row.get('Label', '-')}</span> <span style="font-size:0.8rem; color:#666;">({row.get('Score', 0)})</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.error("ALL SYSTEMS DOWN. Check connection.")

else:
    st.markdown("""
    <div style="text-align:center; padding: 100px; color:#444;">
        <h1>SYSTEM STANDBY</h1>
        <p>Click REFRESH to initialize market scan.</p>
    </div>
    """, unsafe_allow_html=True)
