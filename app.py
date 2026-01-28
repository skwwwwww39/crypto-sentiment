import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import os
import time
import feedparser # ★ここが新しい主役（ブロックされない）
from datetime import datetime

# --- 1. デザイン設定 ---
st.set_page_config(page_title="Crypto RSS Sentinel", layout="wide", page_icon="⚡")

st.markdown("""
<style>
    .stApp {
        background: radial-gradient(circle at center top, #1a0b2e 0%, #000000 100%);
        color: #e0e0e0;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(189, 0, 255, 0.2);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        text-shadow: 0 0 10px rgba(0, 229, 255, 0.6);
        color: #fff;
    }
    .metric-label {
        color: #b39ddb;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. API設定 ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-flash-latest')

# --- 3. データ取得 (RSSフィード) ---
def get_rss_news():
    """
    Yahoo FinanceのRSSフィードからニュースを取得する。
    API制限に引っかからない最強の方法。
    """
    # Yahoo FinanceのBTCニュースフィード
    rss_url = "https://finance.yahoo.com/rss/headline?s=BTC-USD"
    
    status_container = st.empty()
    status_container.info("📡 Connecting to Global RSS Feed...")
    
    try:
        feed = feedparser.parse(rss_url)
        
        if not feed.entries:
            status_container.warning("No entries found in RSS feed.")
            return []
            
        news_items = []
        for i, entry in enumerate(feed.entries):
            # 必要な情報を抽出
            title = entry.title
            link = entry.link
            published = entry.published if 'published' in entry else "Recent"
            
            # 日付の整形（読みやすくする）
            try:
                # RSSの日付形式を変換
                dt = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %z")
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                date_str = published

            news_items.append({
                "id": i,
                "text": title,
                "date": date_str,
                "source": "Yahoo Finance RSS",
                "link": link
            })
            
        status_container.empty()
        return news_items
        
    except Exception as e:
        status_container.error(f"RSS Error: {e}")
        return []

# --- 4. バッチ分析 ---
def analyze_batch(news_list):
    """ニュースをまとめてAIに分析させる"""
    if not api_key: return []
    if not news_list: return []
    
    results = []
    # ニュースのリストをテキストブロックに変換
    news_text_block = "\n".join([f"ID {item['id']}: {item['text']}" for item in news_list])
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.markdown("🧠 AI Analyzing Market Sentiment...")
    
    prompt = f"""
    Analyze the sentiment of these crypto news headlines.
    Output a list of ID, Label, and Score.
    
    Constraints:
    - Label must be one of: [Despair, Fear, Negative, Positive, Optimism, Euphoria]
    - Score must be between -100 (Despair) and 100 (Euphoria)
    - Format per line: ID | Label | Score
    
    Headlines:
    {news_text_block}
    """
    
    try:
        response = model.generate_content(prompt)
        lines = response.text.strip().split("\n")
        
        for line in lines:
            parts = line.split("|")
            if len(parts) == 3:
                try:
                    n_id = int(parts[0].replace("ID", "").strip())
                    label = parts[1].strip()
                    score = int(parts[2].strip())
                    
                    # IDで元のデータと紐付け
                    for item in news_list:
                        if item['id'] == n_id:
                            item['Label'] = label
                            item['Score'] = score
                            results.append(item)
                except:
                    continue
    except Exception as e:
        print(f"Analysis Error: {e}")
    
    progress_bar.progress(100)
    time.sleep(0.5)
    status_text.empty()
    progress_bar.empty()
    return results

# --- 5. メインUI ---
st.title("⚡ Crypto Sentiment Core (RSS)")
st.markdown("Fetching real-time data via **RSS Feeds** (Anti-Block Technology).")

# ボタン
if st.button("FETCH & ANALYZE 🔄", type="primary"):
    
    # 1. データ取得
    raw_news = get_rss_news()
    
    if not raw_news:
        st.error("❌ Failed to fetch data.")
    else:
        # 2. AI分析
        analyzed_data = analyze_batch(raw_news)
        
        if len(analyzed_data) == 0:
            st.error("❌ AI Analysis failed. Please check Gemini API Key.")
        else:
            df = pd.DataFrame(analyzed_data)

            # --- 結果表示 ---
            st.divider()
            
            # KPI
            avg_score = df['Score'].mean()
            if avg_score >= 60: mood, color = "EUPHORIA 🚀", "#00FF99"
            elif avg_score >= 20: mood, color = "OPTIMISM 📈", "#00e5ff"
            elif avg_score <= -60: mood, color = "DESPAIR 💀", "#ff0055"
            elif avg_score <= -20: mood, color = "FEAR 😱", "#ff5e00"
            else: mood, color = "NEUTRAL 😐", "#bd00ff"

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Market Mood</div>
                    <div class="metric-value" style="color:{color}">{mood}</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Avg Sentiment Score</div>
                    <div class="metric-value">{int(avg_score)}</div>
                </div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Headlines Analyzed</div>
                    <div class="metric-value">{len(df)}</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("---")

            # グラフエリア
            col_left, col_right = st.columns([2, 1])

            with col_left:
                st.subheader("📊 Sentiment Spectrum")
                st.markdown("<div style='text-align:center; color:#888; margin-bottom:5px;'>Left: Bearish | Right: Bullish</div>", unsafe_allow_html=True)
                
                fig_bar = px.bar(
                    df, 
                    x="Score", 
                    y="text", # Y軸をタイトルに
                    color="Score",
                    orientation='h',
                    color_continuous_scale=['#ff0055', '#bd00ff', '#00e5ff', '#00FF99'],
                    range_x=[-100, 100],
                )
                fig_bar.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)', 
                    font_color='#e0c0ff',
                    yaxis={'visible': False} # タイトルが長いので隠す（ホバーで見れる）
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            with col_right:
                st.subheader("🥧 Emotion Ratio")
                color_map = {
                    "Euphoria": "#00FF99", "Optimism": "#00e5ff", 
                    "Positive": "#3498DB", "Neutral": "#bd00ff", 
                    "Negative": "#F1C40F", "Fear": "#ff5e00", "Despair": "#ff0055"
                }
                fig_pie = px.pie(
                    df, 
                    names="Label", 
                    hole=0.6, 
                    color="Label", 
                    color_discrete_map=color_map
                )
                fig_pie.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', 
                    font_color='#e0c0ff',
                    legend=dict(orientation="h", y=-0.1)
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            # 詳細リスト
            with st.expander(f"📋 View News List"):
                for index, row in df.iterrows():
                    st.markdown(f"**{row['date']}**: [{row['text']}]({row['link']}) - *{row['Label']} ({row['Score']})*")