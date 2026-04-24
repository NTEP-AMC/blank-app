import streamlit as st
import pandas as pd
import base64
import os
import io
import re
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

# 🎯 DRIVE DATA FETCH 
@st.cache_data(ttl=3600)
def load_all_data():
    try:
        m = pd.read_csv("Master_Line_List.csv", dtype={'Episode ID': str})
        for c in ['Diagnosis Date', 'Initiation Date', 'Outcome Date']:
            if c in m.columns: m[c] = pd.to_datetime(m[c], errors='coerce') 
            
        c_mat = pd.read_csv("Comparison_Matrix.csv", dtype={'Episode ID': str})
        if not c_mat.empty and not m.empty:
            dates_df = m[['Episode ID', 'Diagnosis Date', 'Initiation Date', 'Outcome Date']].drop_duplicates('Episode ID')
            c_mat = c_mat.merge(dates_df, on='Episode ID', how='left')

        curr = pd.read_csv("Current_TB_Patients.csv", dtype={'Episode ID': str})
        t_df = pd.read_csv("Update_Timestamps.csv")
            
        return m, c_mat, curr, t_df
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# 🎯 LIVE GOOGLE SHEET FETCH FOR DIFF CARE
@st.cache_data(ttl=300) 
def get_live_dc():
    try:
        def fetch_sheet(url):
            df = pd.read_csv(url, header=None, low_memory=False, dtype=str)
            header_row = 0
            for i in range(min(5, len(df))):
                row_str = " ".join(df.iloc[i].fillna("").astype(str).str.upper())
                if "EPISODE" in row_str and "NAME" in row_str:
                    header_row = i; break
            header_vals = df.iloc[header_row].fillna("").astype(str).str.upper()
            df = df.iloc[header_row+1:].reset_index(drop=True)
            
            def cx_col(col_let):
                num = 0
                for c in col_let.upper(): num = num * 26 + (ord(c) - ord('A') + 1)
                return num - 1

            tu_idx, phi_idx, id_idx, name_idx, zone_idx = cx_col('A'), cx_col('C'), cx_col('G'), cx_col('H'), cx_col('AR')
            diag_idx, init_idx, out_idx = cx_col('CJ'), cx_col('CK'), cx_col('CL')
            hf_idx, case_idx, site_idx, out_col_idx = cx_col('B'), cx_col('Z'), cx_col('AA'), cx_col('AD')
            ci_idx = cx_col('CI') 
            cx_base, cy_1m, cz_2m, da_3m, db_4m, dc_5m, dd_6m = cx_col('CX'), cx_col('CY'), cx_col('CZ'), cx_col('DA'), cx_col('DB'), cx_col('DC'), cx_col('DD')

            for i, val in enumerate(header_vals):
                val_c = val.strip()
                if "EPISODE" in val_c and "ID" in val_c: id_idx = i
                elif "PATIENT" in val_c and "NAME" in val_c: name_idx = i
                elif "DUE" in val_c and "STATUS" in val_c: ci_idx = i
                elif "DIAGNOSIS" in val_c and "DATE" in val_c: diag_idx = i
                elif "INITIATION" in val_c and "DATE" in val_c: init_idx = i
                elif "OUTCOME" in val_c and "DATE" in val_c: out_idx = i
                elif val_c == "ZONE": zone_idx = i
                elif "ELIGIBILITY" in val_c and "BASE" in val_c: cx_base = i
                elif "ELIGIBILITY" in val_c and "1" in val_c: cy_1m = i
                elif "ELIGIBILITY" in val_c and "2" in val_c: cz_2m = i
                elif "ELIGIBILITY" in val_c and "3" in val_c: da_3m = i
                elif "ELIGIBILITY" in val_c and "4" in val_c: db_4m = i
                elif "ELIGIBILITY" in val_c and "5" in val_c: dc_5m = i
                elif "ELIGIBILITY" in val_c and "6" in val_c: dd_6m = i

            diff_data = []
            for _, row in df.iterrows():
                def get_v(idx): return str(row.iloc[idx]).strip().upper() if idx < len(row) else ""
                elig_base, elig_1m, elig_2m, elig_3m, elig_4m, elig_5m, elig_6m = get_v(cx_base), get_v(cy_1m), get_v(cz_2m), get_v(da_3m), get_v(db_4m), get_v(dc_5m), get_v(dd_6m)
                is_elig = any("ELIG" in v and "NOT" not in v for v in [elig_base, elig_1m, elig_2m, elig_3m, elig_4m, elig_5m, elig_6m])
                if is_elig:
                    tu = get_v(tu_idx).replace("-", "")
                    if "INDIA" in tu: tu = "INDIA COLONY"
                    elif "NAVA" in tu and "VADAJ" in tu: tu = "NAVA VADAJ"
                    elif "JUNA" in tu and "VADAJ" in tu: tu = "JUNA VADAJ"
                    elif "NOB" in tu: tu = "NOBLENAGAR"
                    elif "BEHRAM" in tu: tu = "BEHRAMPURA"
                    elif "SAIJ" in tu: tu = "SAIJPUR"
                    elif "DANI" in tu: tu = "DANILIMDA"
                    elif "AMRAI" in tu: tu = "AMRAIWADI"
                    elif "BHAI" in tu: tu = "BHAIPURA"
                    elif "GHAT" in tu: tu = "GHATLODIA"
                    elif "CHAND" in tu: tu = "CHANDKHEDA"
                    elif "VEJAL" in tu: tu = "VEJALPUR"
                    elif "ISAN" in tu: tu = "ISANPUR"
                    elif "ASAR" in tu: tu = "ASARVA"
                    elif "BAPU" in tu: tu = "BAPUNAGAR"
                    elif "VIRAT" in tu: tu = "VIRATNAGAR"
                    elif "RAKH" in tu: tu = "RAKHIAL"
                    elif "JAMAL" in tu: tu = "JAMALPUR"
                    elif "VASNA" in tu: tu = "VASNA"
                    elif "VATVA" in tu: tu = "VATVA"
                    elif "JODH" in tu: tu = "JODHPUR"
                    elif "SHAH" in tu: tu = "SHAHPUR"
                    elif "RANIP" in tu: tu = "RANIP"
                    
                    zone = get_v(zone_idx)
                    if zone in ["", "NAN", "NONE", "NULL", "N/A"]: zone = 'MAPPING NOT DONE'
                    
                    diff_data.append({
                        'ZONE': zone, 'TB Unit': tu, 'PHI': get_v(phi_idx), 'Episode ID': get_v(id_idx), 'Patient Name': get_v(name_idx),
                        'Due_Status': get_v(ci_idx), 'Diagnosis Date': get_v(diag_idx), 'Initiation Date': get_v(init_idx), 'Outcome Date': get_v(out_idx),
                        'Facility_Type': get_v(hf_idx), 'Type_of_Case': get_v(case_idx), 
                        'Site_of_TBDisease': get_v(site_idx), 'Treatment_Outcome': get_v(out_col_idx),
                        'Elig_BASELINE': elig_base, 'Elig_1ST_MONTH': elig_1m, 'Elig_2ND_MONTH': elig_2m,
                        'Elig_3RD_MONTH': elig_3m, 'Elig_4TH_MONTH': elig_4m, 'Elig_5TH_MONTH': elig_5m, 'Elig_6TH_MONTH': elig_6m
                    })
            return pd.DataFrame(diff_data)

        url_new = "https://docs.google.com/spreadsheets/d/1hkJBnJOuxcVu233f6e2_0cOE-BM7bdDOyHuzrlGogMU/export?format=csv&gid=1152778583"
        url_old = "https://docs.google.com/spreadsheets/d/1zdf96eisZHzdk5ECFSI7eeOtNQoOXk3QRUUROtIZQmc/export?format=csv&gid=1152778583"
        return fetch_sheet(url_new), fetch_sheet(url_old)
    except: return pd.DataFrame(), pd.DataFrame()

df_master_raw, df_comp_raw, df_curr_tb_raw, df_time = load_all_data()
df_dc_new_raw, df_dc_old_raw = get_live_dc()

def filter_by_role(df, role, target):
    if df.empty: return df
    target_up = str(target).upper().strip()
    if role == "TB_UNIT" and 'TB Unit' in df.columns:
        return df[df['TB Unit'].astype(str).str.upper().str.contains(target_up, na=False)]
    elif role == "ZONE" and 'ZONE' in df.columns:
        return df[df['ZONE'].astype(str).str.upper().str.contains(target_up, na=False) | df['ZONE'].isin(['N/A', 'NAN', 'MAPPING NOT DONE'])]
    return df

df_master = filter_by_role(df_master_raw.copy(), st.session_state.role, st.session_state.target)
df_comp = filter_by_role(df_comp_raw.copy(), st.session_state.role, st.session_state.target) 
df_curr_tb = filter_by_role(df_curr_tb_raw.copy(), st.session_state.role, st.session_state.target)
df_dc_new = filter_by_role(df_dc_new_raw.copy(), st.session_state.role, st.session_state.target)
df_dc_old = filter_by_role(df_dc_old_raw.copy(), st.session_state.role, st.session_state.target)

def draw_card(title, value, color, icon):
    return f"""<div style="background-color: {color}; border-radius: 8px; padding: 15px 5px; margin-bottom: 10px; color: white; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"><div style="font-size: 24px; margin-bottom: 5px;">{icon}</div><div style="font-size: 13px; font-weight: bold; text-transform: uppercase;">{title}</div><div style="font-size: 26px; font-weight: 900; margin-top: 8px;">{value}</div></div>"""

def clean_selection(selected_list): return [item.rsplit(" (", 1)[0] for item in selected_list]

def get_options_with_counts(df, column_name, tab_name="tab1"):
    if df.empty or column_name not in df.columns: return []
    try:
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

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Master Dashboard", "🔄 Daily Comparison", "🏥 Current TB Patients", "🚀 Smart PPT", "🏥 Diff. Care"])

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
            # 🎯 SMART FILTER CASCADING
            s_tu = clean_selection(st.multiselect("TB Unit", get_options_with_counts(df_disp, 'TB Unit', 'tab1'), key='tu1'))
            if s_tu: df_disp = df_disp[df_disp['TB Unit'].isin(s_tu)]
        with c2:
            if 'Facility Type' in df_disp.columns:
                available_facs = df_disp['Facility Type'].astype(str).str.upper().unique()
                fac_opts = [f for f in ["PUBLIC", "PRIVATE"] if any(a in ["PUBLIC", "PHI"] if f=="PUBLIC" else a not in ["PUBLIC", "PHI", "N/A", "NAN", ""] for a in available_facs)]
                s_ft_raw = st.multiselect("Facility Category", fac_opts, key='fc1')
                if s_ft_raw:
                    if "PUBLIC" in s_ft_raw and "PRIVATE" in s_ft_raw: pass
                    elif "PUBLIC" in s_ft_raw: df_disp = df_disp[df_disp['Facility Type'].astype(str).str.upper().isin(['PUBLIC', 'PHI'])]
                    elif "PRIVATE" in s_ft_raw: df_disp = df_disp[~df_disp['Facility Type'].astype(str).str.upper().isin(['PUBLIC', 'PHI'])]
            # 🎯 SMART FILTER CASCADING
            s_phi = clean_selection(st.multiselect("Filter PHI", get_options_with_counts(df_disp, 'PHI', 'tab1'), key='phi1'))
            if s_phi: df_disp = df_disp[df_disp['PHI'].isin(s_phi)]
            inds = ["Outcome", "UDST", "Not Put On", "SLPA", "Consent", "ADT", "RBS", "ART", "CPT", "HIV"]
            f_rep = st.multiselect("Report Type", inds, key='rep1')
        with c3:
            diag_dt = st.date_input("Diagnosis Date Range", value=[], key="d1")
            init_dt = st.date_input("Initiation Date Range", value=[], key="d2")
            out_dt = st.date_input("Outcome Date Range", value=[], key="d3")
        if len(diag_dt) == 2: df_disp = df_disp[pd.to_datetime(df_disp.get('Diagnosis Date'), errors='coerce').dt.date.between(diag_dt[0], diag_dt[1])]
        if len(init_dt) == 2: df_disp = df_disp[pd.to_datetime(df_disp.get('Initiation Date'), errors='coerce').dt.date.between(init_dt[0], init_dt[1])]
        if len(out_dt) == 2: df_disp = df_disp[pd.to_datetime(df_disp.get('Outcome Date'), errors='coerce').dt.date.between(out_dt[0], out_dt[1])]
        if f_rep and 'Pending Status' in df_disp.columns: df_disp = df_disp[df_disp['Pending Status'].str.contains("|".join(f_rep), na=False)]

    if 'Pending Status' in df_disp.columns:
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
        st.download_button("📥 Download Master Excel", convert_df_to_excel(df_disp, "Master_Report"), "Master_Report.xlsx", key='dl1')

# ==========================================
# 🟢 TAB 2: DAILY COMPARISON
# ==========================================
with tab2:
    st.markdown("#### 🔄 Comparison Matrix")
    with st.expander("🔽 Filters & Dates", expanded=True):
        c1, c2, c3 = st.columns(3)
        df_c = df_comp.copy()
        with c1: 
            if st.session_state.role == "ADMIN":
                s2_z = clean_selection(st.multiselect("Filter Zone", get_options_with_counts(df_c, 'ZONE', 'tab2'), key='z2'))
                if s2_z: df_c = df_c[df_c['ZONE'].isin(s2_z)]
            # 🎯 SMART FILTER CASCADING
            s2_tu = clean_selection(st.multiselect("Filter TB Unit", get_options_with_counts(df_c, 'TB Unit', 'tab2'), key='tu2'))
            if s2_tu: df_c = df_c[df_c['TB Unit'].isin(s2_tu)]
        with c2: 
            if 'Facility Type' in df_c.columns:
                available_facs2 = df_c['Facility Type'].astype(str).str.upper().unique()
                fac_opts2 = [f for f in ["PUBLIC", "PRIVATE"] if any(a in ["PUBLIC", "PHI"] if f=="PUBLIC" else a not in ["PUBLIC", "PHI", "N/A", "NAN", ""] for a in available_facs2)]
                s2_ft_raw = st.multiselect("Facility Category", fac_opts2, key='fc2')
                if s2_ft_raw:
                    if "PUBLIC" in s2_ft_raw and "PRIVATE" in s2_ft_raw: pass
                    elif "PUBLIC" in s2_ft_raw: df_c = df_c[df_c['Facility Type'].astype(str).str.upper().isin(['PUBLIC', 'PHI'])]
                    elif "PRIVATE" in s2_ft_raw: df_c = df_c[~df_c['Facility Type'].astype(str).str.upper().isin(['PUBLIC', 'PHI'])]
            # 🎯 SMART FILTER CASCADING
            s2_phi = clean_selection(st.multiselect("Filter PHI", get_options_with_counts(df_c, 'PHI', 'tab2'), key='phi2'))
            if s2_phi: df_c = df_c[df_c['PHI'].isin(s2_phi)]
        with c3: 
            ignore_cols = ['ZONE', 'TB Unit', 'PHI', 'Episode ID', 'Patient Name', 'Facility Type', 'Diagnosis Date', 'Initiation Date', 'Outcome Date']
            s2_ind = st.multiselect("Filter by Report Type", [c for c in df_c.columns if c not in ignore_cols], key='ind2')
            s2_stat = st.multiselect("Filter by Status", ["🔴 NEW", "🟢 RESOLVED", "🟡 PERSISTENT"], key='stat2')
        
        cd1, cd2, cd3 = st.columns(3)
        with cd1: diag_dt2 = st.date_input("Diagnosis Date Range", value=[], key="d1_2")
        with cd2: init_dt2 = st.date_input("Initiation Date Range", value=[], key="d2_2")
        with cd3: out_dt2 = st.date_input("Outcome Date Range", value=[], key="d3_2")

        if len(diag_dt2) == 2: df_c = df_c[pd.to_datetime(df_c.get('Diagnosis Date'), errors='coerce').dt.date.between(diag_dt2[0], diag_dt2[1])]
        if len(init_dt2) == 2: df_c = df_c[pd.to_datetime(df_c.get('Initiation Date'), errors='coerce').dt.date.between(init_dt2[0], init_dt2[1])]
        if len(out_dt2) == 2: df_c = df_c[pd.to_datetime(df_c.get('Outcome Date'), errors='coerce').dt.date.between(out_dt2[0], out_dt2[1])]

    if s2_ind or s2_stat:
        mask = pd.Series(False, index=df_c.index)
        for ind in (s2_ind if s2_ind else [c for c in df_c.columns if c not in ignore_cols]):
            if ind in df_c.columns: mask = mask | df_c[ind].isin(s2_stat if s2_stat else ["🔴 NEW", "🟢 RESOLVED", "🟡 PERSISTENT"])
        df_c = df_c[mask]
    
    ind_cols_in_df = [c for c in df_c.columns if c not in ignore_cols]
    new_c = (df_c[ind_cols_in_df] == "🔴 NEW").sum().sum() if ind_cols_in_df else 0
    res_c = (df_c[ind_cols_in_df] == "🟢 RESOLVED").sum().sum() if ind_cols_in_df else 0
    per_c = (df_c[ind_cols_in_df] == "🟡 PERSISTENT").sum().sum() if ind_cols_in_df else 0
    
    st.markdown("##### 📈 Daily Action Status")
    cc1, cc2, cc3, cc4 = st.columns(4)
    with cc1: st.markdown(draw_card("TOTAL PENDENCY", new_c + per_c, "#1f618d", "📄"), unsafe_allow_html=True)
    with cc2: st.markdown(draw_card("🔴 NEW", new_c, "#E74C3C", "🚨"), unsafe_allow_html=True)
    with cc3: st.markdown(draw_card("🟡 PERSISTENT", per_c, "#F1C40F", "⏳"), unsafe_allow_html=True)
    with cc4: st.markdown(draw_card("🟢 RESOLVED", res_c, "#27AE60", "✅"), unsafe_allow_html=True)
    
    st.dataframe(df_c, use_container_width=True, hide_index=True)
    if not df_c.empty:
        st.download_button("📥 Download Comparison Matrix", convert_df_to_excel(df_c, "Comparison_Matrix"), "Comparison.xlsx", key='dl2')

# ==========================================
# 🟢 TAB 3: CURRENT PATIENTS
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
            # 🎯 SMART FILTER CASCADING
            s3_tu = clean_selection(st.multiselect("Filter TB Unit", get_options_with_counts(df_t3, 'TB Unit', 'tab3'), key='tu3'))
            if s3_tu: df_t3 = df_t3[df_t3['TB Unit'].isin(s3_tu)]
        with c2:
            if 'Facility Type' in df_t3.columns:
                available_facs3 = df_t3['Facility Type'].astype(str).str.upper().unique()
                fac_opts3 = [f for f in ["PUBLIC", "PRIVATE"] if any(a in ["PUBLIC", "PHI"] if f=="PUBLIC" else a not in ["PUBLIC", "PHI", "N/A", "NAN", ""] for a in available_facs3)]
                s3_ft_raw = st.multiselect("Facility Category", fac_opts3, key='fc3')
                if s3_ft_raw:
                    if "PUBLIC" in s3_ft_raw and "PRIVATE" in s3_ft_raw: pass
                    elif "PUBLIC" in s3_ft_raw: df_t3 = df_t3[df_t3['Facility Type'].astype(str).str.upper().isin(['PUBLIC', 'PHI'])]
                    elif "PRIVATE" in s3_ft_raw: df_t3 = df_t3[~df_t3['Facility Type'].astype(str).str.upper().isin(['PUBLIC', 'PHI'])]
            # 🎯 SMART FILTER CASCADING
            s3_phi = clean_selection(st.multiselect("Filter PHI", get_options_with_counts(df_t3, 'PHI', 'tab3'), key='phi3'))
            if s3_phi: df_t3 = df_t3[df_t3['PHI'].isin(s3_phi)]
    st.markdown("##### 📈 Patient Overview")
    st.markdown(draw_card("Total Active Patients", len(df_t3), "#16A085", "🏥"), unsafe_allow_html=True)
    st.dataframe(df_t3, use_container_width=True, hide_index=True)
    if not df_t3.empty:
        st.download_button("📥 Download Excel", convert_df_to_excel(df_t3, "Current_Patients"), "Current_Patients.xlsx", key='dl3')

# ==========================================
# 🟢 TAB 4: PPT GENERATOR
# ==========================================
with tab4:
    st.info("Smart PPT functionality is available. Configure parameters to generate.")

# ==========================================
# 🟢 TAB 5: DIFFERENTIATED CARE (THE BIG UPDATE)
# ==========================================
with tab5:
    st.markdown("<h3 style='color: #1f618d;'>🏥 Differentiated Care Tracking System</h3>", unsafe_allow_html=True)
    if df_dc_new.empty:
        st.warning("⚠️ ડેટા મળ્યો નથી.")
    else:
        with st.expander("🔽 Filters & Dates", expanded=False):
            df_dc = df_dc_new.copy()
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.session_state.role == "ADMIN":
                    s6_z = st.multiselect("Zone", sorted([x for x in df_dc['ZONE'].unique() if pd.notna(x) and x!=""]), key='z6')
                    if s6_z: df_dc = df_dc[df_dc['ZONE'].isin(s6_z)]
                
                # 🎯 SMART FILTER CASCADING
                tu_opts = sorted([x for x in df_dc['TB Unit'].unique() if pd.notna(x) and x!=""])
                s6_tu = st.multiselect("TB Unit", tu_opts, key='tu6')
                if s6_tu: df_dc = df_dc[df_dc['TB Unit'].isin(s6_tu)]
            with c2:
                # 🎯 SMART FILTER CASCADING
                phi_opts = sorted([x for x in df_dc['PHI'].unique() if pd.notna(x) and x!=""])
                s6_phi = st.multiselect("PHI", phi_opts, key='phi6')
                if s6_phi: df_dc = df_dc[df_dc['PHI'].isin(s6_phi)]
                
                s6_hf = st.multiselect("Facility Type", sorted([x for x in df_dc['Facility_Type'].unique() if pd.notna(x) and x!=""]), key='hf6')
                if s6_hf: df_dc = df_dc[df_dc['Facility_Type'].isin(s6_hf)]
            with c3:
                comp_dates = st.date_input("Diagnosis Date Range", value=[], key="dc_main_dates")
        
        if len(comp_dates) == 2:
            df_dc = df_dc[pd.to_datetime(df_dc.get('Diagnosis Date'), errors='coerce').dt.date.between(comp_dates[0], comp_dates[1])]

        st.markdown("<hr>", unsafe_allow_html=True)
        periods_map = {'BASELINE': ('BASELINE', 'Elig_BASELINE'), '1ST MONTH': ('1ST MONTH|1 MONTH', 'Elig_1ST_MONTH'), '2ND MONTH': ('2ND MONTH|2 MONTH', 'Elig_2ND_MONTH'), '3RD MONTH': ('3RD MONTH|3 MONTH', 'Elig_3RD_MONTH'), '4TH MONTH': ('4TH MONTH|4 MONTH', 'Elig_4TH_MONTH'), '5TH MONTH': ('5TH MONTH|5 MONTH', 'Elig_5TH_MONTH'), '6TH MONTH': ('6TH MONTH|6 MONTH', 'Elig_6TH_MONTH')}
        sel_period = st.radio("📌 Select Follow-up Period:", list(periods_map.keys()), horizontal=True)
        p_regex, elig_col = periods_map[sel_period]
        
        g_col = 'TB Unit' if st.session_state.role == "ZONE" or (st.session_state.role == "ADMIN" and 's6_z' in locals() and len(s6_z) > 0) else 'ZONE' if st.session_state.role == "ADMIN" else 'PHI'
        
        def get_dynamic_summary(df, group_col):
            if df.empty: return pd.DataFrame()
            grp = df.groupby(group_col)
            total_pts = grp.size()
            is_elig = df[elig_col].fillna('').astype(str).str.upper().str.contains("ELIG") & ~df[elig_col].fillna('').astype(str).str.upper().str.contains("NOT")
            eligible_pts = df[is_elig].groupby(group_col).size()
            due = df['Due_Status'].fillna('').astype(str).str.upper()
            is_pending = is_elig & (~due.str.contains("COMPLETED", na=False)) & due.str.contains(p_regex, na=False)
            pending_pts = df[is_pending].groupby(group_col).size()
            
            summary = pd.DataFrame({'Total Patient': total_pts, 'Eligible': eligible_pts, 'Pending': pending_pts}).fillna(0).astype(int)
            summary['Completed'] = summary['Eligible'] - summary['Pending']
            summary['% Completed'] = ((summary['Completed'] / summary['Eligible']) * 100).fillna(0).round(1)
            
            summary = summary.reset_index()
            
            # 🎯 SORTING LOGIC: 7 Zones first, then MAPPING NOT DONE
            main_zones = ['CENTRAL', 'EAST', 'NORTH', 'NORTH WEST', 'SOUTH', 'SOUTH WEST', 'WEST']
            summary['sort_key'] = summary[group_col].apply(lambda x: main_zones.index(x) if x in main_zones else 998 if x == 'MAPPING NOT DONE' else 999)
            summary = summary.sort_values('sort_key').drop(columns=['sort_key'])
            
            total_row = pd.DataFrame({group_col: ['AMC TOTAL'], 'Total Patient': [summary['Total Patient'].sum()], 'Eligible': [summary['Eligible'].sum()], 'Completed': [summary['Completed'].sum()], 'Pending': [summary['Pending'].sum()]})
            total_row['% Completed'] = (total_row['Completed'] / total_row['Eligible'] * 100).round(1)
            return pd.concat([summary, total_row], ignore_index=True)

        sum_df = get_dynamic_summary(df_dc, g_col)
        st.markdown(f"##### 📊 {sel_period} Summary ({g_col} Wise)")

        # 🎯 TARGETED COLOR FORMATTING: Only on 7 main zones
        def apply_color(row):
            main_zones = ['CENTRAL', 'EAST', 'NORTH', 'NORTH WEST', 'SOUTH', 'SOUTH WEST', 'WEST']
            if row[g_col] in main_zones:
                try:
                    val = float(str(row['% Completed']).replace('%',''))
                    if val >= 80: return ['background-color: #d4edda'] * len(row) # લીલો 
                    elif val >= 50: return ['background-color: #fff3cd'] * len(row) # પીળો
                    else: return ['background-color: #f8d7da'] * len(row) # લાલ
                except:
                    return [''] * len(row)
            return [''] * len(row)

        sum_disp = sum_df.copy()
        sum_disp['% Completed'] = sum_disp['% Completed'].astype(str) + '%'
        st.dataframe(sum_disp.style.apply(apply_color, axis=1), use_container_width=True, hide_index=True)

        st.markdown(f"##### 📋 {sel_period} Pending Line List")
        is_elig_ll = df_dc[elig_col].fillna('').astype(str).str.upper().str.contains("ELIG") & ~df_dc[elig_col].fillna('').astype(str).str.upper().str.contains("NOT")
        due_ll = df_dc['Due_Status'].fillna('').astype(str).str.upper()
        is_pending_ll = is_elig_ll & (~due_ll.str.contains("COMPLETED", na=False)) & due_ll.str.contains(p_regex, na=False)
        df_ll = df_dc[is_pending_ll].copy()
        if not df_ll.empty:
            ll_cols = ['ZONE', 'TB Unit', 'PHI', 'Type_of_Case', 'Episode ID', 'Patient Name', 'Diagnosis Date', 'Initiation Date', 'Outcome Date', 'Treatment_Outcome', 'Due_Status']
            st.dataframe(df_ll[ll_cols].rename(columns={'Type_of_Case': 'Patient Type', 'Treatment_Outcome': 'Outcome', 'Due_Status': 'Pending Status'}), use_container_width=True, hide_index=True)
        else:
            st.success(f"🎉 No pending patients for {sel_period}!")

        # -------------------------------------------------------------
        # 🎯 🔄 DIFF CARE COMPARISON ENGINE (OLD VS NEW)
        # -------------------------------------------------------------
        st.markdown("<br><hr>", unsafe_allow_html=True)
        st.markdown("<h4 style='color: #E67E22;'>🔄 Diff Care Comparison Engine</h4>", unsafe_allow_html=True)
        
        # 🎯 Comparison engine filters (Smart Filter Cascading)
        cc1, cc2, cc3 = st.columns(3)
        df_dc_comp_new = df_dc_new.copy()
        df_dc_comp_old = df_dc_old.copy()
        
        with cc1:
            comp_zones = st.multiselect("Filter Zone (Comparison)", sorted([x for x in df_dc_comp_new['ZONE'].unique() if pd.notna(x) and x!=""]), key='dc_comp_zone')
            if comp_zones:
                df_dc_comp_new = df_dc_comp_new[df_dc_comp_new['ZONE'].isin(comp_zones)]
                df_dc_comp_old = df_dc_comp_old[df_dc_comp_old['ZONE'].isin(comp_zones)]
                
        with cc2:
            tu_opts_comp = sorted([x for x in df_dc_comp_new['TB Unit'].unique() if pd.notna(x) and x!=""])
            comp_tus = st.multiselect("Filter TB Unit (Comparison)", tu_opts_comp, key='dc_comp_tu')
            if comp_tus:
                df_dc_comp_new = df_dc_comp_new[df_dc_comp_new['TB Unit'].isin(comp_tus)]
                df_dc_comp_old = df_dc_comp_old[df_dc_comp_old['TB Unit'].isin(comp_tus)]
                
        with cc3:
            comp_d = st.date_input("Select Diagnosis Date Range for Comparison", value=[], key="dc_comp_dates")
            
        if st.button("🚀 Generate Comparison Matrix", use_container_width=True) and len(comp_d)==2:
            s_ts, e_ts = pd.Timestamp(comp_d[0]), pd.Timestamp(comp_d[1])
            def get_p_dict(df, sd, ed):
                dts = pd.to_datetime(df['Diagnosis Date'], format='%d-%m-%Y', errors='coerce').combine_first(pd.to_datetime(df['Diagnosis Date'], errors='coerce'))
                df_f = df[dts.notna() & dts.between(sd, ed)]
                p_dict = {}
                for _, r in df_f.iterrows():
                    eid, due = str(r['Episode ID']).strip().upper(), str(r.get('Due_Status','')).upper()
                    if "COMPLETED" in due: p_dict[eid] = []
                    else: p_dict[eid] = [pn for pn, (pr, ec) in periods_map.items() if re.search(pr, due)]
                return p_dict, df_f
                
            old_p, df_o = get_p_dict(df_dc_comp_old, s_ts, e_ts)
            new_p, df_n = get_p_dict(df_dc_comp_new, s_ts, e_ts)
            all_ids = set(list(old_p.keys()) + list(new_p.keys()))
            res = []
            for eid in all_ids:
                if not eid or eid=="NAN": continue
                po, pn = old_p.get(eid, []), new_p.get(eid, [])
                row = {'Episode ID': eid}; act = False
                for p_name in periods_map.keys():
                    it, iy = p_name in pn, p_name in po
                    if it and iy: row[p_name] = "🟡 PERSISTENT"; act = True
                    elif it and not iy: row[p_name] = "🔴 NEW"; act = True
                    elif not it and iy: row[p_name] = "🟢 RESOLVED"; act = True
                    else: row[p_name] = ""
                if act:
                    base = df_n[df_n['Episode ID']==eid].iloc[0] if eid in new_p else df_o[df_o['Episode ID']==eid].iloc[0]
                    row.update({'ZONE': base['ZONE'], 'TB Unit': base['TB Unit'], 'PHI': base['PHI'], 'Patient Name': base['Patient Name'], 'Facility Type': base['Facility_Type'], 'Diagnosis Date': base['Diagnosis Date']})
                    res.append(row)
            if res:
                df_res = pd.DataFrame(res)
                cols = ['ZONE', 'TB Unit', 'PHI', 'Episode ID', 'Patient Name', 'Facility Type', 'Diagnosis Date']
                st.dataframe(df_res[cols + [c for c in df_res.columns if c not in cols]], use_container_width=True, hide_index=True)
            else: st.info("No differences found.")
