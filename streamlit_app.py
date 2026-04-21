import streamlit as st
import pandas as pd
import base64

st.set_page_config(page_title="AMC NTEP Dashboard", layout="wide", initial_sidebar_state="collapsed")

def img_to_b64(img_path):
    try:
        with open(img_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode('utf-8')
    except: return ""

# ==========================================
# 🎯 --- SIMPLE & CLEAN LOGIN PAGE ---
# ==========================================
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("<h2 style='text-align: center; color: #1f618d; margin-top: 15vh;'>AMC | NTEP Secure Login</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        pwd = st.text_input("Password", type="password")
        if st.button("Login", use_container_width=True):
            if pwd == "AMC@2026": 
                st.session_state.auth = True
                st.rerun()
            else: st.error("⚠️ Invalid Password")
    st.stop()


# ==========================================
# 🎯 --- ORIGINAL MAIN DASHBOARD ---
# ==========================================
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    .block-container { padding-top: 1rem; padding-bottom: 1rem; max-width: 1000px; }
    .amc-footer { text-align: center; font-size: 11px; color: #555; margin-top: 10px; padding-top: 10px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

def draw_card(title, value, color, icon):
    return f"""
    <div style="background-color: {color}; border-radius: 8px; padding: 15px 5px; margin-bottom: 10px; color: white; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="font-size: 24px; margin-bottom: 5px;">{icon}</div>
        <div style="font-size: 13px; font-weight: bold; text-transform: uppercase; line-height: 1.1;">{title}</div>
        <div style="font-size: 26px; font-weight: 900; margin-top: 8px;">{value}</div>
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
b64_h1, b64_h2 = img_to_b64("images/h1.jpg"), img_to_b64("images/h2.jpg")

st.markdown(f"<div style='display: flex; justify-content: space-between; align-items: center;'><img src='data:image/png;base64,{b64_amc}' height='75'><h3 style='margin:0; font-weight:900;'>AMC | NTEP</h3><img src='data:image/jpeg;base64,{b64_ntep}' height='75'></div>", unsafe_allow_html=True)
st.markdown("<div style='background-color:#1f618d; color:white; text-align:center; padding:12px; border-radius:5px; margin:15px 0;'>TB Monitoring Dashboard - Ahmedabad</div>", unsafe_allow_html=True)

# તમારો ફેવરિટ હેરિટેજ ફોટો વ્યૂ 
if b64_h1 and b64_h2:
    st.markdown(f"<div style='display:flex; gap:8px; margin-bottom: 20px;'><img src='data:image/jpeg;base64,{b64_h1}' style='width:50%; height:130px; object-fit:cover; border-radius:5px;'><img src='data:image/jpeg;base64,{b64_h2}' style='width:50%; height:130px; object-fit:cover; border-radius:5px;'></div>", unsafe_allow_html=True)

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

        d1, d2, d3 = st.columns(3)
        with d1: dr_diag = st.date_input("Diagnosis Date", value=[], key="dr_diag")
        with d2: dr_init = st.date_input("Initiation Date", value=[], key="dr_init")
        with d3: dr_out = st.date_input("Outcome Date", value=[], key="dr_out")
        
        if st.button("Reset Filters", key="r1"): st.rerun()

    df_disp = df_master.copy()
    if s_z: df_disp = df_disp[df_disp['ZONE'].isin(s_z)]
    if s_tu: df_disp = df_disp[df_disp['TB Unit'].isin(s_tu)]
    if s_ft: df_disp = df_disp[df_disp['Facility Type'].isin(s_ft)]
    if s_phi: df_disp = df_disp[df_disp['PHI'].isin(s_phi)]
    if f_rep: df_disp = df_disp[df_disp['Pending Status'].str.contains("|".join(f_rep), na=False)]

    if len(dr_diag) == 2: df_disp = df_disp[(df_disp['Diagnosis Date'].dt.date >= dr_diag[0]) & (df_disp['Diagnosis Date'].dt.date <= dr_diag[1])]
    if len(dr_init) == 2: df_disp = df_disp[(df_disp['Initiation Date'].dt.date >= dr_init[0]) & (df_disp['Initiation Date'].dt.date <= dr_init[1])]
    if len(dr_out) == 2: df_disp = df_disp[(df_disp['Outcome Date'].dt.date >= dr_out[0]) & (df_disp['Outcome Date'].dt.date <= dr_out[1])]

    f_counts = {k: len(df_disp[df_disp['Pending Status'].str.contains(k, na=False)]) for k in inds}
    total_pendency = sum(f_counts.values()) 
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(draw_card("Total Pendency", total_pendency, "#1f618d", "📄"), unsafe_allow_html=True)
    with c2: st.markdown(draw_card("Outcome Pending", f_counts["Outcome"], "#F39C12", "🏥"), unsafe_allow_html=True)
    with c3: st.markdown(draw_card("UDST Pending", f_counts["UDST"], "#C0392B", "🧪"), unsafe_allow_html=True)
    with c4: st.markdown(draw_card("Not Put On", f_counts["Not Put On"], "#27AE60", "⏳"), unsafe_allow_html=True)

    with st.expander("View All Other Pending Indicators"):
        r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
        with r2_c1: st.markdown(draw_card("SLPA", f_counts["SLPA"], "#D35400", "🔬"), unsafe_allow_html=True)
        with r2_c2: st.markdown(draw_card("Consent", f_counts["Consent"], "#8E44AD", "📝"), unsafe_allow_html=True)
        with r2_c3: st.markdown(draw_card("ADT", f_counts["ADT"], "#16A085", "🩸"), unsafe_allow_html=True)
        with r2_c4: st.markdown(draw_card("RBS", f_counts["RBS"], "#E67E22", "💉"), unsafe_allow_html=True)
        r3_c1, r3_c2, r3_c3, r3_c4 = st.columns(4)
        with r3_c1: st.markdown(draw_card("ART", f_counts["ART"], "#2980B9", "💊"), unsafe_allow_html=True)
        with r3_c2: st.markdown(draw_card("CPT", f_counts["CPT"], "#D35400", "🛡️"), unsafe_allow_html=True)
        with r3_c3: st.markdown(draw_card("HIV", f_counts["HIV"], "#C0392B", "🩺"), unsafe_allow_html=True)

    conf = {"Diagnosis Date": st.column_config.DateColumn(format="DD-MM-YYYY"), "Initiation Date": st.column_config.DateColumn(format="DD-MM-YYYY"), "Outcome Date": st.column_config.DateColumn(format="DD-MM-YYYY")}
    st.dataframe(df_disp, use_container_width=True, hide_index=True, column_config=conf)

with tab2:
    st.markdown("#### 🔄 Comparison Matrix")
    with st.expander("🔽 Dependent Filters"):
        c1, c2 = st.columns(2)
        with c1:
            z2_opts = get_options_with_counts(df_comp, 'ZONE')
            s2_z_raw = st.multiselect("Filter Zone", z2_opts, key='z2')
            s2_z = clean_selection(s2_z_raw)
            
            df2_tu = df_comp[df_comp['ZONE'].isin(s2_z)] if s2_z else df_comp
            tu2_opts = get_options_with_counts(df2_tu, 'TB Unit')
            s2_tu_raw = st.multiselect("Filter TB Unit", tu2_opts, key='tu2')
            s2_tu = clean_selection(s2_tu_raw)
        with c2:
            df2_phi = df2_tu[df2_tu['TB Unit'].isin(s2_tu)] if s2_tu else df2_tu
            phi2_opts = get_options_with_counts(df2_phi, 'PHI')
            s2_phi_raw = st.multiselect("Filter PHI", phi2_opts, key='phi2')
            s2_phi = clean_selection(s2_phi_raw)
            
    df_c_disp = df_comp.copy()
    if s2_z: df_c_disp = df_c_disp[df_c_disp['ZONE'].isin(s2_z)]
    if s2_tu: df_c_disp = df_c_disp[df_c_disp['TB Unit'].isin(s2_tu)]
    if s2_phi: df_c_disp = df_c_disp[df_c_disp['PHI'].isin(s2_phi)]

    t_new = (df_c_disp == "🔴 NEW").sum().sum()
    t_res = (df_c_disp == "🟢 RESOLVED").sum().sum()
    t_per = (df_c_disp == "🟡 PERSISTENT").sum().sum()
    t_total = t_new + t_per
    
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.markdown(draw_card("Total Pendency", t_total, "#1f618d", "📊"), unsafe_allow_html=True)
    with k2: st.markdown(draw_card("New Pendency", t_new, "#C0392B", "🔴"), unsafe_allow_html=True)
    with k3: st.markdown(draw_card("Resolved", t_res, "#27AE60", "🟢"), unsafe_allow_html=True)
    with k4: st.markdown(draw_card("Persistent", t_per, "#F39C12", "🟡"), unsafe_allow_html=True)
    
    st.dataframe(df_c_disp, use_container_width=True, hide_index=True)

with tab3:
    st.markdown("#### 🏥 Current TB Patients of AMC")
    st.caption("આ લિસ્ટમાં માત્ર એવા જ દર્દીઓ છે જેનું Notification Register માં 'Treatment Outcome' ખાલી છે.")
    
    with st.expander("🔽 Filters (Geography & Treatment Info)"):
        c1, c2 = st.columns(2)
        with c1:
            z3_opts = get_options_with_counts(df_curr_tb, 'ZONE')
            s3_z_raw = st.multiselect("Zone", z3_opts, key='z3')
            s3_z = clean_selection(s3_z_raw)
            
            df3_tu = df_curr_tb[df_curr_tb['ZONE'].isin(s3_z)] if s3_z else df_curr_tb
            tu3_opts = get_options_with_counts(df3_tu, 'TB Unit')
            s3_tu_raw = st.multiselect("TB Unit", tu3_opts, key='tu3')
            s3_tu = clean_selection(s3_tu_raw)
            
            df3_ft = df3_tu[df3_tu['TB Unit'].isin(s3_tu)] if s3_tu else df3_tu
            ft3_opts = get_options_with_counts(df3_ft, 'Facility Type')
            s3_ft_raw = st.multiselect("Facility Type", ft3_opts, key='ft3')
            s3_ft = clean_selection(s3_ft_raw)

        with c2:
            df3_phi = df3_ft[df3_ft['Facility Type'].isin(s3_ft)] if s3_ft else df3_ft
            phi3_opts = get_options_with_counts(df3_phi, 'PHI')
            s3_phi_raw = st.multiselect("PHI", phi3_opts, key='phi3')
            s3_phi = clean_selection(s3_phi_raw)
            
            case_opts = get_options_with_counts(df_curr_tb, 'Type of Case')
            s3_case_raw = st.multiselect("Type of Case", case_opts)
            s3_case = clean_selection(s3_case_raw)
            
            reg_opts = get_options_with_counts(df_curr_tb, 'TB_regimen')
            s3_reg_raw = st.multiselect("Type of TB Regimen", reg_opts)
            s3_reg = clean_selection(s3_reg_raw)
            
        st.markdown("---")
        d1, d2, d3 = st.columns(3)
        with d1: dr3_diag = st.date_input("Diagnosis Date Filter", value=[], key="dr3_diag")
        with d2: dr3_init = st.date_input("Initiation Date Filter", value=[], key="dr3_init")
        with d3: dr3_out = st.date_input("Outcome Date Filter", value=[], key="dr3_out")
        
        if st.button("Reset Tab 3 Filters", key="r3"): st.rerun()

    df_curr_disp = df_curr_tb.copy()
    
    if s3_z: df_curr_disp = df_curr_disp[df_curr_disp['ZONE'].isin(s3_z)]
    if s3_tu: df_curr_disp = df_curr_disp[df_curr_disp['TB Unit'].isin(s3_tu)]
    if s3_ft: df_curr_disp = df_curr_disp[df_curr_disp['Facility Type'].isin(s3_ft)]
    if s3_phi: df_curr_disp = df_curr_disp[df_curr_disp['PHI'].isin(s3_phi)]
    if s3_case: df_curr_disp = df_curr_disp[df_curr_disp['Type of Case'].isin(s3_case)]
    if s3_reg: df_curr_disp = df_curr_disp[df_curr_disp['TB_regimen'].isin(s3_reg)]
    
    if len(dr3_diag) == 2: df_curr_disp = df_curr_disp[(df_curr_disp['Diagnosis Date'].dt.date >= dr3_diag[0]) & (df_curr_disp['Diagnosis Date'].dt.date <= dr3_diag[1])]
    if len(dr3_init) == 2: df_curr_disp = df_curr_disp[(df_curr_disp['Initiation Date'].dt.date >= dr3_init[0]) & (df_curr_disp['Initiation Date'].dt.date <= dr3_init[1])]
    if len(dr3_out) == 2: df_curr_disp = df_curr_disp[(df_curr_disp['Outcome Date'].dt.date >= dr3_out[0]) & (df_curr_disp['Outcome Date'].dt.date <= dr3_out[1])]

    st.markdown(draw_card("Total Current Patients", len(df_curr_disp), "#27AE60", "👥"), unsafe_allow_html=True)
    
    cols_to_show = ['ZONE', 'TB Unit', 'PHI', 'Episode ID', 'Diagnosis Date', 'Initiation Date', 'Outcome Date', 'TB_regimen', 'Type of Case']
    df_curr_final = df_curr_disp[cols_to_show]
    
    st.dataframe(df_curr_final, use_container_width=True, hide_index=True, column_config=conf)
    st.download_button("📥 Download Current Patients List", df_curr_final.to_csv(index=False).encode('utf-8'), "Current_TB_Patients.csv", "text/csv", use_container_width=True)

try:
    df_times = pd.read_csv("Update_Timestamps.csv")
    time_html = "<div style='display:flex; flex-wrap:wrap; justify-content:center; gap:8px; margin-top:20px; padding-top:15px; border-top:1px solid #ddd;'>"
    for _, r in df_times.iterrows():
        color = "#27AE60" if r['Last Updated'] != "N/A" else "#C0392B"
        time_html += f"<div style='background:#f4f6f7; padding:4px 8px; border-radius:4px; text-align:center; border-left:3px solid {color}; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'><div style='font-size:9px; color:#666; text-transform:uppercase;'><b>{r['Register']}</b></div><div style='font-size:10px; color:#222; margin-top:1px;'>🕒 {r['Last Updated']}</div></div>"
    time_html += "</div>"
    st.markdown(time_html, unsafe_allow_html=True)
except:
    pass

st.markdown("<div class='amc-footer'>Created by District TB Center AMC | NTEP Monitoring System</div>", unsafe_allow_html=True)
