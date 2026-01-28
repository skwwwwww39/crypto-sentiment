import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. Cyberpunk Design System ---
st.set_page_config(page_title="The Funding Snowball", layout="wide", page_icon="❄️")

st.markdown("""
<style>
    /* 全体設定 */
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(circle at 50% 0%, #0d1b2a 0%, #000000 80%);
        color: #e0e0e0;
    }
    
    /* 入力エリア */
    .stSlider > div > div > div > div { background-color: #00e5ff; }
    
    /* ガラスカード */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 229, 255, 0.1);
        border-radius: 16px;
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
        text-align: center;
        transition: transform 0.3s;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .glass-card:hover {
        transform: translateY(-5px);
        border-color: #00e5ff;
        box-shadow: 0 0 30px rgba(0, 229, 255, 0.2);
    }
    
    /* KPIテキスト */
    .kpi-label {
        font-size: 0.8rem;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 5px;
    }
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #fff, #ccc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .kpi-sub {
        font-size: 0.9rem;
        color: #00e5ff;
        font-weight: bold;
    }

    /* ロードマップのステップ */
    .step-card {
        background: rgba(0, 0, 0, 0.3);
        border-left: 4px solid #bd00ff;
        padding: 15px;
        margin-bottom: 10px;
        border-radius: 0 8px 8px 0;
    }
    
    /* ボタン */
    .stButton > button {
        background: linear-gradient(90deg, #00e5ff, #0044ff);
        border: none;
        color: white;
        font-weight: bold;
        padding: 15px 30px;
        border-radius: 30px;
        width: 100%;
        font-size: 1.1rem;
        transition: 0.3s;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stButton > button:hover {
        box-shadow: 0 0 40px rgba(0, 229, 255, 0.6);
        transform: scale(1.02);
    }
</style>
""", unsafe_allow_html=True)

# --- 2. Logic: Snowball Simulator ---

# SuperFundedのプラン定義 (仮想データ)
ACCOUNTS = {
    5000: {'fee': 49, 'size': 5000},
    10000: {'fee': 99, 'size': 10000},
    25000: {'fee': 199, 'size': 25000},
    50000: {'fee': 299, 'size': 50000},
    100000: {'fee': 499, 'size': 100000},
    200000: {'fee': 949, 'size': 200000},
}

def simulate_snowball(start_budget, monthly_return_pct, profit_split_pct, reinvest_rate_pct):
    """
    再投資シミュレーション:
    利益が出たら、その一部を使って「さらに大きな口座」を買い足していくロジック
    """
    # 予算内で買える最大の口座を探す
    start_account_size = 0
    start_fee = 0
    for size, data in ACCOUNTS.items():
        if data['fee'] <= start_budget:
            start_account_size = size
            start_fee = data['fee']
        else:
            break
            
    if start_account_size == 0:
        return None, "Budget too low for any account."

    # シミュレーション変数の初期化
    months = 24
    active_accounts = [start_account_size] # 保有している口座リスト
    cash_on_hand = start_budget - start_fee
    total_withdrawn = 0
    
    history = []
    
    for m in range(1, months + 1):
        # 1. 現在の全口座でトレードして利益を出す
        current_total_funding = sum(active_accounts)
        monthly_profit_gross = current_total_funding * (monthly_return_pct / 100)
        
        # 2. 報酬を受け取る
        payout = monthly_profit_gross * (profit_split_pct / 100)
        
        # 3. 再投資用と手取りに分ける
        reinvest_budget = payout * (reinvest_rate_pct / 100)
        pocket_money = payout - reinvest_budget
        
        cash_on_hand += reinvest_budget
        total_withdrawn += pocket_money
        
        # 4. 新しい口座を買えるかチェック (より大きな口座を優先)
        purchased = None
        # 降順（大きい口座順）にチェック
        for size in sorted(ACCOUNTS.keys(), reverse=True):
            fee = ACCOUNTS[size]['fee']
            # 手持ち資金で買える & 現在の総資金額 + 新規口座 <= 200万ドル(上限キャップ等の想定)
            if cash_on_hand >= fee:
                cash_on_hand -= fee
                active_accounts.append(size)
                purchased = size
                break # 1ヶ月に1個追加とする
        
        history.append({
            "Month": m,
            "Total Funding": current_total_funding,
            "Monthly Payout": payout,
            "Pocket Money": pocket_money,
            "Accounts Count": len(active_accounts),
            "New Account": f"+${purchased:,}" if purchased else "-"
        })
        
    return pd.DataFrame(history), None

# --- 3. Main UI ---

st.title("❄️ THE FUNDING SNOWBALL")
st.markdown("<h4 style='color:#888;'>TURN SMALL CAPITAL INTO AN EMPIRE // REINVESTMENT STRATEGY</h4>", unsafe_allow_html=True)

# サイドバー入力
with st.sidebar:
    st.header("🛠️ STRATEGY SETUP")
    
    start_budget = st.select_slider(
        "Your Starting Budget ($)",
        options=[50, 100, 200, 300, 500, 1000],
        value=100
    )
    
    st.markdown("---")
    
    monthly_return = st.slider("Avg Monthly Return (%)", 1.0, 10.0, 4.0, 0.5)
    profit_split = st.slider("Profit Split (%)", 70, 95, 80, 5)
    
    st.markdown("---")
    
    reinvest_rate = st.slider("Reinvestment Rate (%)", 0, 100, 50, 10, 
                              help="How much of your profit do you use to buy NEW accounts?")
    
    st.info(f"💡 With {reinvest_rate}% reinvestment, you keep {100-reinvest_rate}% of profits for yourself.")

# シミュレーション実行
df, error = simulate_snowball(start_budget, monthly_return, profit_split, reinvest_rate)

if error:
    st.error(error)
else:
    # 最終結果
    final_funding = df['Total Funding'].iloc[-1]
    final_monthly_income = df['Monthly Payout'].iloc[-1]
    total_pocket = df['Pocket Money'].sum()
    final_accounts = df['Accounts Count'].iloc[-1]

    # --- ROW 1: KEY METRICS ---
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">Month 1 Funding</div>
            <div class="kpi-value">${df['Total Funding'].iloc[0]:,.0f}</div>
            <div class="kpi-sub">Your Start</div>
        </div>""", unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="glass-card" style="border-color: #bd00ff; box-shadow: 0 0 15px rgba(189, 0, 255, 0.2);">
            <div class="kpi-label">Month 24 Funding</div>
            <div class="kpi-value" style="color:#bd00ff;">${final_funding:,.0f}</div>
            <div class="kpi-sub">Your Empire</div>
        </div>""", unsafe_allow_html=True)
        
    with c3:
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">Monthly Income (M24)</div>
            <div class="kpi-value" style="color:#00ff99;">${final_monthly_income:,.0f}</div>
            <div class="kpi-sub">Passive Cashflow</div>
        </div>""", unsafe_allow_html=True)
        
    with c4:
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">Active Accounts</div>
            <div class="kpi-value">{final_accounts}</div>
            <div class="kpi-sub">Diversified Portfolio</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- ROW 2: VISUALIZATION ---
    c_left, c_right = st.columns([2, 1])
    
    with c_left:
        st.subheader("📈 The Stairway to Wealth")
        st.caption("Total Funded Capital Growth (Reinvesting Profits)")
        
        # 階段状のグラフ (Step Chart)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['Month'], 
            y=df['Total Funding'],
            mode='lines',
            line=dict(shape='hv', width=4, color='#00e5ff'), # hv = Horizontal-Vertical (階段)
            fill='tozeroy',
            fillcolor='rgba(0, 229, 255, 0.1)',
            name='Total Funding'
        ))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)', 
            font_color='#ccc',
            xaxis=dict(showgrid=False, title='Months'),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', title='Total Funding ($)'),
            height=350,
            margin=dict(l=0,r=0,t=20,b=0)
        )
        st.plotly_chart(fig, use_container_width=True)

    with c_right:
        st.subheader("💰 Income Stream")
        st.caption("Monthly Payouts (After Reinvestment)")
        
        fig_bar = px.bar(
            df, 
            x="Month", 
            y="Pocket Money",
            color="Pocket Money",
            color_continuous_scale=['#333', '#00ff99']
        )
        fig_bar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)', 
            font_color='#ccc',
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
            height=350,
            coloraxis_showscale=False,
            margin=dict(l=0,r=0,t=20,b=0)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # --- ROW 3: ROADMAP ---
    st.subheader("🗺️ YOUR EXECUTION ROADMAP")
    
    with st.expander("See Step-by-Step Plan", expanded=True):
        # 重要なイベント（口座追加）があった月だけ抽出
        milestones = df[df['New Account'] != '-']
        
        if milestones.empty:
            st.warning("With this budget and return rate, it's hard to scale. Try increasing your budget or return rate.")
        else:
            for idx, row in milestones.iterrows():
                month = row['Month']
                new_acc = row['New Account']
                total = row['Total Funding']
                
                st.markdown(f"""
                <div class="step-card">
                    <span style="color:#888; font-weight:bold;">MONTH {month}</span> &nbsp; | &nbsp; 
                    <span style="color:#00ff99; font-weight:bold;">PROFIT UNLOCKED!</span> 
                    &nbsp; ➤ Used profits to buy <span style="color:#bd00ff; font-weight:bold; font-size:1.1rem;">{new_acc} Account</span> 
                    &nbsp; ➤ Total Funding: <b>${total:,.0f}</b>
                </div>
                """, unsafe_allow_html=True)

    # --- CTA ---
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; padding: 20px;">
        <h2 style="background: linear-gradient(to right, #00e5ff, #bd00ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            START WITH ${start_budget}, END WITH ${final_funding:,.0f}
        </h2>
        <p style="font-size: 1.1rem; color: #aaa;">
            You don't need a scaling plan. You build your own empire.<br>
            It all starts with that first, small account.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔥 BUY YOUR FIRST ACCOUNT ($" + str(start_budget) + ") 🔥"):
        st.balloons()