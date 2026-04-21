import streamlit as st
import pandas as pd
import base64

st.set_page_config(page_title="AMC NTEP Dashboard", layout="wide", initial_sidebar_state="collapsed")

def img_to_b64(img_path):
    try:
        with open(img_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode('utf-8')
    except: return ""

# 🎯 બૅકગ્રાઉન્ડ ઈમેજ (તમારો Heritage ફોટો 'bg.jpg' નામે હોવો જોઈએ)
bg_img = img_to_b64("images/bg.jpg")
if bg_img: bg_css = f"background-image: url('data:image/jpeg;base64,{bg_img}');"
else: bg_css = "background: linear-gradient(135deg, #1f4037 0%, #99f2c8 100%);"

# ==========================================
# 🎯 --- PREMIUM LOGIN PAGE (Mobile Friendly) ---
# ==========================================
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    login_style = f"""
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        #MainMenu {{visibility: hidden;}} header {{visibility: hidden;}} footer {{visibility: hidden;}}
        .stApp {{
            {bg_css}
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        .login-container {{
            display: flex; justify-content: center; align-items: center; height: 85vh;
        }}
        .glass-panel {{
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 20px;
            padding: 40px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4);
            text-align: center;
            color: white;
        }}
        .glass-panel h2 {{ font-weight: 900; font-size: 28px; margin-bottom: 5px; color: #fff; text-shadow: 2px 2px 4px rgba(0,0,0,0.6); }}
        .glass-panel p {{ color: #e0e0e0; font-size: 14px; font-weight: bold; margin-bottom: 30px; letter-spacing: 2px; text-shadow: 1px 1px 3px rgba(0,0,0,0.6); }}
        .stTextInput>div>div>input {{ background-color: rgba(255, 255, 255, 0.85) !important; border-radius: 10px !important; padding: 12px !important; color: #111 !important; border: 1px solid rgba(255,255,255,0.5) !important; font-size: 16px !important; }}
        .stButton>button {{ width: 100%; background: linear-gradient(90deg, #E67E22 0%, #D35400 100%); color: white; border-radius: 10px; padding: 12px; font-size: 16px; font-weight: bold; border: none; margin-top: 15px; text-transform: uppercase; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }}
        .stButton>button:hover {{ background: linear-gradient(90deg, #D35400 0%, #E67E22 100%); transform: translateY(-2px); }}
        @media (max-width: 768px) {{ .glass-panel {{ width: 90% !important; padding: 30px !important; margin-top: 5vh; }} }}
    </style>
    """
    st.markdown(login_style, unsafe_allow_html=True)
    st.markdown("<div class='login-container'>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,3,1])
    with col2:
        st.markdown("<div class='glass-panel'><h2>AMC | NTEP</h2><p>SECURE PORTAL</p>", unsafe_allow_html=True)
        pwd = st.text_input("Password", type="password", placeholder="Enter Password...", label_visibility="collapsed")
        if st.button("Access Dashboard"):
            if pwd == "AMC@2026": st.session_state.auth = True; st.rerun()
            else: st.error("⚠️ Invalid Password.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# ==========================================
# 🎯 --- MAIN DASHBOARD (BLURRY HERITAGE BG) ---
# ==========================================

dash_style = f"""
<style>
    #MainMenu {{visibility: hidden;}} header {{visibility: hidden;}} footer {{visibility: hidden;}}
    .stApp {{
        {bg_css}
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    /* 🎯 ડેશબોર્ડની પાછળ કાચ જેવો સફેદ પડદો જેથી અક્ષર વંચાય અને બેકગ્રાઉન્ડ પણ દેખાય */
    .block-container {{
        background: rgba(255, 255, 255, 0.88);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 30px;
        margin-top: 3vh;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        max-width: 1050px;
    }}
    .amc-footer {{ text-align: center; font-size: 11px; color: #444; margin-top: 15px; padding-top: 10px; font-weight: bold; border-top: 1px solid rgba(0,0,0,0.1);}}
</style>
"""
st.markdown(dash_style, unsafe_allow_html=True)

def draw_card(title, value, color, icon):
    return f"""
    <div style="background-color: {color}; border-radius: 12px; padding: 18px 5px; margin-bottom: 15px; color: white; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.15); transition: transform 0.2s;">
        <div style="font-size: 26px; margin-bottom: 8px;">{icon}</div>
        <div style="font-size: 12px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;">{title}</div>
        <div style="font-size: 30px; font-weight: 900; margin-top: 5px; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);">{value}</div>
    </div>
    """

def get_options_with_counts(df, column_name):
    counts = df[column_name].value_counts()
    return [f"{val} ({count})" for val, count in counts.items() if str(val) not in ["nan", "", "None", "N/A"]]

def clean_selection(selected_list):
    return [item.rsplit(" (", 1)[0] for item in selected_list]

try:
    df_master = pd.read_csv("Master_Line_List.csv")
    for col in ['Diagnosis Date', 'Initiation Date', 'Outcome Date']:
        if col in df_master.columns: df_master[col] = pd.to_datetime(df_master[col], errors='coerce')
    df_comp = pd.read_csv("Comparison_Matrix.csv")
    df_curr_tb = pd.read_csv("Current_TB_Patients.csv")
    for col in ['Diagnosis Date', 'Initiation Date', 'Outcome Date']:
        if col in df_curr_tb.columns: df_curr_tb[col] = pd.to_datetime(df_curr_tb[col], errors='coerce')
except:
    st.error("⚠️ ડેટા અપડેટ કરો...")
    st.stop()

b64_amc, b64_ntep = img_to_b64("images/amc.png"), img_to_b64("images/ntep.jpg")

st.markdown(f"<div style='display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #1f618d; padding-bottom: 10px;'><img src='data:image/png;base64,{b64_amc}' height='70'><h3 style='margin:0; font-weight:900; color: #1f618d; letter-spacing: 1px;'>AMC | NTEP</h3><img src='data:image/jpeg;base64,{b64_ntep}' height='70'></div>", unsafe_allow_html=True)
st.markdown("<div style='background: linear-gradient(90deg, #1f618d 0%, #2980b9 100%); color:white; text-align:center; padding:12px; border-radius:8px; margin:15px 0; font-weight: bold; letter-spacing: 1px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>TB Monitoring Dashboard - Ahmedabad</div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📊 Master Dashboard", "🔄 Daily Comparison", "🏥 Current TB Patients"])

with tab1:
    with st.expander("🔽 Filters & Sorting"):
        inds = ["SLPA", "UDST", "Not Put On", "Outcome", "Consent", "ADT", "RBS", "ART", "CPT", "HIV"]
        f_rep = st.multiselect("Report Type", inds)
        
        c1, c2 = st.columns(2)
        with c1:
            z_opts = get_options_with_counts(df_master, 'ZONE')
            s_z_raw = st.multiselect("Zone", z_opts)
            s_z = clean_selection(s_z_raw)
            
            df_tu = df_master[df_master['ZONE'].isin(s_z)] if s_z else df_master
            tu_opts = get_options_with_counts(df_tu, 'TB Unit')
            s_tu_raw = st.multiselect("TB Unit", tu_opts)
            s_tu = clean_selection(s_tu_raw)
        with c2:
            df_ft = df_tu[df_tu['TB Unit'].isin(s_tu)] if s_tu else df_tu
            ft_opts = get_options_with_counts(df_ft, 'Facility Type')
            s_ft_raw = st.multiselect("Facility Type", ft_opts)
            s_ft = clean_selection(s_ft_raw)
            
            df_phi = df_ft[df_ft['Facility Type'].isin(s_ft)] if s_ft else df_ft
            phi_opts = get_options_with_counts(df_phi, 'PHI')
            s_phi_raw = st.multiselect("PHI", phi_opts)
            s_phi = clean_selection(s_phi_raw)

    df_disp = df_master.copy()
    if s_z: df_disp = df_disp[df_disp['ZONE'].isin(s_z)]
    if s_tu: df_disp = df_disp[df_disp['TB Unit'].isin(s_tu)]
    if s_ft: df_disp = df_disp[df_disp['Facility Type'].isin(s_ft)]
    if s_phi: df_disp = df_disp[df_disp['PHI'].isin(s_phi)]
    if f_rep: df_disp = df_disp[df_disp['Pending Status'].str.contains("|".join(f_rep), na=False)]

    f_counts = {k: len(df_disp[df_disp['Pending Status'].str.contains(k, na=False)]) for k in inds}
    total_pendency = sum(f_counts.values()) 
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(draw_card("Total Pendency", total_pendency, "#1f618d", "📄"), unsafe_allow_html=True)
    with c2: st.markdown(draw_card("Outcome Pending", f_counts["Outcome"], "#F39C12", "🏥"), unsafe_allow_html=True)
    with c3: st.markdown(draw_card("UDST Pending", f_counts["UDST"], "#C0392B", "🧪"), unsafe_allow_html=True)
    with c4: st.markdown(draw_card("Not Put On", f_counts["Not Put On"], "#27AE60", "⏳"), unsafe_allow_html=True)

    conf = {"Diagnosis Date": st.column_config.DateColumn(format="DD-MM-YYYY"), "Initiation Date": st.column_config.DateColumn(format="DD-MM-YYYY"), "Outcome Date": st.column_config.DateColumn(format="DD-MM-YYYY")}
    st.dataframe(df_disp, use_container_width=True, hide_index=True, column_config=conf)

with tab2:
    st.markdown("#### 🔄 Comparison Matrix")
    with st.expander("🔽 Filters (Geography & Report Type)"):
        c1, c2, c3 = st.columns(3)
        with c1:
            z2_opts = get_options_with_counts(df_comp, 'ZONE')
            s2_z_raw = st.multiselect("Filter Zone", z2_opts, key='z2')
            s2_z = clean_selection(s2_z_raw)
        with c2:
            df2_tu = df_comp[df_comp['ZONE'].isin(s2_z)] if s2_z else df_comp
            tu2_opts = get_options_with_counts(df2_tu, 'TB Unit')
            s2_tu_raw = st.multiselect("Filter TB Unit", tu2_opts, key='tu2')
            s2_tu = clean_selection(s2_tu_raw)
        with c3:
            status_options = ["🔴 NEW", "🟢 RESOLVED", "🟡 PERSISTENT"]
            s2_status = st.multiselect("Filter by Status", status_options, key='status2')
            
    df_c_disp = df_comp.copy()
    if s2_z: df_c_disp = df_c_disp[df_c_disp['ZONE'].isin(s2_z)]
    if s2_tu: df_c_disp = df_c_disp[df_c_disp['TB Unit'].isin(s2_tu)]

    if s2_status:
        base_cols_comp = ['ZONE', 'PHI', 'TB Unit', 'Episode ID', 'Patient Name']
        ind_cols = [c for c in df_c_disp.columns if c not in base_cols_comp]
        mask = pd.Series(False, index=df_c_disp.index)
        for col in ind_cols:
            for stat in s2_status:
                mask = mask | (df_c_disp[col] == stat)
        df_c_disp = df_c_disp[mask]
    
    st.dataframe(df_c_disp, use_container_width=True, hide_index=True)

with tab3:
    st.markdown("#### 🏥 Current TB Patients of AMC")
    df_curr_disp = df_curr_tb.copy()
    st.markdown(draw_card("Total Current Patients", len(df_curr_disp), "#27AE60", "👥"), unsafe_allow_html=True)
    st.dataframe(df_curr_disp, use_container_width=True, hide_index=True, column_config=conf)

st.markdown("<div class='amc-footer'>Developed for District TB Center AMC | Empowering NTEP Monitoring</div>", unsafe_allow_html=True)
