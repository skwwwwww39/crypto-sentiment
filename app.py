import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber
import re

# --- 1. Design System ---
st.set_page_config(page_title="Titan Analytics: SuperFunded", layout="wide", page_icon="🛡️")

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
        text-align: center;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .kpi-label { font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 1px; }
    .kpi-value { font-size: 2.0rem; font-weight: 800; color: #fff; }
    .stFileUploader > div > div {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px dashed #bd00ff;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. Advanced OCR Cleaning Engine ---

def clean_superfunded_number(val_str):
    """
    SuperFundedのPDF特有のOCRエラー（誤字）を修正して数値化する
    例: "5-1,143,66" -> -1143.66
    例: "840:81" -> 840.81
    """
    if not isinstance(val_str, str):
        return 0.0
    
    # 1. 改行が含まれている場合、最後の行（Net Profitの位置）を取得
    if '\n' in val_str:
        val_str = val_str.split('\n')[-1]

    s = val_str.strip()
    
    # 2. 通貨記号とカンマを除去
    s = s.replace('$', '').replace(',', '').replace(' ', '')
    
    # 3. OCRエラー修正: 先頭の "5-" や "4-" はマイナス記号の誤検知
    s = re.sub(r'^[45]-', '-', s)
    
    # 4. OCRエラー修正: 数字の間の ":" は小数点の誤検知
    s = s.replace(':', '.')
    
    # 5. その他、末尾の変な文字を除去
    s = re.sub(r'[^\d\.\-]', '', s)

    try:
        return float(s)
    except:
        return 0.0

def parse_pdf_robust(file):
    """ロバスト（頑丈）なPDFパーサー"""
    data = []
    
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                
                for table in tables:
                    for row in table:
                        # 空セルを除去してリスト化
                        cleaned_row = [str(cell).strip() for cell in row if cell]
                        
                        # データ行の判定: 
                        # "Buy" か "Sell" という単語が、リストの前半(インデックス1~3あたり)に含まれているか
                        trade_type = None
                        type_idx = -1
                        
                        for i, cell in enumerate(cleaned_row[:5]): # 最初の5列以内を探す
                            if cell.lower() in ['buy', 'sell']:
                                trade_type = cell
                                type_idx = i
                                break
                        
                        if trade_type and len(cleaned_row) >= 5:
                            try:
                                # 構造の推定:
                                # Typeが見つかった列の:
                                # 1つ前 = 日付 (Open Time)
                                # 1つ後 = 通貨ペア (Symbol)
                                # 一番最後 = 損益 (Net Profit)
                                
                                date_val = cleaned_row[type_idx - 1]
                                symbol_val = cleaned_row[type_idx + 1]
                                profit_val = cleaned_row[-1] # 常に最後の列がNet Profit
                                
                                # 日付のクリーニング (改行がある場合は最初の行)
                                if '\n' in date_val:
                                    date_val = date_val.split('\n')[0]

                                item = {
                                    "Open Time": date_val,
                                    "Type": trade_type,
                                    "Symbol": symbol_val,
                                    "Net Profit": clean_superfunded_number(profit_val)
                                }
                                data.append(item)
                            except:
                                continue

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        
        # 日付変換: "18/02/25 17:34:28" -> datetime
        df['Open Time'] = pd.to_datetime(df['Open Time'], dayfirst=True, errors='coerce')
        
        # 日付変換に失敗した行（ヘッダーの残りなど）を削除
        df = df.dropna(subset=['Open Time'])
        
        return df

    except Exception as e:
        st.error(f"System Error: {e}")
        return pd.DataFrame()

def load_demo_data():
    dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq='D')
    df = pd.DataFrame({
        "Open Time": dates,
        "Symbol": ["USDJPY", "EURUSD", "GBPUSD", "XAUUSD", "BTCUSD"] * 6,
        "Type": ["Buy", "Sell"] * 15,
        "Net Profit": [150, -80, 240, -120, 500, -80, 50, -200, 400, -50] * 3
    })
    return df

# --- 3. Analytics Logic ---

def analyze_data(df):
    if df.empty: return None
    
    total_trades = len(df)
    total_pnl = df['Net Profit'].sum()
    wins = df[df['Net Profit'] > 0]
    losses = df[df['Net Profit'] <= 0]
    
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    
    gross_profit = wins['Net Profit'].sum()
    gross_loss = abs(losses['Net Profit'].sum())
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
    
    df_sorted = df.sort_values('Open Time')
    df_sorted['Cumulative PnL'] = df_sorted['Net Profit'].cumsum()
    
    df['Day'] = df['Open Time'].dt.day_name()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_pnl = df.groupby('Day')['Net Profit'].sum().reindex(day_order).fillna(0).reset_index()

    return {
        "df": df_sorted,
        "total_trades": total_trades,
        "total_pnl": total_pnl,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "day_pnl": day_pnl
    }

# --- 4. Dashboard UI ---

st.title("🛡️ TITAN ANALYTICS")
st.markdown("SUPERFUNDED JOURNAL // INTELLIGENT PARSER")

with st.sidebar:
    st.header("📂 DATA INPUT")
    uploaded_file = st.file_uploader("Upload PDF Report", type="pdf")
    use_demo = st.checkbox("Demo Mode", value=False)

df = pd.DataFrame()

if uploaded_file:
    with st.spinner("Decoding PDF & Fixing OCR Errors..."):
        df = parse_pdf_robust(uploaded_file)
        if df.empty:
            st.error("Error: Could not extract trades. Please check the PDF format.")
elif use_demo:
    df = load_demo_data()

if not df.empty:
    m = analyze_data(df)
    
    # KPI Row
    c1, c2, c3, c4 = st.columns(4)
    p_col = "#00ff99" if m['total_pnl'] >= 0 else "#ff0055"
    
    c1.markdown(f"<div class='glass-card'><div class='kpi-label'>NET PROFIT</div><div class='kpi-value' style='color:{p_col}'>${m['total_pnl']:,.2f}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='glass-card'><div class='kpi-label'>WIN RATE</div><div class='kpi-value'>{m['win_rate']:.1f}%</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='glass-card'><div class='kpi-label'>PROFIT FACTOR</div><div class='kpi-value'>{m['profit_factor']:.2f}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='glass-card'><div class='kpi-label'>TRADES</div><div class='kpi-value'>{m['total_trades']}</div></div>", unsafe_allow_html=True)

    # Charts
    st.subheader("📈 Equity Curve")
    fig_eq = px.area(m['df'], x='Open Time', y='Cumulative PnL')
    fig_eq.update_traces(line_color='#00e5ff', fillcolor='rgba(0, 229, 255, 0.1)')
    fig_eq.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#888', height=350, margin=dict(t=0,b=0,l=0,r=0))
    st.plotly_chart(fig_eq, use_container_width=True)

    c_left, c_right = st.columns(2)
    with c_left:
        st.subheader("📅 PnL by Day")
        fig_day = px.bar(m['day_pnl'], x='Day', y='Net Profit', color='Net Profit', color_continuous_scale=['#ff0055', '#333', '#00ff99'])
        fig_day.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#888', height=300, margin=dict(t=0,b=0,l=0,r=0))
        st.plotly_chart(fig_day, use_container_width=True)
    
    with c_right:
        st.subheader("📊 Symbol Performance")
        sym_pnl = df.groupby('Symbol')['Net Profit'].sum().sort_values()
        fig_sym = px.bar(x=sym_pnl.values, y=sym_pnl.index, orientation='h', color=sym_pnl.values, color_continuous_scale=['#ff0055', '#333', '#00ff99'])
        fig_sym.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#888', height=300, margin=dict(t=0,b=0,l=0,r=0))
        st.plotly_chart(fig_sym, use_container_width=True)

    with st.expander("Show Parsed Raw Data"):
        st.dataframe(m['df'][['Open Time', 'Symbol', 'Type', 'Net Profit']].sort_values('Open Time', ascending=False), use_container_width=True)

else:
    st.markdown("<div style='text-align:center; padding:50px; opacity:0.6'><h1>READY TO ANALYZE</h1><p>Upload your PDF from the sidebar.</p></div>", unsafe_allow_html=True)