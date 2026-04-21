import streamlit as st
import pandas as pd
import base64

st.set_page_config(page_title="AMC NTEP Dashboard", layout="wide", initial_sidebar_state="expanded")

def img_to_b64(img_path):
    try:
        with open(img_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode('utf-8')
    except: return ""

if "auth" not in st.session_state: 
    st.session_state.auth = False
    st.session_state.current_user = ""
    st.session_state.role = ""
    st.session_state.target = ""

try:
    df_users = pd.read_csv("users.csv")
    df_users['Username'] = df_users['Username'].astype(str).str.strip().str.upper()
    df_users['Password'] = df_users['Password'].astype(str).str.strip()
except:
    st.error("⚠️ User Database (users.csv) મળ્યું નથી!")
    st.stop()

if not st.session_state.auth:
    st.markdown("<h2 style='text-align: center; color: #1f618d; margin-top: 10vh;'>AMC | NTEP Secure Login</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555;'>Log in with your Zone or TB Unit ID</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        uname = st.text_input("Username").strip().upper()
        pwd = st.text_input("Password", type="password").strip()
        
        if st.button("Login", use_container_width=True):
            user_match = df_users[(df_users['Username'] == uname) & (df_users['Password'] == pwd)]
            if not user_match.empty: 
                st.session_state.auth = True
                st.session_state.current_user = uname
                st.session_state.role = user_match.iloc[0]['Role']
                st.session_state.target = user_match.iloc[0]['Target']
                st.rerun()
            else: 
                st.error("⚠️ Invalid Username or Password")
    st.stop()

st.sidebar.markdown(f"### 👤 Logged in as:")
st.sidebar.success(f"**{st.session_state.target} ({st.session_state.role})**")

with st.sidebar.expander("🔑 Change My Password"):
    new_pwd = st.text_input("New Password", type="password", key="p1")
    conf_pwd = st.text_input("Confirm Password", type="password", key="p2")
    if st.button("Update Password", use_container_width=True):
        if new_pwd == conf_pwd and new_pwd != "":
            df_users.loc[df_users['Username'] == st.session_state.current_user, 'Password'] = new_pwd
            df_users.to_csv("users.csv", index=False)
            st.success("✅ Password updated!")
        else:
            st.error("⚠️ Passwords do not match!")

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Logout"):
    st.session_state.auth = False
    st.rerun()

st.markdown("""<style>#MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}</style>""", unsafe_allow_html=True)

try:
    df_master = pd.read_csv("Master_Line_List.csv")
    for col in ['Diagnosis Date', 'Initiation Date', 'Outcome Date']:
        if col in df_master.columns: df_master[col] = pd.to_datetime(df_master[col], errors='coerce')
    df_comp = pd.read_csv("Comparison_Matrix.csv")
    df_curr_tb = pd.read_csv("Current_TB_Patients.csv")
except:
    st.error("⚠️ ડેટા ઉપલબ્ધ નથી...")
    st.stop()

def filter_by_role(df, role, target):
    if df.empty: return df
    if role == "TB_UNIT" and 'TB Unit' in df.columns:
        return df[df['TB Unit'].astype(str).str.strip().str.upper() == target]
    elif role == "ZONE" and 'ZONE' in df.columns:
        valid_zones = [target, 'N/A', 'NAN', 'NONE']
        return df[df['ZONE'].astype(str).str.strip().str.upper().isin(valid_zones)]
    return df

df_master = filter_by_role(df_master, st.session_state.role, st.session_state.target)
df_comp = filter_by_role(df_comp, st.session_state.role, st.session_state.target)
df_curr_tb = filter_by_role(df_curr_tb, st.session_state.role, st.session_state.target)

def draw_card(title, value, color, icon):
    return f"""<div style="background-color: {color}; border-radius: 8px; padding: 15px 5px; margin-bottom: 10px; color: white; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"><div style="font-size: 24px; margin-bottom: 5px;">{icon}</div><div style="font-size: 13px; font-weight: bold; text-transform: uppercase;">{title}</div><div style="font-size: 26px; font-weight: 900; margin-top: 8px;">{value}</div></div>"""

def get_options_with_counts(df, column_name):
    counts = df[column_name].value_counts()
    return [f"{val} ({count})" for val, count in counts.items() if str(val) not in ["nan", "", "None", "N/A"]]

def clean_selection(selected_list):
    return [item.rsplit(" (", 1)[0] for item in selected_list]

b64_amc, b64_ntep = img_to_b64("images/amc.png"), img_to_b64("images/ntep.jpg")
b64_h1, b64_h2 = img_to_b64("images/h1.jpg"), img_to_b64("images/h2.jpg")

st.markdown(f"<div style='display: flex; justify-content: space-between; align-items: center;'><img src='data:image/png;base64,{b64_amc}' height='75'><h3 style='margin:0; font-weight:900;'>AMC | NTEP</h3><img src='data:image/jpeg;base64,{b64_ntep}' height='75'></div>", unsafe_allow_html=True)
st.markdown("<div style='background-color:#1f618d; color:white; text-align:center; padding:12px; border-radius:5px; margin:15px 0;'>TB Monitoring Dashboard - Ahmedabad</div>", unsafe_allow_html=True)

if b64_h1 and b64_h2:
    st.markdown(f"<div style='display:flex; gap:8px; margin-bottom: 20px;'><img src='data:image/jpeg;base64,{b64_h1}' style='width:50%; height:130px; object-fit:cover; border-radius:5px;'><img src='data:image/jpeg;base64,{b64_h2}' style='width:50%; height:130px; object-fit:cover; border-radius:5px;'></div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📊 Master Dashboard", "🔄 Daily Comparison", "🏥 Current TB Patients"])

# ==========================================
# 🟢 TAB 1: MASTER DASHBOARD
# ==========================================
with tab1:
    with st.expander("🔽 Filters & Sorting"):
        inds = ["Outcome", "UDST", "Not Put On", "SLPA", "Consent", "ADT", "RBS", "ART", "CPT", "HIV"]
        f_rep = st.multiselect("Report Type", inds, key='rep1')
        c1, c2 = st.columns(2)
        with c1:
            s_z = clean_selection(st.multiselect("Zone", get_options_with_counts(df_master, 'ZONE'), key='z1'))
            s_tu = clean_selection(st.multiselect("TB Unit", get_options_with_counts(df_master[df_master['ZONE'].isin(s_z)] if s_z else df_master, 'TB Unit'), key='tu1'))
        with c2:
            s_ft_raw = st.multiselect("Facility Category", ["PUBLIC", "PRIVATE"], key='fc1')
            s_phi = clean_selection(st.multiselect("PHI", get_options_with_counts(df_master, 'PHI'), key='phi1'))
    
    df_disp = df_master.copy()
    if s_z: df_disp = df_disp[df_disp['ZONE'].isin(s_z)]
    if s_tu: df_disp = df_disp[df_disp['TB Unit'].isin(s_tu)]
    if s_phi: df_disp = df_disp[df_disp['PHI'].isin(s_phi)]
    if f_rep: df_disp = df_disp[df_disp['Pending Status'].str.contains("|".join(f_rep), na=False)]
    
    if s_ft_raw:
        if "PUBLIC" in s_ft_raw and "PRIVATE" in s_ft_raw: pass
        elif "PUBLIC" in s_ft_raw: df_disp = df_disp[df_disp['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])]
        elif "PRIVATE" in s_ft_raw: df_disp = df_disp[~df_disp['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])]

    f_counts = {k: len(df_disp[df_disp['Pending Status'].str.contains(k, na=False)]) for k in inds}
    
    # 🎯 ડેશબોર્ડ બોક્સ (બધા જ 10 રિપોર્ટ માટે)
    st.markdown("##### 📈 Key Performance Indicators")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(draw_card("Total Pendency", len(df_disp), "#1f618d", "📄"), unsafe_allow_html=True)
    with c2: st.markdown(draw_card("Outcome Pending", f_counts["Outcome"], "#F39C12", "🏥"), unsafe_allow_html=True)
    with c3: st.markdown(draw_card("UDST Pending", f_counts["UDST"], "#C0392B", "🧪"), unsafe_allow_html=True)
    with c4: st.markdown(draw_card("Not Put On", f_counts["Not Put On"], "#27AE60", "⏳"), unsafe_allow_html=True)

    c5, c6, c7, c8 = st.columns(4)
    with c5: st.markdown(draw_card("SLPA", f_counts["SLPA"], "#8E44AD", "🔬"), unsafe_allow_html=True)
    with c6: st.markdown(draw_card("Consent", f_counts["Consent"], "#D35400", "📝"), unsafe_allow_html=True)
    with c7: st.markdown(draw_card("HIV", f_counts["HIV"], "#C0392B", "🩸"), unsafe_allow_html=True)
    with c8: st.markdown(draw_card("ART / CPT", f"{f_counts['ART']} / {f_counts['CPT']}", "#2980B9", "💊"), unsafe_allow_html=True)

    c9, c10, c11, _ = st.columns(4)
    with c9: st.markdown(draw_card("RBS", f_counts["RBS"], "#16A085", "🩺"), unsafe_allow_html=True)
    with c10: st.markdown(draw_card("ADT", f_counts["ADT"], "#E67E22", "📊"), unsafe_allow_html=True)
    
    st.dataframe(df_disp, use_container_width=True, hide_index=True)
    st.download_button("📥 Download This Report", df_disp.to_csv(index=False).encode('utf-8'), "Master_Report.csv", "text/csv", key='dl1')

# ==========================================
# 🟡 TAB 2: DAILY COMPARISON
# ==========================================
with tab2:
    st.markdown("#### 🔄 Comparison Matrix")
    with st.expander("🔽 Filters"):
        c1, c2, c3 = st.columns(3)
        with c1: 
            s2_z = clean_selection(st.multiselect("Filter Zone", get_options_with_counts(df_comp, 'ZONE'), key='z2'))
            s2_tu = clean_selection(st.multiselect("Filter TB Unit", get_options_with_counts(df_comp[df_comp['ZONE'].isin(s2_z)] if s2_z else df_comp, 'TB Unit'), key='tu2'))
        with c2: 
            s2_ft_raw = st.multiselect("Facility Category", ["PUBLIC", "PRIVATE"], key='fc2')
            s2_phi = clean_selection(st.multiselect("Filter PHI", get_options_with_counts(df_comp, 'PHI'), key='phi2'))
        with c3: 
            ignore_cols = ['ZONE', 'TB Unit', 'PHI', 'Episode ID', 'Patient Name', 'Facility Type']
            s2_ind = st.multiselect("Filter by Report Type", [c for c in df_comp.columns if c not in ignore_cols], key='ind2')
            s2_stat = st.multiselect("Filter by Status", ["🔴 NEW", "🟢 RESOLVED", "🟡 PERSISTENT"], key='stat2')
            
    df_c = df_comp.copy()
    if s2_z: df_c = df_c[df_c['ZONE'].isin(s2_z)]
    if s2_tu: df_c = df_c[df_c['TB Unit'].isin(s2_tu)]
    if s2_phi: df_c = df_c[df_c['PHI'].isin(s2_phi)]
    if s2_ft_raw:
        if "PUBLIC" in s2_ft_raw and "PRIVATE" in s2_ft_raw: pass
        elif "PUBLIC" in s2_ft_raw: df_c = df_c[df_c['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])]
        elif "PRIVATE" in s2_ft_raw: df_c = df_c[~df_c['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])]
    
    if s2_ind or s2_stat:
        inds_to_check = s2_ind if s2_ind else [c for c in df_c.columns if c not in ignore_cols]
        stats_to_check = s2_stat if s2_stat else ["🔴 NEW", "🟢 RESOLVED", "🟡 PERSISTENT"]
        mask = pd.Series(False, index=df_c.index)
        for ind in inds_to_check:
            if ind in df_c.columns:
                mask = mask | df_c[ind].isin(stats_to_check)
        df_c = df_c[mask]
        
    # 🎯 Tab 2 ના નવા KPI બોક્સ (New / Resolved)
    ind_cols_in_df = [c for c in df_c.columns if c not in ignore_cols]
    new_c = (df_c[ind_cols_in_df] == "🔴 NEW").sum().sum()
    res_c = (df_c[ind_cols_in_df] == "🟢 RESOLVED").sum().sum()
    per_c = (df_c[ind_cols_in_df] == "🟡 PERSISTENT").sum().sum()
    
    st.markdown("##### 📈 Daily Action Status")
    cc1, cc2, cc3 = st.columns(3)
    with cc1: st.markdown(draw_card("🔴 NEW PENDENCY", new_c, "#E74C3C", "🚨"), unsafe_allow_html=True)
    with cc2: st.markdown(draw_card("🟢 RESOLVED", res_c, "#27AE60", "✅"), unsafe_allow_html=True)
    with cc3: st.markdown(draw_card("🟡 PERSISTENT", per_c, "#F1C40F", "⏳"), unsafe_allow_html=True)

    st.dataframe(df_c, use_container_width=True, hide_index=True)
    st.download_button("📥 Download Comparison", df_c.to_csv(index=False).encode('utf-8'), "Comparison_Matrix.csv", "text/csv", key='dl2')

# ==========================================
# 🔵 TAB 3: CURRENT TB PATIENTS
# ==========================================
with tab3:
    st.markdown("#### 🏥 Current TB Patients")
    with st.expander("🔽 Filters"):
        c1, c2 = st.columns(2)
        with c1:
            s3_z = clean_selection(st.multiselect("Filter Zone", get_options_with_counts(df_curr_tb, 'ZONE'), key='z3'))
            s3_tu = clean_selection(st.multiselect("Filter TB Unit", get_options_with_counts(df_curr_tb[df_curr_tb['ZONE'].isin(s3_z)] if s3_z else df_curr_tb, 'TB Unit'), key='tu3'))
        with c2:
            s3_ft_raw = st.multiselect("Facility Category", ["PUBLIC", "PRIVATE"], key='fc3')
            s3_phi = clean_selection(st.multiselect("Filter PHI", get_options_with_counts(df_curr_tb, 'PHI'), key='phi3'))
            
    df_t3 = df_curr_tb.copy()
    if s3_z: df_t3 = df_t3[df_t3['ZONE'].isin(s3_z)]
    if s3_tu: df_t3 = df_t3[df_t3['TB Unit'].isin(s3_tu)]
    if s3_phi: df_t3 = df_t3[df_t3['PHI'].isin(s3_phi)]
    if s3_ft_raw:
        if "PUBLIC" in s3_ft_raw and "PRIVATE" in s3_ft_raw: pass
        elif "PUBLIC" in s3_ft_raw: df_t3 = df_t3[df_t3['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])]
        elif "PRIVATE" in s3_ft_raw: df_t3 = df_t3[~df_t3['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])]

    # 🎯 Tab 3 નો નવો ચોક્કસ ક્રમ
    t3_col_order = ['ZONE', 'TB Unit', 'PHI', 'Facility Type', 'Episode ID', 'Patient Name', 'Type of Case', 'TB_regimen', 'Diagnosis Date', 'Initiation Date', 'Outcome Date']
    t3_final_cols = [c for c in t3_col_order if c in df_t3.columns]
    
    st.dataframe(df_t3[t3_final_cols], use_container_width=True, hide_index=True)
    st.download_button("📥 Download Patient List", df_t3[t3_final_cols].to_csv(index=False).encode('utf-8'), "Current_Patients.csv", "text/csv", key='dl3')
