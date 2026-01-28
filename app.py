import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
import os
import time
import feedparser
from datetime import datetime

# --- 1. 超リッチなデザイン設定 (Cyberpunk UI) ---
st.set_page_config(page_title="Cyberpunk Crypto Core", layout="wide", page_icon="🔮")

st.markdown("""
<style>
    /* 全体の背景：深い没入感のあるグラデーション */
    .stApp {
        background: radial-gradient(circle at center top, #1a0b2e 0%, #000000 100%);
        color: #e0e0e0;
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    /* アニメーション定義 */
    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(189, 0, 255, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(189, 0, 255, 0); }
        100% { box-shadow: 0 0 0 0 rgba(189, 0, 255, 0); }
    }

    /* ガラス調カードデザイン */
    .metric-card {
        background: rgba(20, 20, 35, 0.6);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(189, 0, 255, 0.3);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        animation: fadeUp 0.6s ease-out forwards;
        margin-bottom: 20px;
        position: relative;
        overflow: hidden;
    }
    
    /* カードのホバーエフェクト */
    .metric-card:hover {
        transform: translateY(-5px);
        border-color: #00e5ff;
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.4);
    }
    
    /* カード内のテキスト */
    .metric-label {
        color: #b39ddb;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #fff 0%, #a0a0a0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 20px rgba(189, 0, 255, 0.5);
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #00e5ff;
        margin-top: 5px;
    }

    /* ボタンデザイン */
    .stButton > button {
        background: linear-gradient(90deg, #bd00ff, #00e5ff);
        border: none;
        color: white;
        font-weight: bold;
        padding: 12px 30px;
        border-radius: 30px;
        box-shadow: 0 0 15px rgba(189, 0, 255, 0.6);
        transition: all 0.3s;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 30px rgba(0, 229, 255, 0.8);
    }

    /* タイトル装飾 */
    h1 {
        text-align: center;
        font-weight: 900;
        letter-spacing: -1px;
        background: linear-gradient(to right, #bd00ff, #00e5ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 40px;
        filter: drop-shadow(0 0 10px rgba(189,0,255,0.5));
    }
</style>
""", unsafe_allow_html=True)

# --- 2. API設定 ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("🚨 APIキーが見つかりません。")
    st.stop()

genai.configure(api_key=api_key)
# ★無料枠が多いLiteモデル
model_name = 'gemini-flash-lite-latest' 
model = genai.GenerativeModel(model_name)

# --- 3. データ取得 (RSS - Yahoo Finance) ---
def get_rss_news(limit=25): # 情報量を増やすため25件に増量
    rss_url = "https://finance.yahoo.com/rss/headline?s=BTC-USD"
    try:
        feed = feedparser.parse(rss_url)
        if not feed.entries: return []
        news_items = []
        for i, entry in enumerate(feed.entries[:limit]):
            title = entry.title
            link = entry.link
            published = entry.published if 'published' in entry else "Recent"
            try:
                dt = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %z")
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                date_str = published
            news_items.append({"id": i, "text": title, "date": date_str, "source": "Yahoo Finance", "link": link})
        return news_items
    except Exception as e:
        st.error(f"RSS Error: {e}")
        return []

# --- 4. 一括分析 ---
def analyze_all_at_once(news_list):
    if not news_list: return []
    results = []
    news_text_block = "\n".join([f"ID {item['id']}: {item['text']}" for item in news_list])
    
    # プロンプト：より厳密なJSON形式のような出力を要求
    prompt = f"""
    Analyze sentiment of these {len(news_list)} crypto headlines.
    Return ONLY a list: ID | Label | Score
    Label options: [Despair, Fear, Negative, Positive, Optimism, Euphoria]
    Score: -100 to 100
    
    Headlines:
    {news_text_block}
    """
    try:
        response = model.generate_content(prompt)
        if not response.text: return []
        lines = response.text.strip().split("\n")
        for line in lines:
            parts = line.split("|")
            if len(parts) == 3:
                try:
                    n_id = int(parts[0].replace("ID", "").strip())
                    label = parts[1].strip()
                    score = int(parts[2].strip())
                    for item in news_list:
                        if item['id'] == n_id:
                            item['Label'] = label
                            item['Score'] = score
                            results.append(item)
                except:
                    continue
        return results
    except Exception as e:
        st.error(f"AI Error: {e}")
        return []

# --- 5. メインUI ---
st.title("🔮 CYBERPUNK SENTIMENT CORE")
st.markdown(f"<div style='text-align: center; color: #666; margin-top: -20px; margin-bottom: 30px;'>SYSTEM: ONLINE | MODEL: {model_name} | SOURCE: YAHOO FINANCE GLOBAL</div>", unsafe_allow_html=True)

if st.button("INITIALIZE SCAN sequence 🔄", type="primary"):
    
    with st.spinner("📡 INTERCEPTING GLOBAL MARKET SIGNALS..."):
        raw_news = get_rss_news(limit=20) # 20件取得
        
        if not raw_news:
            st.error("SIGNAL LOST.")
        else:
            analyzed_data = analyze_all_at_once(raw_news)
            
            if not analyzed_data:
                st.warning("NO DATA DECODED.")
                df = pd.DataFrame(raw_news)
            else:
                df = pd.DataFrame(analyzed_data)

            # --- KPI 計算 ---
            avg_score = df['Score'].mean()
            post_count = len(df)
            
            # ムード判定
            if avg_score >= 60: mood, color, icon = "EUPHORIA", "#00FF99", "🚀"
            elif avg_score >= 20: mood, color, icon = "OPTIMISM", "#00e5ff", "📈"
            elif avg_score <= -60: mood, color, icon = "DESPAIR", "#ff0055", "💀"
            elif avg_score <= -20: mood, color, icon = "FEAR", "#ff5e00", "😱"
            else: mood, color, icon = "NEUTRAL", "#bd00ff", "😐"
            
            # 最もポジティブ/ネガティブなニュース
            top_bull = df.loc[df['Score'].idxmax()]
            top_bear = df.loc[df['Score'].idxmin()]

            # --- 上部 KPI カード (4枚構成) ---
            c1, c2, c3, c4 = st.columns(4)
            
            with c1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Market Mood</div>
                    <div class="metric-value" style="color: {color}; text-shadow: 0 0 15px {color};">{mood}</div>
                    <div class="metric-sub">{icon} System Status</div>
                </div>""", unsafe_allow_html=True)
                
            with c2:
                st.markdown(f"""
                <div class="metric-card" style="animation-delay: 0.1s;">
                    <div class="metric-label">Sentiment Score</div>
                    <div class="metric-value">{int(avg_score)}</div>
                    <div class="metric-sub">Range: -100 to 100</div>
                </div>""", unsafe_allow_html=True)

            with c3:
                st.markdown(f"""
                <div class="metric-card" style="animation-delay: 0.2s;">
                    <div class="metric-label">Signal Density</div>
                    <div class="metric-value">{post_count}</div>
                    <div class="metric-sub">Packets Analyzed</div>
                </div>""", unsafe_allow_html=True)
                
            with c4:
                # 勢い（ボラティリティ的なもの）を簡易計算
                volatility = df['Score'].std()
                st.markdown(f"""
                <div class="metric-card" style="animation-delay: 0.3s;">
                    <div class="metric-label">Volatility Index</div>
                    <div class="metric-value">{int(volatility) if not pd.isna(volatility) else 0}</div>
                    <div class="metric-sub">Sentiment Deviation</div>
                </div>""", unsafe_allow_html=True)

            # --- グラフセクション ---
            col_graph_left, col_graph_right = st.columns([2, 1])

            with col_graph_left:
                st.markdown("### 📊 Sentiment Spectrum Analysis")
                # バーチャート
                fig_bar = px.bar(
                    df, y="text", x="Score", orientation='h', color="Score",
                    color_continuous_scale=['#ff0055', '#bd00ff', '#00e5ff', '#00FF99'],
                    range_x=[-100, 100], text="Label"
                )
                fig_bar.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e0e0e0', family="Arial"),
                    yaxis=dict(showticklabels=False), # テキストが長いのでY軸ラベルは隠す
                    xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                    margin=dict(l=0, r=0, t=0, b=0),
                    height=350
                )
                fig_bar.update_traces(textposition='inside')
                st.plotly_chart(fig_bar, use_container_width=True)

            with col_graph_right:
                st.markdown("### 🥧 Emotion Distribution")
                # ドーナツチャート（Plotly Graph Objectsでリッチに）
                labels = df['Label'].value_counts().index
                values = df['Label'].value_counts().values
                colors = {'Euphoria': '#00FF99', 'Optimism': '#00e5ff', 'Positive': '#3498DB', 
                          'Neutral': '#bd00ff', 'Negative': '#F1C40F', 'Fear': '#ff5e00', 'Despair': '#ff0055'}
                marker_colors = [colors.get(l, '#888') for l in labels]

                fig_pie = go.Figure(data=[go.Pie(
                    labels=labels, values=values, hole=.5,
                    marker=dict(colors=marker_colors, line=dict(color='#000000', width=2))
                )])
                fig_pie.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e0e0e0'),
                    margin=dict(l=20, r=20, t=0, b=0),
                    height=350,
                    showlegend=True,
                    legend=dict(orientation="h", y=-0.1)
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            # --- 詳細ニュースリスト (情報過多デザイン) ---
            st.markdown("### 📋 DECODED INTELLIGENCE LOGS")
            
            for index, row in df.iterrows():
                # スコアに応じた色
                s_color = "#00FF99" if row['Score'] > 20 else "#ff0055" if row['Score'] < -20 else "#bd00ff"
                
                # HTMLでリッチなリスト表示
                st.markdown(f"""
                <div style="
                    background: rgba(255,255,255,0.03); 
                    border-left: 4px solid {s_color};
                    padding: 15px; 
                    margin-bottom: 10px; 
                    border-radius: 4px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;">
                    <div>
                        <div style="font-size: 0.8rem; color: #888;">{row['date']} | ID: {row['id']}</div>
                        <div style="font-size: 1.1rem; font-weight: bold; color: #fff;">
                            <a href="{row['link']}" target="_blank" style="text-decoration: none; color: #fff;">{row['text']}</a>
                        </div>
                    </div>
                    <div style="text-align: right; min-width: 100px;">
                        <div style="font-size: 1.2rem; font-weight: bold; color: {s_color};">{row['Label']}</div>
                        <div style="font-size: 0.9rem; color: #aaa;">Score: {row['Score']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)