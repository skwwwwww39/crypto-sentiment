import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
import os
import requests
from datetime import datetime
import re
from collections import Counter

# --- 1. Cyberpunk Design System ---
st.set_page_config(page_title="Terminal: Crypto Sentinel", layout="wide", page_icon="⚡")

st.markdown("""
<style>
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(circle at 50% 0%, #1a0b2e 0%, #000000 60%);
        color: #e0e0e0;
    }
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        display: flex;
        flex-direction: column;
        justify-content: center;
        height: 100%;
    }
    .kpi-value { font-size: 2.2rem; font-weight: 800; color: #fff; line-height: 1.2; }
    .kpi-label { font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 1px; }
    .kpi-sub { font-size: 0.8rem; margin-top: 5px; opacity: 0.8; }
    
    .stButton > button {
        background: linear-gradient(90deg, #bd00ff, #240046);
        border: 1px solid #bd00ff;
        color: white;
        font-weight: bold;
        padding: 12px 25px;
        border-radius: 4px;
        width: 100%;
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

# --- 3. Data Fetching ---

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
        df_chart['timestamp'] = pd.to_datetime(df_chart['timestamp'], unit='ms')
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
        if "Data" not in data: return []
        news_items = []
        for i, item in enumerate(data["Data"][:limit]):
            title = item.get("title", "")
            source = item.get("source_info", {}).get("name", "CryptoCompare")
            url = item.get("url", "#")
            published_on = item.get("published_on", 0)
            dt_obj = datetime.fromtimestamp(published_on)
            date_str = dt_obj.strftime("%Y-%m-%d %H:%M")
            news_items.append({
                "id": i, "text": title, "date_str": date_str,
                "timestamp": dt_obj, "source": source, "link": url
            })
        return news_items
    except Exception as e:
        st.error(f"API Error: {e}")
        return []

# --- 4. Analytics Modules (Robust Parsing) ---

def analyze_sentiment(news_list):
    if not news_list: return []
    results = []
    batch_size = 10
    
    for i in range(0, len(news_list), batch_size):
        batch = news_list[i:i+batch_size]
        news_block = "\n".join([f"ID {item['id']}: {item['text']}" for item in batch])
        
        prompt = f"""
        Analyze sentiment of these {len(batch)} crypto headlines.
        Return ONLY a list in format: ID|Label|Score
        Label: [Euphoria, Optimism, Positive, Neutral, Negative, Fear, Despair]
        Score: -100 to 100
        NO Markdown. NO bolding.
        
        Headlines:
        {news_block}
        """
        try:
            res = model.generate_content(prompt)
            if not res.text: continue
            
            # ★修正点：正規表現をやめて、泥臭くパースする（データ消失防止）
            lines = res.text.strip().split("\n")
            for line in lines:
                parts = line.split("|")
                if len(parts) >= 3:
                    try:
                        # 余計な文字（*やスペース）を削除して読み込む
                        nid_str = re.sub(r'\D', '', parts[0]) # 数字以外消す
                        if not nid_str: continue
                        nid = int(nid_str)
                        
                        label = parts[1].strip().replace("*", "")
                        
                        score_str = parts[2].strip().replace("*", "")
                        score = int(float(score_str)) # "90.0" とか来てもいいように
                        
                        # IDで紐付け
                        for item in news_list:
                            if item['id'] == nid:
                                # 新しい辞書を作って追加（安全策）
                                new_item = item.copy()
                                new_item['Label'] = label
                                new_item['Score'] = score
                                results.append(new_item)
                                break
                    except:
                        continue
        except Exception as e:
            print(f"Batch Error: {e}")
            continue
    return results

def extract_keywords(df):
    if df.empty: return []
    text = " ".join(df['text'].tolist()).lower()
    ignore = ['to', 'in', 'for', 'of', 'the', 'on', 'and', 'a', 'is', 'at', 'bitcoin', 'crypto', 'price', 'market', 'btc', 'after', 'as', 'with', 'from', 'by', 'vs', 'new', 'top', 'why', 'will', 'news', 'analysis', 'live', '-', '|', 'cryptocurrency', 'says', 'update', 'daily']
    words = re.findall(r'\b\w{3,}\b', text)
    filtered = [w for w in words if w not in ignore and not w.isdigit()]
    return Counter(filtered).most_common(8)

# --- 5. Main Dashboard UI ---

st.title("⚡ TRADER'S COCKPIT: BTC SENTINEL")
st.markdown("REAL-TIME MARKET INTELLIGENCE // CRYPTOCOMPARE API FEED")

if st.button("🔄 REFRESH DATA FEED", type="primary"):
    with st.spinner("📡 PROCESSING DATA..."):
        btc_price, btc_change, btc_chart = get_crypto_price()
        fng_val, fng_class = get_fear_greed_index()
        raw_news = get_real_market_news(limit=25)
        
        df = pd.DataFrame()
        if raw_news:
            analyzed_data = analyze_sentiment(raw_news)
            # データが取れなかった場合（解析失敗時）は生データを表示
            if analyzed_data:
                df = pd.DataFrame(analyzed_data)
            else:
                df = pd.DataFrame(raw_news)
                st.warning("Sentiment analysis unavailable. Displaying raw feed.")

    # --- LAYOUT ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        p_col = "#00ff99" if btc_change >= 0 else "#ff0055"
        st.markdown(f"<div class='glass-card'><div class='kpi-label'>BTC PRICE</div><div class='kpi-value'>${btc_price:,.0f}</div><div class='kpi-sub' style='color:{p_col}'>{btc_change:+.2f}%</div></div>", unsafe_allow_html=True)
    with c2:
        if not df.empty and 'Score' in df.columns:
            sc = df['Score'].mean()
            col = "#00ff99" if sc > 20 else "#ff0055" if sc < -20 else "#bd00ff"
            st.markdown(f"<div class='glass-card'><div class='kpi-label'>AI SENTIMENT</div><div class='kpi-value' style='color:{col}'>{int(sc)}</div><div class='kpi-sub'>Market Mood</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='glass-card'><div class='kpi-label'>AI SENTIMENT</div><div class='kpi-value'>--</div></div>", unsafe_allow_html=True)
    with c3:
        f_col = "#00ff99" if fng_val > 50 else "#ff0055"
        st.markdown(f"<div class='glass-card'><div class='kpi-label'>FEAR & GREED</div><div class='kpi-value' style='color:{f_col}'>{fng_val}</div><div class='kpi-sub'>{fng_class}</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='glass-card'><div class='kpi-label'>SIGNAL DENSITY</div><div class='kpi-value'>{len(df)}</div><div class='kpi-sub'>News Analyzed</div></div>", unsafe_allow_html=True)

    # --- CHARTS ---
    c_left, c_right = st.columns([2, 1])
    
    with c_left:
        st.subheader("📈 Price Action")
        if not btc_chart.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=btc_chart['timestamp'], y=btc_chart['price'], mode='lines', line=dict(color='#00e5ff', width=2)))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#888'), margin=dict(l=0,r=0,t=0,b=0), height=350, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'))
            st.plotly_chart(fig, use_container_width=True)

    with c_right:
        st.subheader("🌊 Sentiment Flow")
        # ★★★ グラフ修正の核心：時間統合とソート ★★★
        if not df.empty and 'Score' in df.columns and 'timestamp' in df.columns:
            chart_df = df.copy()
            chart_df['timestamp'] = pd.to_datetime(chart_df['timestamp'])
            
            # 1. 同じ時間のデータを平均化して「1つの点」にする（ループ回避）
            chart_df = chart_df.groupby('timestamp', as_index=False)['Score'].mean()
            
            # 2. 時間順にソート（逆行回避）
            chart_df = chart_df.sort_values('timestamp')
            
            # 3. 直線で描画
            fig = px.line(chart_df, x='timestamp', y='Score')
            fig.update_traces(line_color='#00ff99', line_shape='linear', fill='tozeroy', fillcolor='rgba(0,255,153,0.1)')
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#888'), margin=dict(l=0,r=0,t=0,b=0), height=350, xaxis=dict(showgrid=False), yaxis=dict(range=[-100,100], gridcolor='rgba(255,255,255,0.1)'))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data for chart.")

    # --- ANALYSIS ---
    c_kw, c_pie = st.columns(2)
    with c_kw:
        st.subheader("🗣 Narrative")
        if not df.empty:
            kw = extract_keywords(df)
            if kw:
                kdf = pd.DataFrame(kw, columns=['word','count'])
                fig = px.bar(kdf, x='count', y='word', orientation='h', color='count', color_continuous_scale='Viridis')
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#e0e0e0', height=300, margin=dict(t=0,b=0))
                st.plotly_chart(fig, use_container_width=True)
    
    with c_pie:
        st.subheader("🥧 Emotions")
        if not df.empty and 'Label' in df.columns:
            cmap = {'Euphoria': '#00FF99', 'Optimism': '#00e5ff', 'Positive': '#3498DB', 'Neutral': '#555', 'Negative': '#F1C40F', 'Fear': '#ff5e00', 'Despair': '#ff0055'}
            fig = px.pie(df, names='Label', hole=0.6, color='Label', color_discrete_map=cmap)
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#e0e0e0', height=300, margin=dict(t=0,b=0))
            st.plotly_chart(fig, use_container_width=True)

    # --- LOGS ---
    st.subheader("📋 Logs")
    if not df.empty:
        df_log = df.sort_values('timestamp', ascending=False) if 'timestamp' in df.columns else df
        for _, row in df_log.iterrows():
            sc = row.get('Score', 0)
            c = "#00ff99" if sc > 0 else "#ff0055" if sc < 0 else "#888"
            st.markdown(f"<div style='border-left:3px solid {c}; padding-left:10px; margin-bottom:5px; background:rgba(255,255,255,0.02)'><div>{row['date_str']} | {row['source']}</div><div style='display:flex; justify-content:space-between'><a href='{row['link']}' style='color:#eee; text-decoration:none'>{row['text']}</a><span style='color:{c}'>{row.get('Label','-')} ({sc})</span></div></div>", unsafe_allow_html=True)

else:
    st.markdown("<div style='text-align:center; padding:50px;'><h1>READY</h1><p>Click REFRESH</p></div>", unsafe_allow_html=True)