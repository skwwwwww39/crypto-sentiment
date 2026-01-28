import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import os
import time
import requests
import random
from datetime import datetime, timedelta

# --- 1. アプリ設定とデザイン ---
st.set_page_config(page_title="Cyberpunk Crypto Dashboard", layout="wide", page_icon="🔮")

st.markdown("""
<style>
    /* 全体背景 */
    .stApp {
        background: radial-gradient(circle at center top, #240046 0%, #0a0015 80%);
        color: #FAFAFA;
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    /* アニメーション */
    @keyframes fadeUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    
    /* カードデザイン */
    .metric-card {
        background: rgba(20, 0, 40, 0.6);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(189, 0, 255, 0.3);
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 10px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        animation: fadeUp 0.6s ease-out forwards;
    }
    .metric-label { color: #bd00ff; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 5px; }
    .metric-value { color: #fff; font-size: 2rem; font-weight: 800; text-shadow: 0 0 10px rgba(189, 0, 255, 0.6); }

    /* ボタン */
    .stButton > button {
        background: linear-gradient(90deg, #bd00ff, #00e5ff);
        border: none; color: white; font-weight: bold; padding: 12px 24px; border-radius: 30px;
        width: 100%; transition: transform 0.2s;
        box-shadow: 0 0 15px rgba(189, 0, 255, 0.4);
    }
    .stButton > button:hover { transform: scale(1.02); box-shadow: 0 0 25px rgba(0, 229, 255, 0.6); }

    /* グラフの説明文 */
    .chart-desc { font-size: 0.8rem; color: #aaa; text-align: center; margin-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 2. 設定 ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-flash-latest')

CRYPTOPANIC_API_KEY = "ce5d1a3effe7a877dcf19adbce33ef35ded05f5e"

# --- 3. データ取得 (強化版) ---
def get_real_news():
    # filter=hot に変更してニュースを取りやすくする
    url = f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTOPANIC_API_KEY}&public=true&filter=hot"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200: return []
        
        data = response.json()
        news_items = []
        if "results" in data:
            # 取得数を20件に増やす
            for item in data["results"][:20]:
                title = item["title"]
                currencies = [c["code"] for c in item.get("currencies", [])]
                currency_label = f" ({', '.join(currencies)})" if currencies else ""
                # 日付のフォーマット調整
                date_str = item["created_at"].replace("T", " ")[:16] 
                
                news_items.append({
                    "text": f"{title}{currency_label}",
                    "date": date_str,
                    "source": item["domain"]
                })
        return news_items
    except:
        return []

def generate_fallback_data():
    """データ量不足時の拡張シミュレーションデータ"""
    base_time = datetime.now()
    data = [
        ("Bitcoin surges past resistance, eyes on $100k target! 🚀", "Euphoria"),
        ("Ethereum gas fees hit 6-month low, network activity rising.", "Optimism"),
        ("SEC delays ETF decision again, market uncertain.", "Fear"),
        ("Solana network halted for 2 hours, devs investigating.", "Negative"),
        ("Whale wallet moves 5000 BTC to exchange, possible dump?", "Fear"),
        ("New regulatory framework in EU looks promising for DeFi.", "Positive"),
        ("DOGE jumps 20% after Elon Musk tweet.", "Euphoria"),
        ("Market consolidation continues, low volume weekend.", "Neutral"),
        ("Hacker steals $50M from bridge, warning issued.", "Despair"),
        ("Cardano upgrade goes live successfully.", "Positive"),
        ("Traders are shorting BNB heavily right now.", "Negative"),
        ("Global adoption of crypto payments increasing in Asia.", "Optimism"),
        ("Inflation data comes in hot, crypto correlates with stocks.", "Fear"),
        ("XRP wins minor legal battle, community celebrates.", "Euphoria"),
        ("Top analyst predicts bear market is officially over.", "Optimism")
    ]
    
    fallback_items = []
    for i, (txt, mood) in enumerate(data):
        # 時間を少しずつずらす
        t = base_time - timedelta(minutes=i*15)
        fallback_items.append({
            "text": txt,
            "source": "Simulation Feed",
            "date": t.strftime("%Y-%m-%d %H:%M")
        })
    return fallback_items

# --- 4. AI分析 ---
def analyze_sentiment(text):
    if not api_key: return "Neutral", 0
    # プロンプト調整：明確にスコアを出すように指示
    prompt = f"""
    Analyze sentiment of: "{text}"
    Classify one of: [Despair, Fear, Negative, Neutral, Positive, Optimism, Euphoria]
    Score: -100(Despair) to 100(Euphoria).
    Output: Label:Label, Score:Number
    """
    try:
        response = model.generate_content(prompt)
        content = response.text
        label, score = "Neutral", 0
        
        if "Label:" in content:
            label = content.split("Label:")[1].split(",")[0].strip().split("\n")[0]
        if "Score:" in content:
            import re
            nums = re.findall(r'-?\d+', content.split("Score:")[1])
            if nums: score = int(nums[0])
            
        return label, score
    except:
        return "Neutral", 0

# --- 5. メイン画面 ---
st.title("🔮 Cyberpunk Sentiment Core v2")

if st.button("SCAN GLOBAL MARKETS (START) 🔄"):
    
    with st.spinner("📡 Intercepting global crypto signals..."):
        news_data = get_real_news()
        is_simulation = False
        
        if not news_data:
            st.toast("Connection unstable. Engaging Simulation Mode.", icon="⚠️")
            news_data = generate_fallback_data()
            is_simulation = True
            time.sleep(1)

    # データ期間の取得
    dates = [d['date'] for d in news_data]
    period_start = min(dates)
    period_end = max(dates)
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, item in enumerate(news_data):
        status_text.caption(f"Analyzing packet {i+1}/{len(news_data)}: {item['text'][:40]}...")
        label, score = analyze_sentiment(item['text'])
        results.append({**item, "Label": label, "Score": score})
        time.sleep(0.1) # 高速化
        progress_bar.progress((i + 1) / len(news_data))
        
    status_text.empty()
    progress_bar.empty()
    df = pd.DataFrame(results)
    
    # --- 結果表示 ---
    st.divider()
    
    # 期間表示
    source_label = "🔴 LIVE FEED (CryptoPanic)" if not is_simulation else "⚠️ SIMULATION DATA"
    st.markdown(f"""
    <div style='display:flex; justify-content:space-between; color:#888; font-size:0.8rem; margin-bottom:10px;'>
        <span>SOURCE: <b>{source_label}</b></span>
        <span>PERIOD: <b>{period_start} 〜 {period_end}</b></span>
    </div>
    """, unsafe_allow_html=True)

    # KPI
    avg_score = df['Score'].mean()
    if avg_score >= 60: mood, col = "EUPHORIA 🚀", "#00FF99"
    elif avg_score >= 20: mood, col = "OPTIMISM 📈", "#00e5ff"
    elif avg_score <= -60: mood, col = "DESPAIR 💀", "#ff0055"
    elif avg_score <= -20: mood, col = "FEAR 😱", "#ff5e00"
    else: mood, col = "NEUTRAL 😐", "#bd00ff"

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Market Mood</div><div class='metric-value' style='color:{col}; text-shadow:0 0 15px {col}'>{mood}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Sentiment Score</div><div class='metric-value'>{int(avg_score)}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Posts Analyzed</div><div class='metric-value'>{len(df)}</div></div>", unsafe_allow_html=True)

    # グラフエリア
    st.subheader("📊 Visual Analysis")
    
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.markdown("<div class='chart-desc'>記事ごとの感情スコア分布 (右に行くほどポジティブ)</div>", unsafe_allow_html=True)
        fig_bar = px.bar(
            df, x="Score", y="Text", orientation='h', 
            color="Score", color_continuous_scale=['#ff0055', '#bd00ff', '#00e5ff', '#00FF99'],
            range_x=[-100, 100]
        )
        fig_bar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#e0c0ff',
            yaxis={'visible': False}, 
            xaxis=dict(title="← Bearish (弱気) ｜ Bullish (強気) →", gridcolor='rgba(255,255,255,0.1)'),
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        st.markdown("<div class='chart-desc'>感情ラベルの割合</div>", unsafe_allow_html=True)
        color_map = {"Euphoria": "#00FF99", "Optimism": "#00e5ff", "Positive": "#3498DB", 
                     "Neutral": "#bd00ff", "Negative": "#F1C40F", "Fear": "#ff5e00", "Despair": "#ff0055"}
        fig_pie = px.pie(df, names="Label", hole=0.4, color="Label", color_discrete_map=color_map)
        fig_pie.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', font_color='#e0c0ff',
            showlegend=True, legend=dict(orientation="h", y=-0.1)
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with st.expander("📄 データ詳細ログを見る"):
        st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.info("👆 ボタンを押して分析を開始してください")