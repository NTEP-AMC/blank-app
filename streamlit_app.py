import streamlit as st
import pandas as pd
import base64
import os
from datetime import datetime
import pytz

st.set_page_config(page_title="AMC NTEP Dashboard", layout="wide", initial_sidebar_state="collapsed")

def img_to_b64(img_path):
    try:
        with open(img_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode('utf-8')
    except: return ""

LOG_FILE = "activity_log.csv"
india_tz = pytz.timezone('Asia/Kolkata')

def log_activity(username, role, target, action):
    if not os.path.exists(LOG_FILE):
        df_log = pd.DataFrame(columns=["Timestamp", "Username", "Role", "Target", "Action"])
        df_log.to_csv(LOG_FILE, index=False)
    current_time = datetime.now(india_tz).strftime("%d-%b-%Y, %I:%M %p")
    new_entry = pd.DataFrame([{"Timestamp": current_time, "Username": username, "Role": role, "Target": target, "Action": action}])
    new_entry.to_csv(LOG_FILE, mode='a', header=False, index=False)

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
                log_activity(st.session_state.current_user, st.session_state.role, st.session_state.target, "Logged In")
                st.rerun()
            else: st.error("⚠️ Invalid Username or Password")
    st.stop()

st.markdown("""<style>#MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}</style>""", unsafe_allow_html=True)

st.markdown(f"<div style='background-color: #d4edda; color: #155724; padding: 12px; border-radius: 8px; border: 1px solid #c3e6cb; margin-bottom: 10px; font-size: 16px; font-weight: bold;'>👤 Logged in as: <span style='color: #0b2e13; font-size: 18px;'>{st.session_state.target} ({st.session_state.role})</span></div>", unsafe_allow_html=True)

with st.expander("⚙️ Account Settings & Change Password"):
    c_p0, c_p1, c_p2, c_p3 = st.columns([2, 2, 2, 1])
    with c_p0: old_pwd = st.text_input("Old Password", type="password", key="p0")
    with c_p1: new_pwd = st.text_input("New Password", type="password", key="p1")
    with c_p2: conf_pwd = st.text_input("Confirm Password", type="password", key="p2")
    with c_p3:
        st.write(""); st.write("")
        if st.button("Update", use_container_width=True):
            current_actual_pwd = df_users.loc[df_users['Username'] == st.session_state.current_user, 'Password'].values[0]
            if old_pwd != current_actual_pwd: st.error("⚠️ Old Password is incorrect!")
            elif new_pwd != conf_pwd: st.error("⚠️ New Passwords do not match!")
            elif new_pwd == "": st.error("⚠️ Password cannot be empty!")
            else:
                df_users.loc[df_users['Username'] == st.session_state.current_user, 'Password'] = new_pwd
                df_users.to_csv("users.csv", index=False)
                log_activity(st.session_state.current_user, st.session_state.role, st.session_state.target, "Password Changed")
                st.success("✅ Password updated!")
    st.markdown("---")
    if st.button("🚪 Logout Securely"):
        log_activity(st.session_state.current_user, st.session_state.role, st.session_state.target, "Logged Out")
        st.session_state.auth = False
        st.rerun()

if st.session_state.role == "ADMIN":
    with st.expander("🛡️ Admin Panel: View Passwords & Activity Logs"):
        a_tab1, a_tab2 = st.tabs(["🔑 Manage Users", "📝 Activity Logs"])
        with a_tab1:
            st.warning("⚠️ Strictly Confidential: Live User Credentials")
            st.dataframe(df_users, use_container_width=True, hide_index=True)
            st.download_button("📥 Download Credentials", df_users.to_csv(index=False).encode('utf-8'), "Users_Passwords.csv", "text/csv", key='dl_cred')
        with a_tab2:
            st.info("📊 Tracking user logins and downloads.")
            try:
                df_logs = pd.read_csv(LOG_FILE)
                st.dataframe(df_logs.iloc[::-1], use_container_width=True, hide_index=True)
                st.download_button("📥 Download Logs", df_logs.to_csv(index=False).encode('utf-8'), "Activity_Logs.csv", "text/csv", key='dl_logs')
            except: st.write("No logs available yet.")

st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)

try:
    df_master = pd.read_csv("Master_Line_List.csv")
    for col in ['Diagnosis Date', 'Initiation Date', 'Outcome Date']:
        if col in df_master.columns: df_master[col] = pd.to_datetime(df_master[col], errors='coerce')
    df_comp = pd.read_csv("Comparison_Matrix.csv")
    df_curr_tb = pd.read_csv("Current_TB_Patients.csv")
    df_time = pd.read_csv("Update_Timestamps.csv")
    df_dtb_care = pd.read_csv("Differentiated_Care.csv")
except Exception as e:
    st.error("⚠️ ડેટા ઉપલબ્ધ નથી...")
    df_dtb_care = pd.DataFrame()

def filter_by_role(df, role, target):
    if df.empty: return df
    if role == "TB_UNIT" and 'TB Unit' in df.columns: return df[df['TB Unit'].astype(str).str.strip().str.upper() == target]
    elif role == "ZONE" and 'ZONE' in df.columns: return df[df['ZONE'].astype(str).str.strip().str.upper().isin([target, 'N/A', 'NAN', 'NONE'])]
    return df

df_master = filter_by_role(df_master, st.session_state.role, st.session_state.target)
df_comp = filter_by_role(df_comp, st.session_state.role, st.session_state.target)
df_curr_tb = filter_by_role(df_curr_tb, st.session_state.role, st.session_state.target)
df_dtb_care = filter_by_role(df_dtb_care, st.session_state.role, st.session_state.target)

def draw_card(title, value, color, icon):
    return f"""<div style="background-color: {color}; border-radius: 8px; padding: 15px 5px; margin-bottom: 10px; color: white; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"><div style="font-size: 24px; margin-bottom: 5px;">{icon}</div><div style="font-size: 13px; font-weight: bold; text-transform: uppercase;">{title}</div><div style="font-size: 26px; font-weight: 900; margin-top: 8px;">{value}</div></div>"""

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
    except: return []

def clean_selection(selected_list): return [item.rsplit(" (", 1)[0] for item in selected_list]

b64_amc, b64_ntep = img_to_b64("images/amc.png"), img_to_b64("images/ntep.jpg")
st.markdown(f"<div style='display: flex; justify-content: space-between; align-items: center;'><img src='data:image/png;base64,{b64_amc}' height='75'><h3 style='margin:0; font-weight:900;'>AMC | NTEP</h3><img src='data:image/jpeg;base64,{b64_ntep}' height='75'></div>", unsafe_allow_html=True)
st.markdown("<div style='background-color:#1f618d; color:white; text-align:center; padding:12px; border-radius:5px; margin:15px 0;'>TB Monitoring Dashboard - Ahmedabad</div>", unsafe_allow_html=True)

if not df_time.empty:
    with st.expander("🕒 Register Last Sync Timestamps (IST)"):
        t_cols = st.columns(5)
        for i, row in df_time.iterrows():
            with t_cols[i % 5]: st.markdown(f"<div style='font-size:13px; color:#333;'><b>{row['Register']}</b><br><span style='color:#E67E22;'>{row['Last Updated']}</span></div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📊 Master Dashboard", "🔄 Daily Comparison", "🏥 Current TB Patients", "⚕️ Differentiated TB Care"])

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
            available_facs = df_disp['Facility Type'].str.upper().unique()
            fac_opts = [f for f in ["PUBLIC", "PRIVATE"] if any(a in ["PUBLIC", "PHI"] if f=="PUBLIC" else a not in ["PUBLIC", "PHI", "N/A", "NAN", ""] for a in available_facs)]
            s_ft_raw = st.multiselect("Facility Category", fac_opts, key='fc1')
            if s_ft_raw:
                if "PUBLIC" in s_ft_raw and "PRIVATE" in s_ft_raw: pass
                elif "PUBLIC" in s_ft_raw: df_disp = df_disp[df_disp['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])]
                elif "PRIVATE" in s_ft_raw: df_disp = df_disp[~df_disp['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])]
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
    sorted_counts = sorted(f_counts.items(), key=lambda x: x[1], reverse=True)
    top_3, others = sorted_counts[:3], sorted_counts[3:]
    colors = {"Outcome": "#F39C12", "UDST": "#C0392B", "Not Put On": "#27AE60", "SLPA": "#8E44AD", "Consent": "#D35400", "HIV": "#C0392B", "ART": "#2980B9", "CPT": "#2980B9", "RBS": "#16A085", "ADT": "#E67E22"}
    
    st.markdown("##### 📈 Top 3 Highest Pending Actions")
    cc1, cc2, cc3, cc4 = st.columns(4)
    with cc1: st.markdown(draw_card("Total Pendency", sum(f_counts.values()), "#1f618d", "📄"), unsafe_allow_html=True)
    with cc2: st.markdown(draw_card(top_3[0][0], top_3[0][1], colors.get(top_3[0][0], "#34495E"), "📌"), unsafe_allow_html=True)
    with cc3: st.markdown(draw_card(top_3[1][0], top_3[1][1], colors.get(top_3[1][0], "#34495E"), "📌"), unsafe_allow_html=True)
    with cc4: st.markdown(draw_card(top_3[2][0], top_3[2][1], colors.get(top_3[2][0], "#34495E"), "📌"), unsafe_allow_html=True)

    with st.expander("🔽 Tap to show other reports"):
        oc_cols = st.columns(4)
        for i, (k, v) in enumerate(others):
            with oc_cols[i % 4]: st.markdown(draw_card(k, v, colors.get(k, "#34495E"), "📌"), unsafe_allow_html=True)
    
    st.dataframe(df_disp, use_container_width=True, hide_index=True)
    st.download_button("📥 Download This Report", df_disp.to_csv(index=False).encode('utf-8'), "Master_Report.csv", "text/csv", key='dl1', on_click=log_activity, args=(st.session_state.current_user, st.session_state.role, st.session_state.target, "Downloaded Master Report"))

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
            available_facs2 = df_c['Facility Type'].str.upper().unique()
            fac_opts2 = [f for f in ["PUBLIC", "PRIVATE"] if any(a in ["PUBLIC", "PHI"] if f=="PUBLIC" else a not in ["PUBLIC", "PHI", "N/A", "NAN", ""] for a in available_facs2)]
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
        mask = pd.Series(False, index=df_c.index)
        for ind in (s2_ind if s2_ind else [c for c in df_c.columns if c not in ignore_cols]):
            if ind in df_c.columns: mask = mask | df_c[ind].isin(s2_stat if s2_stat else ["🔴 NEW", "🟢 RESOLVED", "🟡 PERSISTENT"])
        df_c = df_c[mask]
        
    ind_cols_in_df = [c for c in df_c.columns if c not in ignore_cols]
    new_c, res_c, per_c = (df_c[ind_cols_in_df] == "🔴 NEW").sum().sum(), (df_c[ind_cols_in_df] == "🟢 RESOLVED").sum().sum(), (df_c[ind_cols_in_df] == "🟡 PERSISTENT").sum().sum()
    
    st.markdown("##### 📈 Daily Action Status")
    cc1, cc2, cc3, cc4 = st.columns(4)
    with cc1: st.markdown(draw_card("TOTAL PENDENCY", new_c + per_c, "#1f618d", "📄"), unsafe_allow_html=True)
    with cc2: st.markdown(draw_card("🔴 NEW", new_c, "#E74C3C", "🚨"), unsafe_allow_html=True)
    with cc3: st.markdown(draw_card("🟡 PERSISTENT", per_c, "#F1C40F", "⏳"), unsafe_allow_html=True)
    with cc4: st.markdown(draw_card("🟢 RESOLVED", res_c, "#27AE60", "✅"), unsafe_allow_html=True)

    st.dataframe(df_c, use_container_width=True, hide_index=True)
    st.download_button("📥 Download Comparison", df_c.to_csv(index=False).encode('utf-8'), "Comparison_Matrix.csv", "text/csv", key='dl2', on_click=log_activity, args=(st.session_state.current_user, st.session_state.role, st.session_state.target, "Downloaded Comparison Report"))

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
            fac_opts3 = [f for f in ["PUBLIC", "PRIVATE"] if any(a in ["PUBLIC", "PHI"] if f=="PUBLIC" else a not in ["PUBLIC", "PHI", "N/A", "NAN", ""] for a in available_facs3)]
            s3_ft_raw = st.multiselect("Facility Category", fac_opts3, key='fc3')
            if s3_ft_raw:
                if "PUBLIC" in s3_ft_raw and "PRIVATE" in s3_ft_raw: pass
                elif "PUBLIC" in s3_ft_raw: df_t3 = df_t3[df_t3['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])]
                elif "PRIVATE" in s3_ft_raw: df_t3 = df_t3[~df_t3['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])]
            s3_phi = clean_selection(st.multiselect("Filter PHI", get_options_with_counts(df_t3, 'PHI', 'tab3'), key='phi3'))
            if s3_phi: df_t3 = df_t3[df_t3['PHI'].isin(s3_phi)]

    st.markdown("##### 📈 Patient Overview")
    c_t3, _, _, _ = st.columns(4)
    with c_t3: st.markdown(draw_card("Total Active Patients", len(df_t3), "#16A085", "🏥"), unsafe_allow_html=True)

    t3_final_cols = [c for c in ['ZONE', 'TB Unit', 'PHI', 'Facility Type', 'Episode ID', 'Patient Name', 'Type of Case', 'TB_regimen', 'Diagnosis Date', 'Initiation Date', 'Outcome Date'] if c in df_t3.columns]
    st.dataframe(df_t3[t3_final_cols], use_container_width=True, hide_index=True)
    st.download_button("📥 Download Patient List", df_t3[t3_final_cols].to_csv(index=False).encode('utf-8'), "Current_Patients.csv", "text/csv", key='dl3', on_click=log_activity, args=(st.session_state.current_user, st.session_state.role, st.session_state.target, "Downloaded Current Patients List"))

# ==========================================
# 🟣 TAB 4: DIFFERENTIATED TB CARE 
# ==========================================
with tab4:
    st.markdown("<h3 style='text-align: center; background-color: #d4edda; color: #155724; padding: 10px; border-radius: 10px; border: 2px solid #000;'>NTEP - AMC DIFF CARE</h3>", unsafe_allow_html=True)
    
    if not df_dtb_care.empty:
        df_t4 = df_dtb_care.copy()
        
        for col in ['Diagnosis Date', 'Initiation Date', 'Outcome Date']:
            if col in df_t4.columns: df_t4[col] = pd.to_datetime(df_t4[col], errors='coerce')
        
        df_t4['Notification Month'] = df_t4['Diagnosis Date'].dt.strftime('%b-%Y').fillna("N/A")
        df_t4['Initiation Month'] = df_t4['Initiation Date'].dt.strftime('%b-%Y').fillna("N/A")
        df_t4['Outcome Month'] = df_t4['Outcome Date'].dt.strftime('%b-%Y').fillna("N/A")
        df_t4['Treatment Status'] = df_t4['Treatment Outcome'].apply(lambda x: "Active" if pd.isna(x) or x in ["", "N/A", "NAN", "NONE"] else "Outcome Assigned")
        df_t4['Treatment Outcome Display'] = df_t4['Treatment Outcome'].replace("N/A", "BLANK (ACTIVE)")

        with st.expander("🔽 Looker Studio Filters", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.session_state.role == "ADMIN":
                    s4_z = clean_selection(st.multiselect("ZONE", get_options_with_counts(df_t4, 'ZONE', 'tab4'), key='z4'))
                    if s4_z: df_t4 = df_t4[df_t4['ZONE'].isin(s4_z)]
                
                avail_facs4 = df_t4['Facility Type'].str.upper().unique()
                fac_opts4 = [f for f in ["PUBLIC", "PRIVATE"] if any(a in ["PUBLIC", "PHI"] if f=="PUBLIC" else a not in ["PUBLIC", "PHI", "N/A", "NAN", ""] for a in avail_facs4)]
                s4_ft = st.multiselect("TYPE OF HEALTH FACILITY", fac_opts4, key='ft4')
                if s4_ft:
                    if "PUBLIC" in s4_ft and "PRIVATE" in s4_ft: pass
                    elif "PUBLIC" in s4_ft: df_t4 = df_t4[df_t4['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])]
                    elif "PRIVATE" in s4_ft: df_t4 = df_t4[~df_t4['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])]
                
                s4_nm = clean_selection(st.multiselect("NOTIFICATION MONTH", get_options_with_counts(df_t4, 'Notification Month', 'tab4'), key='nm4'))
                if s4_nm: df_t4 = df_t4[df_t4['Notification Month'].isin(s4_nm)]
                
                s4_im = clean_selection(st.multiselect("TREATMENT INITIATION MONTH", get_options_with_counts(df_t4, 'Initiation Month', 'tab4'), key='im4'))
                if s4_im: df_t4 = df_t4[df_t4['Initiation Month'].isin(s4_im)]

            with c2:
                if st.session_state.role in ["ADMIN", "ZONE"]:
                    s4_tu = clean_selection(st.multiselect("CURRENT TB UNIT", get_options_with_counts(df_t4, 'TB Unit', 'tab4'), key='tu4'))
                    if s4_tu: df_t4 = df_t4[df_t4['TB Unit'].isin(s4_tu)]
                
                s4_tc = clean_selection(st.multiselect("TYPE OF CASE", get_options_with_counts(df_t4, 'Type of Case', 'tab4'), key='tc4'))
                if s4_tc: df_t4 = df_t4[df_t4['Type of Case'].isin(s4_tc)]
                
                s4_sd = clean_selection(st.multiselect("SITE OF DISEASE", get_options_with_counts(df_t4, 'Site of Disease', 'tab4'), key='sd4'))
                if s4_sd: df_t4 = df_t4[df_t4['Site of Disease'].isin(s4_sd)]
                
                s4_to = clean_selection(st.multiselect("TREATMENT OUTCOME", get_options_with_counts(df_t4, 'Treatment Outcome Display', 'tab4'), key='to4'))
                if s4_to: df_t4 = df_t4[df_t4['Treatment Outcome Display'].isin(s4_to)]
                
                # 🎯 અહીં મેં બાય ડિફોલ્ટ 'Completed' કાઢી નાખ્યું છે! 
                all_due_opts = get_options_with_counts(df_t4, 'Follow Up Due', 'tab4')
                default_due_opts = [opt for opt in all_due_opts if "Completed" not in opt]
                
                s4_fd_raw = st.multiselect("FOLLOW UP DUE", all_due_opts, default=default_due_opts, key='fd4')
                s4_fd = clean_selection(s4_fd_raw)
                if s4_fd: df_t4 = df_t4[df_t4['Follow Up Due'].isin(s4_fd)]

            with c3:
                s4_phi = clean_selection(st.multiselect("HEALTH FACILITY", get_options_with_counts(df_t4, 'PHI', 'tab4'), key='phi4'))
                if s4_phi: df_t4 = df_t4[df_t4['PHI'].isin(s4_phi)]
                
                s4_ts = clean_selection(st.multiselect("TREATMENT STATUS", get_options_with_counts(df_t4, 'Treatment Status', 'tab4'), key='ts4'))
                if s4_ts: df_t4 = df_t4[df_t4['Treatment Status'].isin(s4_ts)]
                
                s4_om = clean_selection(st.multiselect("TREATMENT OUTCOME MONTH", get_options_with_counts(df_t4, 'Outcome Month', 'tab4'), key='om4'))
                if s4_om: df_t4 = df_t4[df_t4['Outcome Month'].isin(s4_om)]

        # 🎯 8 KPI BOXES (માત્ર Pending માટે)
        st.markdown("##### 🩺 Follow Up Pending Summary")
        kpi_b = len(df_t4[df_t4['Follow Up Due'].str.contains('BASELINE', na=False)])
        kpi_1 = len(df_t4[df_t4['Follow Up Due'].str.contains('1ST MONTH', na=False)])
        kpi_2 = len(df_t4[df_t4['Follow Up Due'].str.contains('2ND MONTH', na=False)])
        kpi_3 = len(df_t4[df_t4['Follow Up Due'].str.contains('3RD MONTH', na=False)])
        kpi_4 = len(df_t4[df_t4['Follow Up Due'].str.contains('4TH MONTH', na=False)])
        kpi_5 = len(df_t4[df_t4['Follow Up Due'].str.contains('5TH MONTH', na=False)])
        kpi_6 = len(df_t4[df_t4['Follow Up Due'].str.contains('6TH MONTH', na=False)])
        kpi_total = len(df_t4[df_t4['Follow Up Due'] != 'Completed'])
        
        kb1, kb2, kb3, kb4 = st.columns(4)
        with kb1: st.markdown(draw_card("Total Pendency", kpi_total, "#C0392B", "🚨"), unsafe_allow_html=True)
        with kb2: st.markdown(draw_card("Baseline", kpi_b, "#8E44AD", "📌"), unsafe_allow_html=True)
        with kb3: st.markdown(draw_card("1st Month", kpi_1, "#2980B9", "📌"), unsafe_allow_html=True)
        with kb4: st.markdown(draw_card("2nd Month", kpi_2, "#2980B9", "📌"), unsafe_allow_html=True)
        
        kb5, kb6, kb7, kb8 = st.columns(4)
        with kb5: st.markdown(draw_card("3rd Month", kpi_3, "#27AE60", "📌"), unsafe_allow_html=True)
        with kb6: st.markdown(draw_card("4th Month", kpi_4, "#27AE60", "📌"), unsafe_allow_html=True)
        with kb7: st.markdown(draw_card("5th Month", kpi_5, "#F39C12", "📌"), unsafe_allow_html=True)
        with kb8: st.markdown(draw_card("6th Month", kpi_6, "#F39C12", "📌"), unsafe_allow_html=True)

        st.markdown("##### 📊 Zone-wise Due Matrix")
        zones = df_t4['ZONE'].unique()
        matrix_data = []
        for z in zones:
            z_df = df_t4[df_t4['ZONE'] == z]
            matrix_data.append({
                'ZONE': z, 'Completed': len(z_df[z_df['Follow Up Due'] == 'Completed']),
                'BASELINE': len(z_df[z_df['Follow Up Due'].str.contains('BASELINE', na=False)]),
                '1ST MONTH': len(z_df[z_df['Follow Up Due'].str.contains('1ST MONTH', na=False)]),
                '2ND MONTH': len(z_df[z_df['Follow Up Due'].str.contains('2ND MONTH', na=False)]),
                '3RD MONTH': len(z_df[z_df['Follow Up Due'].str.contains('3RD MONTH', na=False)]),
                '4TH MONTH': len(z_df[z_df['Follow Up Due'].str.contains('4TH MONTH', na=False)]),
                '5TH MONTH': len(z_df[z_df['Follow Up Due'].str.contains('5TH MONTH', na=False)]),
                '6TH MONTH': len(z_df[z_df['Follow Up Due'].str.contains('6TH MONTH', na=False)]),
                'Grand Total': len(z_df)
            })
        if matrix_data:
            df_matrix = pd.DataFrame(matrix_data)
            df_matrix.loc['Total'] = df_matrix.sum(numeric_only=True)
            df_matrix.at['Total', 'ZONE'] = 'Grand Total'
            st.dataframe(df_matrix, use_container_width=True, hide_index=True)
        
        display_cols = [c for c in df_t4.columns if "Month" not in c and c not in ["Follow Up Due", "Treatment Status", "Treatment Outcome Display"]]
        display_cols.append('Follow Up Due') 
        
        st.markdown("##### 📄 Patient Line List")
        st.dataframe(df_t4[display_cols], use_container_width=True, hide_index=True)
        st.download_button("📥 Download Differentiated Care Report", df_t4[display_cols].to_csv(index=False).encode('utf-8'), "Differentiated_Care.csv", "text/csv", key='dl4', on_click=log_activity, args=(st.session_state.current_user, st.session_state.role, st.session_state.target, "Downloaded Differentiated Care List"))
    else:
        st.warning("⚠️ Differentiated TB Care નો ડેટા હજી અપડેટ થયો નથી.")
