import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# --- 1. SuperFunded Rich Design System ---
st.set_page_config(page_title="The Reality Check", layout="wide", page_icon="👁️")

st.markdown("""
<style>
    /* 1. 全体背景：深みのある宇宙的なダークテーマ */
    .stApp {
        background-color: #030014;
        background-image: 
            radial-gradient(circle at 50% 0%, #4a00e0 0%, transparent 50%),
            radial-gradient(circle at 80% 80%, #8e2de2 0%, transparent 40%),
            radial-gradient(circle at 20% 90%, #000000 0%, transparent 60%);
        background-attachment: fixed;
        color: #e0e0e0;
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    /* 2. 入力エリアのカスタマイズ */
    .stNumberInput > div > div > input { 
        background-color: rgba(255, 255, 255, 0.05); 
        color: #fff; 
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 8px;
    }
    .stSelectbox > div > div {
        background-color: rgba(255, 255, 255, 0.05);
        color: #fff;
        border-radius: 8px;
    }
    
    /* 3. リッチ・ガラスカード (Glassmorphism) */
    .glass-card {
        background: rgba(20, 20, 35, 0.4);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-top: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 20px;
        padding: 30px;
        margin-bottom: 24px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        text-align: center;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: all 0.3s ease;
    }
    
    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 40px rgba(138, 43, 226, 0.2); /* 紫の光 */
        border-color: rgba(255, 0, 150, 0.3);
    }
    
    /* KPIテキスト装飾 */
    .kpi-label { 
        font-size: 0.85rem; 
        color: #b0b0d0; 
        text-transform: uppercase; 
        letter-spacing: 2px; 
        font-weight: 600;
        margin-bottom: 10px;
    }
    .kpi-value { 
        font-size: 2.8rem; 
        font-weight: 800; 
        background: linear-gradient(to right, #fff, #d0d0ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 20px rgba(74, 0, 224, 0.5);
    }
    .kpi-sub { 
        font-size: 0.9rem; 
        color: #888; 
        margin-top: 5px; 
        font-style: italic;
    }
    
    /* 4. メッセージボックス */
    .message-box {
        background: rgba(0, 0, 0, 0.3);
        border-left: 4px solid;
        padding: 20px;
        border-radius: 0 12px 12px 0;
        margin-top: 20px;
        line-height: 1.6;
    }
    .msg-danger { border-color: #ff0055; background: linear-gradient(90deg, rgba(255,0,85,0.1), transparent); }
    .msg-success { border-color: #00ff99; background: linear-gradient(90deg, rgba(0,255,153,0.1), transparent); }
    
    /* 5. グラデーションテキスト */
    .gradient-text {
        background: linear-gradient(90deg, #ff00cc, #333399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
    }

    /* 6. SFカラー・CTAボタン (紫〜ピンクのグラデーション) */
    .sf-button {
        display: block;
        width: 100%;
        max-width: 600px;
        margin: 40px auto;
        padding: 20px 40px;
        background: linear-gradient(135deg, #6600cc 0%, #ff0066 100%);
        color: white !important;
        font-size: 1.5rem;
        font-weight: 800;
        text-align: center;
        text-decoration: none;
        border-radius: 50px;
        box-shadow: 0 10px 30px rgba(189, 0, 255, 0.4);
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 2px;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .sf-button:hover {
        transform: scale(1.03);
        box-shadow: 0 20px 50px rgba(255, 0, 102, 0.6);
        background: linear-gradient(135deg, #8000ff 0%, #ff0080 100%);
        text-decoration: none;
    }
    .sf-button:active {
        transform: scale(0.98);
    }

</style>
""", unsafe_allow_html=True)

# --- 2. Simulation Logic ---

def analyze_reality(deposit_count, deposit_avg, withdraw_count, withdraw_avg, prop_fee):
    # 現状分析
    total_deposit = deposit_count * deposit_avg
    total_withdraw = withdraw_count * withdraw_avg
    net_pnl = total_withdraw - total_deposit
    
    withdrawal_rate = (withdraw_count / deposit_count * 100) if deposit_count > 0 else 0
    
    # 3年後の予測損失
    future_loss_3y = abs(net_pnl * 3) if net_pnl < 0 else 0
    
    # プロップ比較（機会費用）
    prop_attempts = int(total_deposit / prop_fee) if prop_fee > 0 else 0
    
    return {
        "total_deposit": total_deposit,
        "total_withdraw": total_withdraw,
        "net_pnl": net_pnl,
        "withdrawal_rate": withdrawal_rate,
        "future_loss": future_loss_3y,
        "prop_attempts": prop_attempts
    }

# --- 3. Main UI Layout ---

# ヘッダー
st.markdown("<h1 style='text-align: center; font-size: 4rem; margin-bottom: 0;'>👁️ THE REALITY CHECK</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #b0b0d0; font-size: 1.2rem; letter-spacing: 2px; margin-bottom: 50px;'>ARE YOU INVESTING? OR JUST FUNDING THE BROKER?</p>", unsafe_allow_html=True)

# サイドバー
with st.sidebar:
    st.markdown("### 📊 YOUR TRACK RECORD")
    st.caption("Be honest. The numbers don't lie.")
    
    st.markdown("#### 📥 DEPOSITS")
    dep_count = st.number_input("Deposit Count (Last 12mo)", min_value=0, value=12, step=1)
    dep_avg = st.number_input("Avg. Deposit Amount ($)", min_value=0, value=500, step=100)
    
    st.markdown("#### 📤 WITHDRAWALS")
    wd_count = st.number_input("Withdrawal Count", min_value=0, value=1, step=1)
    wd_avg = st.number_input("Avg. Withdrawal Amount ($)", min_value=0, value=300, step=100)
    
    st.markdown("---")
    st.markdown("#### 🏆 PROP COMPARISON")
    prop_fee = st.selectbox("Compare with Prop Fee", [49, 99, 199, 299, 499], index=2, format_func=lambda x: f"${x} Challenge")

# 計算
res = analyze_reality(dep_count, dep_avg, wd_count, wd_avg, prop_fee)

# --- 結果表示セクション ---

if res['net_pnl'] >= 0:
    st.balloons()
    st.markdown(f"""
    <div class="message-box msg-success">
        <h3 style="color:#00ff99;">🎉 CONGRATULATIONS</h3>
        You are profitable (+${res['net_pnl']:,}). You are in the top 5%.<br>
        Imagine if you applied this skill to a <b>$100,000 Prop Account</b>. Your profits would be 10x-20x higher.
    </div>
    """, unsafe_allow_html=True)
else:
    # KPI Row
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">TOTAL DEPOSITED</div>
            <div class="kpi-value" style="color:#ff0055; text-shadow: 0 0 20px rgba(255, 0, 85, 0.4);">${res['total_deposit']:,.0f}</div>
            <div class="kpi-sub">{dep_count} Transactions to Broker</div>
        </div>""", unsafe_allow_html=True)
        
    with c2:
        color = "#ff0055" if res['withdrawal_rate'] < 50 else "#00ff99"
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">WITHDRAWAL RATE</div>
            <div class="kpi-value" style="color:{color};">{res['withdrawal_rate']:.1f}%</div>
            <div class="kpi-sub">Only {wd_count} success out of {dep_count}</div>
        </div>""", unsafe_allow_html=True)
        
    with c3:
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">NET LOSS (TUITION)</div>
            <div class="kpi-value" style="color:#aaa;">-${abs(res['net_pnl']):,.0f}</div>
            <div class="kpi-sub">Gone forever</div>
        </div>""", unsafe_allow_html=True)

    # 警告メッセージ
    st.markdown(f"""
    <div class="message-box msg-danger">
        <h3 style="color:#ff0055; margin:0;">🚨 WAKE UP CALL</h3>
        <p style="font-size:1.1rem; margin-top:10px;">
            You have donated <b>${res['total_deposit']:,.0f}</b> to your broker this year.<br>
            At this pace, you will lose another <b style="color:#ff0055">${res['future_loss']:,.0f}</b> in the next 3 years.<br>
            This is not trading. This is <b>gambling with bad odds</b>.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # --- SECTION 2: OPPORTUNITY COST ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.subheader("🛡️ THE SMART PIVOT: WHAT YOU COULD HAVE BOUGHT")
    
    col_chart, col_txt = st.columns([3, 2])
    
    with col_chart:
        # リッチなチャート
        fig = go.Figure()
        
        # 1. ユーザーの入金額 (Lost)
        fig.add_trace(go.Bar(
            y=['Total Loss'], x=[res['total_deposit']],
            orientation='h', name='Your Loss',
            text=f"${res['total_deposit']:,} LOST", textposition='auto',
            marker=dict(color='#ff0055', line=dict(color='rgba(255,255,255,0.5)', width=1))
        ))
        
        # 2. プロップの価値 (Opportunity)
        fig.add_trace(go.Bar(
            y=['Prop Power'], x=[res['total_deposit']],
            orientation='h', name='Prop Value',
            text=f"{res['prop_attempts']} CHALLENGES", textposition='auto',
            marker=dict(color='#8e2de2', line=dict(color='rgba(255,255,255,0.5)', width=1))
        ))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e0e0', family="Arial"),
            height=250,
            xaxis=dict(showgrid=False, visible=False),
            yaxis=dict(showgrid=False, tickfont=dict(size=14)),
            margin=dict(l=0, r=0, t=20, b=0),
            showlegend=False,
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_txt:
        st.markdown(f"""
        <div class="glass-card" style="text-align:left; border-left:4px solid #8e2de2;">
            <h4 style="margin:0; color:#bd00ff;">OPPORTUNITY COST</h4>
            <p style="font-size:1rem; margin-top:10px;">
                Instead of losing ${res['total_deposit']:,} with zero return, you could have attempted the 
                <b>SuperFunded Challenge {res['prop_attempts']} times</b>.
            </p>
            <p style="font-size:1rem;">
                Even if you failed {res['prop_attempts']-1} times and passed <b>ONLY ONCE</b>, 
                you would now have a funded account generating monthly income.
            </p>
        </div>
        """, unsafe_allow_html=True)

# --- CTA BUTTON (Custom HTML) ---
st.markdown("<br><br><br>", unsafe_allow_html=True)

st.markdown(f"""
<div style="text-align: center;">
    <h2 style="font-size: 2.5rem; background: linear-gradient(to right, #fff, #aaa); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        STOP THE BLEEDING. START TRADING.
    </h2>
    <p style="color: #ccc; font-size: 1.1rem; margin-bottom: 30px;">
        Switch to a risk-free environment where your downside is capped, and your upside is unlimited.
    </p>
    <a href="https://superfunded.com" target="_blank" class="sf-button">
        🚀 SWITCH TO PROFESSIONAL TRADING
    </a>
    <p style="color: #666; font-size: 0.8rem; margin-top: 20px;">
        Join thousands of traders who stopped gambling and started earning at SuperFunded.
    </p>
</div>
""", unsafe_allow_html=True)