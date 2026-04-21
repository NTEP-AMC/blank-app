import streamlit as st
import pandas as pd
import base64

st.set_page_config(page_title="AMC NTEP Dashboard", layout="wide", initial_sidebar_state="collapsed")

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

# ==========================================
# 🔐 LOGIN SCREEN
# ==========================================
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

st.markdown("""<style>#MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}</style>""", unsafe_allow_html=True)

# ==========================================
# 👤 USER PROFILE & SETTINGS
# ==========================================
st.markdown(f"""
<div style='background-color: #d4edda; color: #155724; padding: 12px; border-radius: 8px; border: 1px solid #c3e6cb; margin-bottom: 10px; font-size: 16px; font-weight: bold;'>
    👤 Logged in as: <span style='color: #0b2e13; font-size: 18px;'>{st.session_state.target} ({st.session_state.role})</span>
</div>
""", unsafe_allow_html=True)

with st.expander("⚙️ Account Settings & Change Password"):
    c_p1, c_p2, c_p3 = st.columns([2, 2, 1])
    with c_p1: new_pwd = st.text_input("New Password", type="password", key="p1")
    with c_p2: conf_pwd = st.text_input("Confirm Password", type="password", key="p2")
    with c_p3:
        st.write("") 
        st.write("")
        if st.button("Update Password", use_container_width=True):
            if new_pwd == conf_pwd and new_pwd != "":
                df_users.loc[df_users['Username'] == st.session_state.current_user, 'Password'] = new_pwd
                df_users.to_csv("users.csv", index=False)
                st.success("✅ Password updated!")
            else:
                st.error("⚠️ Passwords do not match!")
    
    st.markdown("---")
    if st.button("🚪 Logout Securely"):
        st.session_state.auth = False
        st.rerun()

st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)

# ==========================================
# 📊 LOAD DATA
# ==========================================
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

# 🎯 નવું સ્માર્ટ કાઉન્ટર: જે દર્દી નહિ, પણ "પેન્ડન્સી (Actions)" ગણશે!
def get_options_with_counts(df, column_name, tab_name="tab1"):
    if df.empty: return []
    try:
        if tab_name == "tab1" and 'Pending Status' in df.columns:
            df_temp = df.copy()
            df_temp['act_cnt'] = df_temp['Pending Status'].astype(str).apply(lambda x: len([s for s in x.split('+') if s.strip()]))
            counts = df_temp.groupby(column_name)['act_cnt'].sum()
        elif tab_name == "tab2":
            std_cols = ['ZONE', 'TB Unit', 'PHI', 'Episode ID', 'Patient Name', 'Facility Type']
            ind_cols = [c for c in df.columns if c not in std_cols]
            df_temp = df.copy()
            df_temp['act_cnt'] = df_temp[ind_cols].apply(lambda row: sum(row.astype(str).str.strip() != ""), axis=1)
            counts = df_temp.groupby(column_name)['act_cnt'].sum()
        else:
            counts = df[column_name].value_counts()
            
        counts = counts[counts > 0].sort_values(ascending=False)
        return [f"{val} ({int(count)})" for val, count in counts.items() if str(val) not in ["nan", "", "None", "N/A"]]
    except:
        return []

def clean_selection(selected_list):
    return [item.rsplit(" (", 1)[0] for item in selected_list]

b64_amc, b64_ntep = img_to_b64("images/amc.png"), img_to_b64("images/ntep.jpg")

st.markdown(f"<div style='display: flex; justify-content: space-between; align-items: center;'><img src='data:image/png;base64,{b64_amc}' height='75'><h3 style='margin:0; font-weight:900;'>AMC | NTEP</h3><img src='data:image/jpeg;base64,{b64_ntep}' height='75'></div>", unsafe_allow_html=True)
st.markdown("<div style='background-color:#1f618d; color:white; text-align:center; padding:12px; border-radius:5px; margin:15px 0;'>TB Monitoring Dashboard - Ahmedabad</div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📊 Master Dashboard", "🔄 Daily Comparison", "🏥 Current TB Patients"])

# ==========================================
# 🟢 TAB 1: MASTER DASHBOARD 
# ==========================================
with tab1:
    with st.expander("🔽 Filters & Sorting"):
        c1, c2, c3 = st.columns(3)
        df_disp = df_master.copy()
        
        with c1:
            if st.session_state.role == "ADMIN":
                s_z = clean_selection(st.multiselect("Zone", get_options_with_counts(df_disp, 'ZONE', 'tab1'), key='z1'))
                if s_z: df_disp = df_disp[df_disp['ZONE'].isin(s_z)]
            
            if st.session_state.role in ["ADMIN", "ZONE"]:
                s_tu = clean_selection(st.multiselect("TB Unit", get_options_with_counts(df_disp, 'TB Unit', 'tab1'), key='tu1'))
                if s_tu: df_disp = df_disp[df_disp['TB Unit'].isin(s_tu)]
                
        with c2:
            # 🎯 Facility Category પહેલા આવશે, જેથી તે PHI ને ફિલ્ટર કરી શકે!
            available_facs = df_disp['Facility Type'].str.upper().unique()
            fac_opts = []
            if any(f in ['PUBLIC', 'PHI'] for f in available_facs): fac_opts.append("PUBLIC")
            if any(f not in ['PUBLIC', 'PHI', 'N/A', 'NAN', ''] for f in available_facs): fac_opts.append("PRIVATE")
            
            s_ft_raw = st.multiselect("Facility Category", fac_opts, key='fc1')
            if s_ft_raw:
                if "PUBLIC" in s_ft_raw and "PRIVATE" in s_ft_raw: pass
                elif "PUBLIC" in s_ft_raw: df_disp = df_disp[df_disp['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])]
                elif "PRIVATE" in s_ft_raw: df_disp = df_disp[~df_disp['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])]
            
            # હવે PHI અપડેટેડ ડેટામાંથી આવશે
            s_phi = clean_selection(st.multiselect("PHI", get_options_with_counts(df_disp, 'PHI', 'tab1'), key='phi1'))
            if s_phi: df_disp = df_disp[df_disp['PHI'].isin(s_phi)]
            
            inds = ["Outcome", "UDST", "Not Put On", "SLPA", "Consent", "ADT", "RBS", "ART", "CPT", "HIV"]
            f_rep = st.multiselect("Report Type", inds, key='rep1')

        with c3:
            diag_dt = st.date_input("Diagnosis Date Range", value=[], key="d1")
            init_dt = st.date_input("Initiation Date Range", value=[], key="d2")
            out_dt = st.date_input("Outcome Date Range", value=[], key="d3")
            
        if len(diag_dt) == 2: df_disp = df_disp[df_disp['Diagnosis Date'].notna() & df_disp['Diagnosis Date'].dt.date.between(diag_dt[0], diag_dt[1])]
        if len(init_dt) == 2: df_disp = df_disp[df_disp['Initiation Date'].notna() & df_disp['Initiation Date'].dt.date.between(init_dt[0], init_dt[1])]
        if len(out_dt) == 2: df_disp = df_disp[df_disp['Outcome Date'].notna() & df_disp['Outcome Date'].dt.date.between(out_dt[0], out_dt[1])]

        if f_rep: df_disp = df_disp[df_disp['Pending Status'].str.contains("|".join(f_rep), na=False)]

    f_counts = {k: len(df_disp[df_disp['Pending Status'].str.contains(k, na=False)]) for k in inds}
    total_actions_t1 = sum(f_counts.values())
    
    sorted_counts = sorted(f_counts.items(), key=lambda x: x[1], reverse=True)
    top_3 = sorted_counts[:3]
    others = sorted_counts[3:]
    
    icons = {"Outcome": "🏥", "UDST": "🧪", "Not Put On": "⏳", "SLPA": "🔬", "Consent": "📝", "HIV": "🩸", "ART": "💊", "CPT": "💊", "RBS": "🩺", "ADT": "📊"}
    colors = {"Outcome": "#F39C12", "UDST": "#C0392B", "Not Put On": "#27AE60", "SLPA": "#8E44AD", "Consent": "#D35400", "HIV": "#C0392B", "ART": "#2980B9", "CPT": "#2980B9", "RBS": "#16A085", "ADT": "#E67E22"}

    st.markdown("##### 📈 Top 3 Highest Pending Actions")
    cc1, cc2, cc3, cc4 = st.columns(4)
    with cc1: st.markdown(draw_card("Total Pendency", total_actions_t1, "#1f618d", "📄"), unsafe_allow_html=True)
    with cc2: st.markdown(draw_card(top_3[0][0], top_3[0][1], colors.get(top_3[0][0], "#34495E"), icons.get(top_3[0][0], "📌")), unsafe_allow_html=True)
    with cc3: st.markdown(draw_card(top_3[1][0], top_3[1][1], colors.get(top_3[1][0], "#34495E"), icons.get(top_3[1][0], "📌")), unsafe_allow_html=True)
    with cc4: st.markdown(draw_card(top_3[2][0], top_3[2][1], colors.get(top_3[2][0], "#34495E"), icons.get(top_3[2][0], "📌")), unsafe_allow_html=True)

    with st.expander("🔽 Tap to show other reports"):
        oc_cols = st.columns(4)
        for i, (k, v) in enumerate(others):
            with oc_cols[i % 4]:
                st.markdown(draw_card(k, v, colors.get(k, "#34495E"), icons.get(k, "📌")), unsafe_allow_html=True)
    
    st.dataframe(df_disp, use_container_width=True, hide_index=True)
    st.download_button("📥 Download This Report", df_disp.to_csv(index=False).encode('utf-8'), "Master_Report.csv", "text/csv", key='dl1')

# ==========================================
# 🟡 TAB 2: DAILY COMPARISON
# ==========================================
with tab2:
    st.markdown("#### 🔄 Comparison Matrix")
    with st.expander("🔽 Filters"):
        c1, c2, c3 = st.columns(3)
        df_c = df_comp.copy()
        
        with c1: 
            if st.session_state.role == "ADMIN":
                s2_z = clean_selection(st.multiselect("Filter Zone", get_options_with_counts(df_c, 'ZONE', 'tab2'), key='z2'))
                if s2_z: df_c = df_c[df_c['ZONE'].isin(s2_z)]
            
            if st.session_state.role in ["ADMIN", "ZONE"]:
                s2_tu = clean_selection(st.multiselect("Filter TB Unit", get_options_with_counts(df_c, 'TB Unit', 'tab2'), key='tu2'))
                if s2_tu: df_c = df_c[df_c['TB Unit'].isin(s2_tu)]

        with c2: 
            # Facility Type First!
            available_facs2 = df_c['Facility Type'].str.upper().unique()
            fac_opts2 = []
            if any(f in ['PUBLIC', 'PHI'] for f in available_facs2): fac_opts2.append("PUBLIC")
            if any(f not in ['PUBLIC', 'PHI', 'N/A', 'NAN', ''] for f in available_facs2): fac_opts2.append("PRIVATE")

            s2_ft_raw = st.multiselect("Facility Category", fac_opts2, key='fc2')
            if s2_ft_raw:
                if "PUBLIC" in s2_ft_raw and "PRIVATE" in s2_ft_raw: pass
                elif "PUBLIC" in s2_ft_raw: df_c = df_c[df_c['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])]
                elif "PRIVATE" in s2_ft_raw: df_c = df_c[~df_c['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])]
                
            s2_phi = clean_selection(st.multiselect("Filter PHI", get_options_with_counts(df_c, 'PHI', 'tab2'), key='phi2'))
            if s2_phi: df_c = df_c[df_c['PHI'].isin(s2_phi)]
        
        with c3: 
            ignore_cols = ['ZONE', 'TB Unit', 'PHI', 'Episode ID', 'Patient Name', 'Facility Type']
            s2_ind = st.multiselect("Filter by Report Type", [c for c in df_c.columns if c not in ignore_cols], key='ind2')
            s2_stat = st.multiselect("Filter by Status", ["🔴 NEW", "🟢 RESOLVED", "🟡 PERSISTENT"], key='stat2')
            
    if s2_ind or s2_stat:
        inds_to_check = s2_ind if s2_ind else [c for c in df_c.columns if c not in ignore_cols]
        stats_to_check = s2_stat if s2_stat else ["🔴 NEW", "🟢 RESOLVED", "🟡 PERSISTENT"]
        mask = pd.Series(False, index=df_c.index)
        for ind in inds_to_check:
            if ind in df_c.columns:
                mask = mask | df_c[ind].isin(stats_to_check)
        df_c = df_c[mask]
        
    ind_cols_in_df = [c for c in df_c.columns if c not in ignore_cols]
    new_c = (df_c[ind_cols_in_df] == "🔴 NEW").sum().sum()
    res_c = (df_c[ind_cols_in_df] == "🟢 RESOLVED").sum().sum()
    per_c = (df_c[ind_cols_in_df] == "🟡 PERSISTENT").sum().sum()
    total_pendency_c = new_c + per_c
    
    st.markdown("##### 📈 Daily Action Status")
    cc1, cc2, cc3, cc4 = st.columns(4)
    with cc1: st.markdown(draw_card("TOTAL PENDENCY", total_pendency_c, "#1f618d", "📄"), unsafe_allow_html=True)
    with cc2: st.markdown(draw_card("🔴 NEW", new_c, "#E74C3C", "🚨"), unsafe_allow_html=True)
    with cc3: st.markdown(draw_card("🟡 PERSISTENT", per_c, "#F1C40F", "⏳"), unsafe_allow_html=True)
    with cc4: st.markdown(draw_card("🟢 RESOLVED", res_c, "#27AE60", "✅"), unsafe_allow_html=True)

    st.dataframe(df_c, use_container_width=True, hide_index=True)
    st.download_button("📥 Download Comparison", df_c.to_csv(index=False).encode('utf-8'), "Comparison_Matrix.csv", "text/csv", key='dl2')

# ==========================================
# 🔵 TAB 3: CURRENT TB PATIENTS
# ==========================================
with tab3:
    st.markdown("#### 🏥 Current TB Patients")
    with st.expander("🔽 Filters"):
        c1, c2, c3 = st.columns(3)
        df_t3 = df_curr_tb.copy()
        
        with c1:
            if st.session_state.role == "ADMIN":
                s3_z = clean_selection(st.multiselect("Filter Zone", get_options_with_counts(df_t3, 'ZONE', 'tab3'), key='z3'))
                if s3_z: df_t3 = df_t3[df_t3['ZONE'].isin(s3_z)]
            
            if st.session_state.role in ["ADMIN", "ZONE"]:
                s3_tu = clean_selection(st.multiselect("Filter TB Unit", get_options_with_counts(df_t3, 'TB Unit', 'tab3'), key='tu3'))
                if s3_tu: df_t3 = df_t3[df_t3['TB Unit'].isin(s3_tu)]
                
        with c2:
            available_facs3 = df_t3['Facility Type'].str.upper().unique()
            fac_opts3 = []
            if any(f in ['PUBLIC', 'PHI'] for f in available_facs3): fac_opts3.append("PUBLIC")
            if any(f not in ['PUBLIC', 'PHI', 'N/A', 'NAN', ''] for f in available_facs3): fac_opts3.append("PRIVATE")

            s3_ft_raw = st.multiselect("Facility Category", fac_opts3, key='fc3')
            if s3_ft_raw:
                if "PUBLIC" in s3_ft_raw and "PRIVATE" in s3_ft_raw: pass
                elif "PUBLIC" in s3_ft_raw: df_t3 = df_t3[df_t3['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])]
                elif "PRIVATE" in s3_ft_raw: df_t3 = df_t3[~df_t3['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])]

            s3_phi = clean_selection(st.multiselect("Filter PHI", get_options_with_counts(df_t3, 'PHI', 'tab3'), key='phi3'))
            if s3_phi: df_t3 = df_t3[df_t3['PHI'].isin(s3_phi)]

    t3_col_order = ['ZONE', 'TB Unit', 'PHI', 'Facility Type', 'Episode ID', 'Patient Name', 'Type of Case', 'TB_regimen', 'Diagnosis Date', 'Initiation Date', 'Outcome Date']
    t3_final_cols = [c for c in t3_col_order if c in df_t3.columns]
    
    st.dataframe(df_t3[t3_final_cols], use_container_width=True, hide_index=True)
    st.download_button("📥 Download Patient List", df_t3[t3_final_cols].to_csv(index=False).encode('utf-8'), "Current_Patients.csv", "text/csv", key='dl3')
