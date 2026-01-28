import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import os
import time
import feedparser
from datetime import datetime

# --- 1. デザイン設定 ---
st.set_page_config(page_title="Crypto RSS Sentinel", layout="wide", page_icon="⚡")

st.markdown("""
<style>
    .stApp { background: radial-gradient(circle at center top, #1a0b2e 0%, #000000 100%); color: #e0e0e0; }
    .metric-card { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(189, 0, 255, 0.2); backdrop-filter: blur(10px); border-radius: 12px; padding: 20px; text-align: center; }
    .metric-value { font-size: 2.2rem; font-weight: 700; color: #fff; }
    .metric-label { color: #b39ddb; font-size: 0.9rem; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# --- 2. API設定 ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("🚨 APIキーが見つかりません。Streamlit CloudのSecretsに 'GEMINI_API_KEY' を設定してください。")
    st.stop()

genai.configure(api_key=api_key)

# ★修正完了：画像にあった正しいモデル名 'gemini-flash-latest' に設定しました
model_name = 'gemini-flash-latest'
model = genai.GenerativeModel(model_name)

# --- 3. データ取得 (RSS) ---
def get_rss_news():
    rss_url = "https://finance.yahoo.com/rss/headline?s=BTC-USD"
    status = st.empty()
    status.info("📡 Connecting to RSS Feed...")
    try:
        feed = feedparser.parse(rss_url)
        if not feed.entries: return []
        news_items = []
        for i, entry in enumerate(feed.entries):
            title = entry.title
            link = entry.link
            published = entry.published if 'published' in entry else "Recent"
            try:
                dt = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %z")
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                date_str = published
            news_items.append({"id": i, "text": title, "date": date_str, "source": "Yahoo RSS", "link": link})
        status.empty()
        return news_items
    except Exception as e:
        st.error(f"RSS Error: {e}")
        return []

# --- 4. バッチ分析 ---
def analyze_batch(news_list):
    results = []
    news_text_block = "\n".join([f"ID {item['id']}: {item['text']}" for item in news_list])
    
    progress = st.progress(0)
    status = st.empty()
    status.markdown(f"🧠 AI Analyzing with **{model_name}**...")
    
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
        if not response.text:
            st.error("⚠️ AIからの応答が空でした。")
            return []
            
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
    except Exception as e:
        st.error(f"💥 AI分析エラー詳細: {e}")
    
    progress.progress(100)
    time.sleep(0.5)
    status.empty()
    progress.empty()
    return results

# --- 5. メインUI ---
st.title("⚡ Crypto Sentiment Core")

if st.button("FETCH & ANALYZE 🔄", type="primary"):
    raw_news = get_rss_news()
    if not raw_news:
        st.error("❌ Failed to fetch RSS data.")
    else:
        analyzed_data = analyze_batch(raw_news)
        if len(analyzed_data) == 0:
            st.warning("データは取得できましたが、AI分析結果が0件でした。")
        else:
            df = pd.DataFrame(analyzed_data)
            st.divider()
            
            # 結果表示
            avg = df['Score'].mean()
            if avg>=60: m,c="EUPHORIA","#00FF99"
            elif avg>=20: m,c="OPTIMISM","#00e5ff"
            elif avg<=-60: m,c="DESPAIR","#ff0055"
            elif avg<=-20: m,c="FEAR","#ff5e00"
            else: m,c="NEUTRAL","#bd00ff"
            
            c1,c2,c3 = st.columns(3)
            c1.markdown(f"<div class='metric-card'><div class='metric-label'>Mood</div><div class='metric-value' style='color:{c}'>{m}</div></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card'><div class='metric-label'>Score</div><div class='metric-value'>{int(avg)}</div></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-card'><div class='metric-label'>News</div><div class='metric-value'>{len(df)}</div></div>", unsafe_allow_html=True)
            
            st.markdown("---")
            col1, col2 = st.columns([2,1])
            with col1:
                fig = px.bar(df, x="Score", y="text", orientation='h', color="Score", color_continuous_scale=['#ff0055','#bd00ff','#00FF99'], range_x=[-100,100])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#fff', yaxis={'visible':False})
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                # リンク付きで表示
                for index, row in df.iterrows():
                    st.markdown(f"**{row['date']}**<br>[{row['text']}]({row['link']})<br>*{row['Label']} ({row['Score']})*", unsafe_allow_html=True)
                    st.markdown("---")