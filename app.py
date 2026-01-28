import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import os
import time
import requests
from datetime import datetime

# --- 1. アプリ設定と超豪華デザインCSS ---
st.set_page_config(page_title="Cyberpunk Crypto Dashboard", layout="wide", page_icon="🔮")

st.markdown("""
<style>
    /* 全体の背景：深い紫から黒への没入感あるグラデーション */
    .stApp {
        background: radial-gradient(circle at center top, #240046 0%, #0a0015 80%);
        color: #FAFAFA;
        font-family: 'Helvetica Neue', sans-serif;
    }

    /* --- アニメーション定義 --- */
    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(30px) scale(0.95); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }
    @keyframes neonPulse {
        0% { box-shadow: 0 0 5px #bd00ff, 0 0 10px #bd00ff, 0 0 20px #bd00ff; }
        50% { box-shadow: 0 0 10px #00e5ff, 0 0 20px #00e5ff, 0 0 40px #00e5ff; }
        100% { box-shadow: 0 0 5px #bd00ff, 0 0 10px #bd00ff, 0 0 20px #bd00ff; }
    }

    /* --- グラスモーフィズム＆サイバーパンクカード --- */
    .metric-card {
        /* ガラスの質感 */
        background: rgba(20, 0, 40, 0.5); /* 半透明の深い紫 */
        backdrop-filter: blur(15px) saturate(150%); /* 背景ぼかしと彩度強調 */
        -webkit-backdrop-filter: blur(15px) saturate(150%);
        border: 1px solid rgba(189, 0, 255, 0.3); /* 薄いネオン紫の枠 */
        border-top: 1px solid rgba(255, 255, 255, 0.2); /* 上部に光の反射 */
        
        padding: 25px;
        border-radius: 16px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5); /* 深い影 */
        
        /* アニメーションとトランジション */
        animation: fadeUp 0.8s ease-out forwards;
        transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1); /* 滑らかな動き */
    }

    /* ホバー時の強烈な発光エフェクト */
    .metric-card:hover {
        transform: translateY(-10px) scale(1.02); /* 浮き上がる */
        border-color: rgba(189, 0, 255, 0.8);
        background: rgba(40, 0, 70, 0.6);
        /* ネオンの輝き */
        box-shadow: 
            0 15px 40px rgba(0, 0, 0, 0.7),
            0 0 20px rgba(189, 0, 255, 0.4),
            0 0 50px rgba(0, 229, 255, 0.2) inset; /* 内側にも青い光 */
    }

    /* テキストスタイル */
    .metric-label {
        color: #e0c0ff; /* 薄紫 */
        font-size: 1rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 10px;
        text-shadow: 0 0 5px rgba(189, 0, 255, 0.5);
    }
    .metric-value {
        color: #ffffff;
        font-size: 2.5rem;
        font-weight: 800;
        text-shadow: 0 0 15px rgba(0, 229, 255, 0.8); /* 青白い発光 */
    }

    /* ボタンのデザインをサイバーパンクに */
    .stButton > button {
        background: linear-gradient(135deg, #bd00ff, #00e5ff);
        border: none;
        color: white;
        padding: 15px 30px;
        font-size: 1.2rem;
        font-weight: bold;
        border-radius: 50px;
        box-shadow: 0 0 20px rgba(189, 0, 255, 0.5);
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 0 40px rgba(0, 229, 255, 0.8);
    }
    /* Streamlitの標準要素の背景を透明にしてガラス感を高める */
    div[data-testid="stExpander"], div[data-testid="stDataFrame"] {
        background: rgba(20, 0, 40, 0.3);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        border: 1px solid rgba(189, 0, 255, 0.2);
    }
    
    /* タイトルの装飾 */
    h1 {
        text-align: center;
        font-weight: 900;
        background: linear-gradient(to right, #bd00ff, #00e5ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 30px rgba(189, 0, 255, 0.5);
        margin-bottom: 40px;
    }

</style>
""", unsafe_allow_html=True)

# --- 2. 設定 (APIキーなど) ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-flash-latest')

# CryptoPanic APIキー
CRYPTOPANIC_API_KEY = "ce5d1a3effe7a877dcf19adbce33ef35ded05f5e"

# --- 3. データ取得関数 ---
def get_real_news():
    url = f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTOPANIC_API_KEY}&public=true&filter=rising"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        news_items = []
        if "results" in data:
            for item in data["results"][:8]:
                title = item["title"]
                currencies = [c["code"] for c in item.get("currencies", [])]
                currency_label = f" ({', '.join(currencies)})" if currencies else ""
                published_at = item["created_at"][:10]
                news_items.append({
                    "text": f"{title}{currency_label}",
                    "date": published_at,
                    "source": item["domain"]
                })
        return news_items
    except Exception as e:
        st.error(f"ニュース取得エラー: {e}")
        return []

# --- 4. AI分析関数 ---
def analyze_sentiment(text):
    if not api_key: return "Neutral", 0
    prompt = f"""
    Analyze the sentiment of this crypto news: "{text}"
    Classify into exactly one: [Despair, Fear, Negative, Positive, Optimism, Euphoria]
    Score from -100 (Despair) to 100 (Euphoria).
    Output format: Label:Label, Score:Number
    """
    try:
        response = model.generate_content(prompt)
        content = response.text
        label = "Neutral"
        score = 0
        if "Label:" in content:
            label = content.split("Label:")[1].split(",")[0].strip().split("\n")[0]
        if "Score:" in content:
            import re
            numbers = re.findall(r'-?\d+', content.split("Score:")[1])
            if numbers: score = int(numbers[0])
        return label, score
    except:
        return "Neutral", 0

# --- 5. メイン画面 UI ---
st.title("🔮 Cyberpunk Sentiment Core")

# 実行ボタン
if st.button("INITIALIZE NEURAL LINK & ANALYZE 🔄"):
    
    with st.spinner("📡 Establishing connection to global feed..."):
        news_data = get_real_news()
    
    if not news_data:
        st.warning("Signal lost. No news found.")
    else:
        results = []
        # プログレスバーもサイバー風に
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, item in enumerate(news_data):
            # 分析中のテキストを点滅させるような演出
            status_text.markdown(f"Processing data packet **[{i+1}/{len(news_data)}]** > `{item['text'][:40]}...`")
            label, score = analyze_sentiment(item['text'])
            results.append({"Date": item['date'], "Source": item['source'], "Text": item['text'], "Label": label, "Score": score})
            time.sleep(0.3)
            progress_bar.progress((i + 1) / len(news_data))
            
        status_text.empty()
        progress_bar.empty()
        df = pd.DataFrame(results)
        
        # --- ダッシュボード描画 ---
        st.markdown("---")
        
        avg_score = df['Score'].mean()
        
        # ムードに応じた色とアイコン定義
        if avg_score >= 60: mood, color = "EUPHORIA 🚀", "#00FF99"
        elif avg_score >= 20: mood, color = "OPTIMISM 📈", "#00e5ff"
        elif avg_score <= -60: mood, color = "DESPAIR 💀", "#ff0055"
        elif avg_score <= -20: mood, color = "FEAR 😱", "#ff5e00"
        else: mood, color = "NEUTRAL 😐", "#bd00ff"

        # KPIカード表示（アニメーション適用のためdelayを追加）
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
            <div class="metric-card" style="animation-delay: 0.1s;">
                <div class="metric-label">Current Market Vibe</div>
                <div class="metric-value" style="color: {color}; text-shadow: 0 0 20px {color};">{mood}</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="metric-card" style="animation-delay: 0.2s;">
                <div class="metric-label">Neural Sentiment Score</div>
                <div class="metric-value">{int(avg_score)}</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="metric-card" style="animation-delay: 0.3s;">
                <div class="metric-label">Data Packets Analyzed</div>
                <div class="metric-value">{len(df)}</div>
            </div>""", unsafe_allow_html=True)

        # グラフエリア
        st.subheader("📊 Neural Analysis Visuals")
        c_left, c_right = st.columns([2, 1])
        
        with c_left:
            # 棒グラフのデザイン調整
            fig_bar = px.bar(df, x="Score", y="Text", orientation='h', color="Score", 
                             color_continuous_scale=['#ff0055', '#bd00ff', '#00e5ff', '#00FF99'], range_x=[-100, 100])
            fig_bar.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#e0c0ff',
                yaxis={'visible': False}, xaxis=dict(gridcolor='rgba(189, 0, 255, 0.2)'),
                coloraxis_colorbar=dict(title="Score")
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with c_right:
            # ドーナツチャートのデザイン調整
            color_map = {"Euphoria": "#00FF99", "Optimism": "#00e5ff", "Positive": "#3498DB", "Neutral": "#bd00ff", "Negative": "#F1C40F", "Fear": "#ff5e00", "Despair": "#ff0055"}
            fig_pie = px.pie(df, names="Label", hole=0.5, color="Label", color_discrete_map=color_map)
            fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#e0c0ff', showlegend=False)
            # サイバーな雰囲気を出すための注釈を追加
            fig_pie.add_annotation(text="SENTIMENT<br>DISTRIBUTION", showarrow=False, font=dict(color="white", size=12))
            st.plotly_chart(fig_pie, use_container_width=True)

        with st.expander("📄 View Raw Data Logs"):
            st.dataframe(df[["Date", "Source", "Label", "Score", "Text"]], use_container_width=True, hide_index=True)

else:
    # 初期画面の案内もサイバー風に
    st.markdown("""
    <div style='text-align: center; padding: 50px; color: #bd00ff; animation: neonPulse 3s infinite alternate;'>
        <h3>AWAITING ACTIVATION</h3>
        <p>Click the button above to initialize the neural link and scan global crypto feeds.</p>
    </div>
    """, unsafe_allow_html=True)