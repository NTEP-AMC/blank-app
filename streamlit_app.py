import streamlit as st
import pandas as pd
import base64
import os
import io
from datetime import datetime, date, timedelta
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
                st.success("✅ Password updated!")

if st.session_state.role == "ADMIN":
    with st.expander("🛡️ Admin Panel: View Passwords & Activity Logs"):
        a_tab1, a_tab2 = st.tabs(["🔑 Manage Users", "📝 Activity Logs"])
        with a_tab1:
            st.dataframe(df_users, use_container_width=True, hide_index=True)
        with a_tab2:
            try:
                df_logs = pd.read_csv(LOG_FILE)
                st.dataframe(df_logs.iloc[::-1], use_container_width=True, hide_index=True)
            except: st.write("No logs available yet.")

st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)

def convert_df_to_excel(df, sheet_name="Data"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]
        header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'top', 'align': 'center', 'fg_color': '#1f618d', 'font_color': 'white', 'border': 1})
        cell_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        for i, col in enumerate(df.columns):
            if len(df) == 0: column_len = len(str(col)) + 2
            else:
                max_val_len = df[col].astype(str).str.len().max()
                column_len = max(max_val_len if pd.notna(max_val_len) else 0, len(str(col))) + 2
            if column_len > 30: column_len = 30 
            worksheet.set_column(i, i, int(column_len), cell_format)
    return output.getvalue()

def parse_dt_safe(s):
    try: return pd.to_datetime(s, errors='coerce', dayfirst=True)
    except: return pd.NaT

try:
    df_master = pd.read_csv("Master_Line_List.csv")
    for col in ['Diagnosis Date', 'Initiation Date', 'Outcome Date']:
        if col in df_master.columns: df_master[col] = df_master[col].apply(parse_dt_safe)
    df_comp = pd.read_csv("Comparison_Matrix.csv")
    df_curr_tb = pd.read_csv("Current_TB_Patients.csv")
    df_time = pd.read_csv("Update_Timestamps.csv")
    
    # 🎯 NEW: Outcome Cohort લોડ કરો
    df_outcome_full = pd.read_csv("Outcome_Cohort.csv")
    for col in ['Diagnosis Date', 'Initiation Date', 'Outcome Date']:
        if col in df_outcome_full.columns: df_outcome_full[col] = df_outcome_full[col].apply(parse_dt_safe)
        
except Exception as e:
    st.error("⚠️ ડેટા ઉપલબ્ધ નથી...")
    df_outcome_full = pd.DataFrame()

def filter_by_role(df, role, target):
    if df.empty: return df
    if role == "TB_UNIT" and 'TB Unit' in df.columns: return df[df['TB Unit'].astype(str).str.strip().str.upper() == target]
    elif role == "ZONE" and 'ZONE' in df.columns: return df[df['ZONE'].astype(str).str.strip().str.upper().isin([target, 'N/A', 'NAN', 'NONE'])]
    return df

df_master = filter_by_role(df_master, st.session_state.role, st.session_state.target)
df_comp = filter_by_role(df_comp, st.session_state.role, st.session_state.target)
df_curr_tb = filter_by_role(df_curr_tb, st.session_state.role, st.session_state.target)
df_outcome_full = filter_by_role(df_outcome_full, st.session_state.role, st.session_state.target)

def draw_card(title, value, color, icon):
    return f"""<div style="background-color: {color}; border-radius: 8px; padding: 15px 5px; margin-bottom: 10px; color: white; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"><div style="font-size: 24px; margin-bottom: 5px;">{icon}</div><div style="font-size: 13px; font-weight: bold; text-transform: uppercase;">{title}</div><div style="font-size: 26px; font-weight: 900; margin-top: 8px;">{value}</div></div>"""

def clean_selection(selected_list): return [item.rsplit(" (", 1)[0] for item in selected_list]

def get_options_with_counts(df, column_name, tab_name="tab1"):
    if df.empty or column_name not in df.columns: return []
    try:
        if tab_name == "tab1" and 'Pending Status' in df.columns:
            df_temp = df.copy()
            df_temp['act_cnt'] = df_temp['Pending Status'].astype(str).apply(lambda x: len([s for s in x.split('+') if s.strip()]))
            counts = df_temp.groupby(column_name)['act_cnt'].sum()
        else:
            counts = df[column_name].value_counts()
        counts = counts[counts > 0].sort_values(ascending=False)
        return [f"{val} ({int(count)})" for val, count in counts.items() if str(val) not in ["nan", "", "None", "N/A"]]
    except: return []

b64_amc, b64_ntep = img_to_b64("images/amc.png"), img_to_b64("images/ntep.jpg")
st.markdown(f"<div style='display: flex; justify-content: space-between; align-items: center;'><img src='data:image/png;base64,{b64_amc}' height='75'><h3 style='margin:0; font-weight:900;'>AMC | NTEP</h3><img src='data:image/jpeg;base64,{b64_ntep}' height='75'></div>", unsafe_allow_html=True)
st.markdown("<div style='background-color:#1f618d; color:white; text-align:center; padding:12px; border-radius:5px; margin:15px 0;'>TB Monitoring Dashboard - Ahmedabad</div>", unsafe_allow_html=True)

if not df_time.empty:
    with st.expander("🕒 Register Last Sync Timestamps (IST)"):
        t_cols = st.columns(5)
        for i, row in df_time.iterrows():
            with t_cols[i % 5]: st.markdown(f"<div style='font-size:13px; color:#333;'><b>{row['Register']}</b><br><span style='color:#E67E22;'>{row['Last Updated']}</span></div>", unsafe_allow_html=True)

# 🎯 NEW TAB 5 ADDED 
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Master Dashboard", "🔄 Daily Comparison", "🏥 Current TB Patients", "🚀 Smart PPT Generator", "📊 Success & Death Rate"])

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
    if not df_disp.empty:
        excel_data1 = convert_df_to_excel(df_disp, "Master_Report")
        st.download_button("📥 Download Formatted Excel", excel_data1, "Master_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key='dl1')

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
    if ind_cols_in_df:
        new_c, res_c, per_c = (df_c[ind_cols_in_df] == "🔴 NEW").sum().sum(), (df_c[ind_cols_in_df] == "🟢 RESOLVED").sum().sum(), (df_c[ind_cols_in_df] == "🟡 PERSISTENT").sum().sum()
    else:
        new_c, res_c, per_c = 0, 0, 0
    
    st.markdown("##### 📈 Daily Action Status")
    cc1, cc2, cc3, cc4 = st.columns(4)
    with cc1: st.markdown(draw_card("TOTAL PENDENCY", new_c + per_c, "#1f618d", "📄"), unsafe_allow_html=True)
    with cc2: st.markdown(draw_card("🔴 NEW", new_c, "#E74C3C", "🚨"), unsafe_allow_html=True)
    with cc3: st.markdown(draw_card("🟡 PERSISTENT", per_c, "#F1C40F", "⏳"), unsafe_allow_html=True)
    with cc4: st.markdown(draw_card("🟢 RESOLVED", res_c, "#27AE60", "✅"), unsafe_allow_html=True)

    st.dataframe(df_c, use_container_width=True, hide_index=True)
    if not df_c.empty:
        excel_data2 = convert_df_to_excel(df_c, "Comparison_Matrix")
        st.download_button("📥 Download Formatted Excel", excel_data2, "Comparison_Matrix.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key='dl2')

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
    if not df_t3.empty:
        excel_data3 = convert_df_to_excel(df_t3[t3_final_cols], "Current_Patients")
        st.download_button("📥 Download Formatted Excel", excel_data3, "Current_Patients.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key='dl3')

with tab4:
    st.markdown("<h3 style='text-align: center; color: #27AE60;'>🚀 Enterprise PPT Report Generator</h3>", unsafe_allow_html=True)
    
    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1:
            all_inds = ["Outcome", "UDST", "Not Put On", "SLPA", "Consent", "ADT", "RBS", "ART", "CPT", "HIV"]
            sel_report = st.selectbox("📌 1. Select Report Type", all_inds)
            st.markdown("<div style='background-color:#e8f4f8; padding:10px; border-radius:5px;'><b>📅 Period 1 (Current)</b></div>", unsafe_allow_html=True)
            p1_name = st.text_input("Name for Period 1", "Q1 - 2025")
            p1_diag = st.date_input("Diagnosis Date (P1)", value=[])
            p1_init = st.date_input("Treatment Start Date (P1)", value=[])
            p1_out = st.date_input("Outcome Date (P1)", value=[])
        with c2:
            st.write("")
            st.write("")
            compare_mode = st.checkbox("📊 Enable Comparison (Period 2)")
            if compare_mode:
                st.markdown("<div style='background-color:#fef5e7; padding:10px; border-radius:5px;'><b>📅 Period 2 (Previous)</b></div>", unsafe_allow_html=True)
                p2_name = st.text_input("Name for Period 2", "Q2 - 2025")
                p2_diag = st.date_input("Diagnosis Date (P2)", value=[])
                p2_init = st.date_input("Treatment Start Date (P2)", value=[])
                p2_out = st.date_input("Outcome Date (P2)", value=[])
            else:
                p2_name = "None"
                p2_diag, p2_init, p2_out = [], [], []
        with c3:
            st.markdown("<div style='background-color:#e9ecef; padding:10px; border-radius:5px;'><b>🎨 3. Presentation Rules</b></div>", unsafe_allow_html=True)
            st.write("")
            color_rule = st.radio("Color Scale Rules:", ["High is Bad (Red) 🔴", "High is Good (Green) 🟢"])
            high_is_bad = True if "Bad" in color_rule else False
            if compare_mode: color_target = st.radio("Apply Color Formatting On:", [p1_name, p2_name, "Grand Total"])
            else: color_target = p1_name

    def apply_date_filters(df, diag, init, out):
        mask = pd.Series(True, index=df.index)
        if len(diag) == 2: mask &= df['Diagnosis Date'].dt.date.between(diag[0], diag[1])
        if len(init) == 2: mask &= df['Initiation Date'].dt.date.between(init[0], init[1])
        if len(out) == 2: mask &= df['Outcome Date'].dt.date.between(out[0], out[1])
        return mask

    def generate_smart_ppt(df, report_name):
        try:
            from pptx import Presentation
            from pptx.util import Inches, Pt
            from pptx.dml.color import RGBColor
        except ImportError: return None, "⚠️ PPTX લાઈબ્રેરી ઇન્સ્ટોલ નથી!"

        prs = Presentation()
        m1 = apply_date_filters(df, p1_diag, p1_init, p1_out)
        m1 &= df['Pending Status'].astype(str).str.contains(report_name, na=False)
        df_p1 = df[m1].copy()

        df_p2 = pd.DataFrame()
        if compare_mode:
            m2 = apply_date_filters(df, p2_diag, p2_init, p2_out)
            m2 &= df['Pending Status'].astype(str).str.contains(report_name, na=False)
            df_p2 = df[m2].copy()

        def get_bg_color(val, max_val):
            if max_val == 0 or pd.isna(val) or val == 0: return RGBColor(255, 255, 255)
            ratio = val / max_val
            if not high_is_bad: ratio = 1 - ratio 
            if ratio > 0.66: return RGBColor(241, 148, 138)
            elif ratio > 0.33: return RGBColor(249, 231, 159)
            else: return RGBColor(171, 235, 198)

        def add_slide_table(title_text, curr_df, prev_df, entity_col_name):
            slide = prs.slides.add_slide(prs.slide_layouts[5])
            if os.path.exists("images/amc.png"): slide.shapes.add_picture("images/amc.png", Inches(0.3), Inches(0.2), width=Inches(0.8))
            if os.path.exists("images/ntep.jpg"): slide.shapes.add_picture("images/ntep.jpg", Inches(8.9), Inches(0.2), width=Inches(0.8))
            title = slide.shapes.title
            title.text = title_text
            title.text_frame.paragraphs[0].font.size = Pt(28)
            title.text_frame.paragraphs[0].font.bold = True
            if curr_df.empty and prev_df.empty:
                tx = slide.shapes.add_textbox(Inches(2), Inches(3), Inches(5), Inches(1))
                tx.text_frame.text = "આ તારીખો માટે કોઈ દર્દી પેન્ડિંગ નથી."
                return
            if compare_mode:
                final_df = pd.merge(curr_df, prev_df, on=entity_col_name, how='outer').fillna(0)
                final_df['Grand Total'] = final_df[p1_name] + final_df[p2_name]
                final_df = final_df.sort_values(by='Grand Total', ascending=False)
                col_names = [entity_col_name, p1_name, p2_name, 'Grand Total']
            else:
                final_df = curr_df.sort_values(by=p1_name, ascending=False)
                col_names = [entity_col_name, p1_name]

            rows = len(final_df) + 1
            cols = len(col_names)
            table_shape = slide.shapes.add_table(rows, cols, Inches(0.8), Inches(1.5), Inches(8.4), Inches(0.4))
            table = table_shape.table
            if cols == 2:
                table.columns[0].width = Inches(5.4); table.columns[1].width = Inches(3.0)
            elif cols == 4:
                table.columns[0].width = Inches(4.0); table.columns[1].width = Inches(1.5); table.columns[2].width = Inches(1.5); table.columns[3].width = Inches(1.4)
            for i, c_name in enumerate(col_names):
                cell = table.cell(0, i)
                cell.text = c_name
                cell.fill.solid(); cell.fill.fore_color.rgb = RGBColor(31, 97, 141)
                cell.text_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)
                cell.text_frame.paragraphs[0].font.bold = True
            target_idx = col_names.index(color_target)
            max_value = final_df.iloc[:, target_idx].max() if not final_df.empty else 0
            for i, (_, row) in enumerate(final_df.iterrows()):
                name_val = str(row[entity_col_name])
                table.cell(i+1, 0).text = name_val
                table.cell(i+1, 1).text = str(int(row[p1_name]))
                if cols == 4:
                    table.cell(i+1, 2).text = str(int(row[p2_name]))
                    table.cell(i+1, 3).text = str(int(row['Grand Total']))
                if "PRIVATE FACILITIES" in name_val:
                    for j in range(cols):
                        c = table.cell(i+1, j)
                        c.fill.solid(); c.fill.fore_color.rgb = RGBColor(235, 237, 239)
                        c.text_frame.paragraphs[0].font.bold = True
                else:
                    c_target = table.cell(i+1, target_idx)
                    val_target = row.iloc[target_idx]
                    c_target.fill.solid()
                    c_target.fill.fore_color.rgb = get_bg_color(val_target, max_value)

        def get_summary(temp_df, group_col, val_name):
            if temp_df.empty: return pd.DataFrame(columns=[group_col, val_name])
            if group_col == 'PHI':
                pub_mask = temp_df['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])
                pub_sum = temp_df[pub_mask].groupby('PHI').size().reset_index(name=val_name)
                priv_count = len(temp_df[~pub_mask])
                if priv_count > 0:
                    priv_row = pd.DataFrame({'PHI': ['PRIVATE FACILITIES (TOTAL)'], val_name: [priv_count]})
                    return pd.concat([pub_sum, priv_row], ignore_index=True)
                return pub_sum
            else: return temp_df.groupby(group_col).size().reset_index(name=val_name)

        if st.session_state.role == "ZONE":
            tu_curr = get_summary(df_p1, 'TB Unit', p1_name)
            tu_prev = get_summary(df_p2, 'TB Unit', p2_name) if compare_mode else pd.DataFrame()
            add_slide_table(f"{st.session_state.target} Zone - {sel_report} Pending (TU Wise)", tu_curr, tu_prev, 'TB Unit')
            tus = sorted(pd.concat([df_p1['TB Unit'], df_p2['TB Unit'] if compare_mode else pd.Series()]).dropna().unique())
            for tu in tus:
                phi_curr = get_summary(df_p1[df_p1['TB Unit'] == tu], 'PHI', p1_name)
                phi_prev = get_summary(df_p2[df_p2['TB Unit'] == tu], 'PHI', p2_name) if compare_mode else pd.DataFrame()
                add_slide_table(f"TU: {tu} - {sel_report} Pending", phi_curr, phi_prev, 'PHI')

        elif st.session_state.role == "ADMIN":
            z_curr = get_summary(df_p1, 'ZONE', p1_name)
            z_prev = get_summary(df_p2, 'ZONE', p2_name) if compare_mode else pd.DataFrame()
            add_slide_table(f"All Zones - {sel_report} Pending", z_curr, z_prev, 'ZONE')
            zones = sorted(pd.concat([df_p1['ZONE'], df_p2['ZONE'] if compare_mode else pd.Series()]).dropna().unique())
            for z in zones:
                phi_curr = get_summary(df_p1[df_p1['ZONE'] == z], 'PHI', p1_name)
                phi_prev = get_summary(df_p2[df_p2['ZONE'] == z], 'PHI', p2_name) if compare_mode else pd.DataFrame()
                add_slide_table(f"Zone: {z} - {sel_report} Pending", phi_curr, phi_prev, 'PHI')
        else:
            phi_curr = get_summary(df_p1, 'PHI', p1_name)
            phi_prev = get_summary(df_p2, 'PHI', p2_name) if compare_mode else pd.DataFrame()
            add_slide_table(f"{st.session_state.target} - {sel_report} Pending", phi_curr, phi_prev, 'PHI')

        out_io = io.BytesIO()
        prs.save(out_io)
        return out_io.getvalue(), "Success"

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("✨ Generate Custom PPT ✨", use_container_width=True):
        with st.spinner("Generating beautiful Enterprise PPT slides... Please wait..."):
            ppt_bytes, status = generate_smart_ppt(df_master, sel_report)
            if ppt_bytes:
                st.success("✅ PPT 100% તૈયાર છે! નીચેના બટન પર ક્લિક કરીને ડાઉનલોડ કરો.")
                st.download_button(label=f"📥 Download {sel_report}_Analysis.pptx", data=ppt_bytes, file_name=f"{sel_report}_Analysis.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")
            else: st.error(status)

# ==========================================
# 🟢 TAB 5: SUCCESS & DEATH RATE (NEW)
# ==========================================
with tab5:
    st.markdown("<h3 style='color: #1f618d;'>📊 Success Rate & Death Rate (Epidemiological KPIs)</h3>", unsafe_allow_html=True)
    
    if df_outcome_full.empty:
        st.warning("⚠️ Outcome નો ડેટા હજી અપડેટ થયો નથી. કૃપા કરીને Colab માં નવો માસ્ટર કોડ રન કરો.")
    else:
        df_out = df_outcome_full.copy()

        with st.expander("🔽 Filters & Parameters", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                s5_z = clean_selection(st.multiselect("Zone", get_options_with_counts(df_out, 'ZONE', 'tab5'), key='z5'))
                if s5_z: df_out = df_out[df_out['ZONE'].isin(s5_z)]
                
                s5_tu = clean_selection(st.multiselect("TB Unit", get_options_with_counts(df_out, 'TB Unit', 'tab5'), key='tu5'))
                if s5_tu: df_out = df_out[df_out['TB Unit'].isin(s5_tu)]
            
            with c2:
                s5_phi = clean_selection(st.multiselect("PHI", get_options_with_counts(df_out, 'PHI', 'tab5'), key='phi5'))
                if s5_phi: df_out = df_out[df_out['PHI'].isin(s5_phi)]
                
                st.markdown("<div style='margin-top: 25px;'>", unsafe_allow_html=True)
                exclude_regimen = st.checkbox("✅ Exclude 'TREATMENT REGIMEN CHANGED'", value=True, help="કુલ દર્દીઓમાંથી આ આંકડો બાદ થશે")
                st.markdown("</div>", unsafe_allow_html=True)

            with c3:
                diag_dt5 = st.date_input("Diagnosis Date", value=[], key="d1_5")
                init_dt5 = st.date_input("Initiation Date", value=[], key="d2_5")
                out_dt5 = st.date_input("Outcome Date", value=[], key="d3_5")
                
        # Apply Date Filters
        if len(diag_dt5) == 2: df_out = df_out[df_out['Diagnosis Date'].notna() & df_out['Diagnosis Date'].dt.date.between(diag_dt5[0], diag_dt5[1])]
        if len(init_dt5) == 2: df_out = df_out[df_out['Initiation Date'].notna() & df_out['Initiation Date'].dt.date.between(init_dt5[0], init_dt5[1])]
        if len(out_dt5) == 2: df_out = df_out[df_out['Outcome Date'].notna() & df_out['Outcome Date'].dt.date.between(out_dt5[0], out_dt5[1])]

        # 1. માત્ર Outcome આપેલા દર્દીઓ જ લેવાના
        df_out = df_out[df_out['Treatment Outcome'].notna() & (df_out['Treatment Outcome'] != '') & (df_out['Treatment Outcome'] != 'N/A')]
        
        # 2. Exclude REGIMEN CHANGED
        if exclude_regimen:
            df_out = df_out[~df_out['Treatment Outcome'].str.contains('REGIMEN CHANGED', na=False)]

        # 3. Identify Success & Death
        df_out['Is_Success'] = df_out['Treatment Outcome'].str.contains('COMPLETE|CURED', na=False)
        df_out['Is_Dead'] = df_out['Treatment Outcome'].str.contains('DIED|DEATH', na=False)

        total_patients = len(df_out)
        total_success = df_out['Is_Success'].sum()
        total_death = df_out['Is_Dead'].sum()
        
        overall_success_rate = round((total_success / total_patients * 100), 2) if total_patients > 0 else 0
        overall_death_rate = round((total_death / total_patients * 100), 2) if total_patients > 0 else 0

        # KPI Boxes
        kb1, kb2 = st.columns(2)
        with kb1: st.markdown(draw_card("Overall Success Rate", f"{overall_success_rate}%", "#27AE60", "🌟"), unsafe_allow_html=True)
        with kb2: st.markdown(draw_card("Overall Death Rate", f"{overall_death_rate}%", "#C0392B", "⚠️"), unsafe_allow_html=True)

        def get_rate_table(df_group, group_col):
            if df_group.empty: return pd.DataFrame()
            grp = df_group.groupby(group_col)
            summary = pd.DataFrame({
                'Total Outcome Given': grp.size(),
                'Successful Outcomes': grp['Is_Success'].sum(),
                'Deaths': grp['Is_Dead'].sum()
            }).reset_index()
            
            summary['Success Rate (%)'] = (summary['Successful Outcomes'] / summary['Total Outcome Given'] * 100).round(2).astype(str) + '%'
            summary['Death Rate (%)'] = (summary['Deaths'] / summary['Total Outcome Given'] * 100).round(2).astype(str) + '%'
            
            # Select required columns
            return summary[[group_col, 'Total Outcome Given', 'Success Rate (%)', 'Death Rate (%)']].sort_values(by='Total Outcome Given', ascending=False)

        st.markdown("<hr>", unsafe_allow_html=True)
        
        # 🎯 ડાયનેમિક ટેબલ્સ (Zone/TU/PHI)
        if st.session_state.role == "ZONE" or len(s5_z) > 0:
            st.markdown("##### 📍 TU Wise Rates")
            tu_table = get_rate_table(df_out, 'TB Unit')
            st.dataframe(tu_table, use_container_width=True, hide_index=True)
            
            st.markdown("##### 🏥 PHI Wise Rates")
            phi_table = get_rate_table(df_out, 'PHI')
            st.dataframe(phi_table, use_container_width=True, hide_index=True)
        elif st.session_state.role == "ADMIN":
            st.markdown("##### 🗺️ Zone Wise Rates")
            zone_table = get_rate_table(df_out, 'ZONE')
            st.dataframe(zone_table, use_container_width=True, hide_index=True)
        else:
            st.markdown("##### 🏥 PHI Wise Rates")
            phi_table = get_rate_table(df_out, 'PHI')
            st.dataframe(phi_table, use_container_width=True, hide_index=True)

        if not df_out.empty:
            excel_data5 = convert_df_to_excel(df_out, "Outcome_Cohort")
            st.download_button("📥 Download Raw Outcome Cohort", excel_data5, "Outcome_Cohort.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key='dl5')
