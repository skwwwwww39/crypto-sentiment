import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# --- 1. Cyberpunk Design System ---
st.set_page_config(page_title="The Reality Check", layout="wide", page_icon="🎰")

st.markdown("""
<style>
    /* 全体設定 */
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(circle at 50% 0%, #1a0b2e 0%, #000000 80%);
        color: #e0e0e0;
    }
    
    /* 入力エリア */
    .stNumberInput > div > div > input { background-color: #111; color: #fff; border: 1px solid #333; }
    .stSlider > div > div > div > div { background-color: #bd00ff; }
    
    /* カードデザイン */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        text-align: center;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    .kpi-label { font-size: 0.8rem; color: #aaa; text-transform: uppercase; letter-spacing: 1px; }
    .kpi-value { font-size: 2.2rem; font-weight: 800; color: #fff; }
    
    /* 警告ボックス */
    .wake-up-call {
        background: rgba(255, 0, 85, 0.1);
        border-left: 5px solid #ff0055;
        padding: 20px;
        margin-top: 20px;
        border-radius: 5px;
    }
    
    /* 教育ボックス */
    .education-box {
        background: rgba(0, 255, 153, 0.1);
        border-left: 5px solid #00ff99;
        padding: 20px;
        margin-top: 20px;
        border-radius: 5px;
    }

    /* リンクボタンのスタイル */
    .super-button {
        display: inline-block;
        text-decoration: none;
        color: white !important;
        font-weight: 800;
        font-size: 1.3rem;
        padding: 18px 50px;
        border-radius: 50px;
        /* SuperFunded風: 深い青紫から鮮やかなシアンへのリッチなグラデーション */
        background: linear-gradient(135deg, #4f46e5 0%, #0ea5e9 50%, #22d3ee 100%);
        box-shadow: 0 0 20px rgba(14, 165, 233, 0.4);
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 1px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .super-button:hover {
        transform: scale(1.03) translateY(-2px);
        box-shadow: 0 0 40px rgba(14, 165, 233, 0.7);
        background: linear-gradient(135deg, #4338ca 0%, #0284c7 50%, #06b6d4 100%);
    }
    .button-container {
        text-align: center;
        margin-top: 30px;
        margin-bottom: 50px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. Simulation Logic ---

def analyze_reality(deposit_count, deposit_avg, withdraw_count, withdraw_avg, prop_fee):
    """
    現状分析と未来予測
    """
    # 現状 (過去1年)
    total_deposit = deposit_count * deposit_avg
    total_withdraw = withdraw_count * withdraw_avg
    net_pnl = total_withdraw - total_deposit
    
    withdrawal_rate = (withdraw_count / deposit_count * 100) if deposit_count > 0 else 0
    return_rate = (total_withdraw / total_deposit * 100) if total_deposit > 0 else 0
    
    # 3年後の予測
    future_loss_3y = abs(net_pnl * 3) if net_pnl < 0 else 0
    
    # プロップ比較
    prop_attempts = int(total_deposit / prop_fee) if prop_fee > 0 else 0
    
    return {
        "total_deposit": total_deposit,
        "total_withdraw": total_withdraw,
        "net_pnl": net_pnl,
        "withdrawal_rate": withdrawal_rate,
        "return_rate": return_rate,
        "future_loss": future_loss_3y,
        "prop_attempts": prop_attempts
    }

# --- 3. Main UI ---

st.title("👁️ THE REALITY CHECK")
st.markdown("<h4 style='color:#aaa;'>ARE YOU INVESTING? OR JUST DEPOSITING?</h4>", unsafe_allow_html=True)

# サイドバー入力
with st.sidebar:
    st.header("📊 YOUR TRACK RECORD (Last 12 Months)")
    
    st.markdown("### 📥 DEPOSITS (入金)")
    dep_count = st.number_input("How many times did you deposit?", min_value=0, value=12, step=1, help="追加入金を含む")
    dep_avg = st.number_input("Average Deposit Amount ($)", min_value=0, value=500, step=100)
    
    st.markdown("### 📤 WITHDRAWALS (出金)")
    wd_count = st.number_input("How many times did you withdraw?", min_value=0, value=1, step=1, help="銀行口座に着金した回数")
    wd_avg = st.number_input("Average Withdrawal Amount ($)", min_value=0, value=300, step=100)
    
    st.markdown("---")
    st.header("🏆 PROP ALTERNATIVE")
    prop_fee = st.selectbox("Compare with Prop Fee ($)", [49, 99, 199, 299, 499], index=2)

# 計算実行
res = analyze_reality(dep_count, dep_avg, wd_count, wd_avg, prop_fee)

# 結果表示
if res['net_pnl'] >= 0:
    st.success(f"Congratulations! You are profitable (+${res['net_pnl']:,}). You should scale up with a Prop Firm to leverage your skill.")
else:
    # --- SECTION 1: THE PAINFUL TRUTH ---
    st.subheader("📉 The Cycle of Doom")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown(f"""
        <div class="glass-card" style="border-color:#ff0055;">
            <div class="kpi-label">TOTAL DEPOSITED</div>
            <div class="kpi-value" style="color:#ff0055;">${res['total_deposit']:,.0f}</div>
            <div class="kpi-sub">{dep_count} Transactions</div>
        </div>""", unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">WITHDRAWAL RATE</div>
            <div class="kpi-value">{res['withdrawal_rate']:.1f}%</div>
            <div class="kpi-sub">{wd_count} out of {dep_count} times</div>
        </div>""", unsafe_allow_html=True)
        
    with c3:
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">NET LOSS (TUITION)</div>
            <div class="kpi-value" style="color:#888;">-${abs(res['net_pnl']):,.0f}</div>
            <div class="kpi-sub">Money gone forever</div>
        </div>""", unsafe_allow_html=True)

    # 警告メッセージ
    st.markdown(f"""
    <div class="wake-up-call">
        <h3 style="margin:0; color:#ff0055;">🚨 REALITY CHECK</h3>
        <p style="font-size:1.1rem; margin-top:10px;">
            At this pace, you are paying the market <b>${abs(res['net_pnl']):,.0f} per year</b> just to trade.<br>
            If you continue this for 3 years, you will lose another <b>${res['future_loss']:,.0f}</b>.<br>
            This is not trading. This is <b>feeding the broker</b>.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # --- SECTION 2: THE PROP SOLUTION ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.subheader("🛡️ The Smart Pivot: Buy Skill, Not Losses")
    
    c_chart, c_text = st.columns([1, 1])
    
    with c_chart:
        # 比較チャート: 入金額 vs プロップ挑戦回数
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=['Personal FX', 'Prop Firm'],
            x=[1, res['prop_attempts']],
            orientation='h',
            text=[f"1 Account (Blown)", f"{res['prop_attempts']} Challenges"],
            textposition='auto',
            marker=dict(color=['#555', '#0ea5e9'], opacity=0.9)
        ))
        
        fig.update_layout(
            title="What your losses could have bought:",
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color='#e0e0e0', height=250,
            xaxis=dict(showgrid=False, title="Number of Opportunities"),
            yaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig, use_container_width=True)
        
    with c_text:
        st.markdown(f"""
        <div class="education-box">
            <h4 style="margin:0; color:#00ff99;">WHY PROP FIRMS ARE SAFER</h4>
            <ul style="margin-top:10px; font-size:1rem;">
                <li><b>Cost Cap:</b> You spent <b>${res['total_deposit']:,.0f}</b> on deposits. For that same money, you could have bought <b>{res['prop_attempts']} Prop Challenges</b>.</li>
                <li><b>Forced Discipline:</b> In FX, you deposit -> loose discipline -> blow up -> repeat. Prop firms force you to stop (Daily Limit) before you lose everything.</li>
                <li><b>Gambling vs. Training:</b> Personal FX feeds your greed (unlimited leverage). Prop firms train your risk management (strict rules).</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    # --- SECTION 3: BEHAVIORAL ANALYSIS ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🧠 Behavioral Shift")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔴 PERSONAL FX (CFD)")
        st.markdown("""
        - **Mindset:** "I need to double this account quickly."
        - **Action:** Over-leverage, Revenge Trading.
        - **Result:** **100% Loss of Capital.**
        - **Learning:** Minimal (Emotional damage).
        """)
        
    with col2:
        st.markdown("#### 🟢 PROP FIRM (SuperFunded)")
        st.markdown("""
        - **Mindset:** "I need to protect this account to get paid."
        - **Action:** Risk Control, Consistency.
        - **Result:** **Funded or Small Fee Loss.**
        - **Learning:** Massive (Professional habits).
        """)

    # --- CTA LINK BUTTON ---
    st.markdown("---")
    
    # 誘導メッセージ
    st.markdown(f"""
    <div style="text-align:center; padding-top:20px;">
        <h2>Stop Funding Your Broker. Start Funding Yourself.</h2>
        <p style="color:#aaa;">You have paid enough tuition to the market. Switch to a regulated environment.</p>
    </div>
    """, unsafe_allow_html=True)

    # リンク付きグラデーションボタン
    st.markdown("""
    <div class="button-container">
        <a href="https://superfunded.com" target="_blank" class="super-button">
            🔥 SWITCH TO PROFESSIONAL TRADING 🔥
        </a>
    </div>
    """, unsafe_allow_html=True)