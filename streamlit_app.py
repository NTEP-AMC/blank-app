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
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

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

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Master Dashboard", "🔄 Daily Comparison", "🏥 Current TB Patients", "🚀 Smart PPT", "🏥 Diff. Care", "👥 Staff Directory"])

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
            # 🎯 DEPENDENT FILTER: TB Unit based on Zone
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
            # 🎯 DEPENDENT FILTER: PHI based on TB Unit
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
# 🟢 TAB 2: DAILY COMPARISON (NO DATES DISPLAYED)
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
            # 🎯 DEPENDENT FILTER
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
            # 🎯 DEPENDENT FILTER
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
    
    # 🎯 FIX: Removing dates from Tab 2 UI display
    df_c_display = df_c.drop(columns=['Diagnosis Date', 'Initiation Date', 'Outcome Date'], errors='ignore')
    st.dataframe(df_c_display, use_container_width=True, hide_index=True)
    if not df_c_display.empty:
        st.download_button("📥 Download Comparison Matrix", convert_df_to_excel(df_c_display, "Comparison_Matrix"), "Comparison.xlsx", key='dl2')

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
            # 🎯 DEPENDENT FILTER
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
            # 🎯 DEPENDENT FILTER
            s3_phi = clean_selection(st.multiselect("Filter PHI", get_options_with_counts(df_t3, 'PHI', 'tab3'), key='phi3'))
            if s3_phi: df_t3 = df_t3[df_t3['PHI'].isin(s3_phi)]
    st.markdown("##### 📈 Patient Overview")
    st.markdown(draw_card("Total Active Patients", len(df_t3), "#16A085", "🏥"), unsafe_allow_html=True)
    t3_final_cols = [c for c in ['ZONE', 'TB Unit', 'PHI', 'Facility Type', 'Episode ID', 'Patient Name', 'Type of Case', 'TB_regimen', 'Diagnosis Date', 'Initiation Date', 'Outcome Date'] if c in df_t3.columns]
    st.dataframe(df_t3[t3_final_cols], use_container_width=True, hide_index=True)
    if not df_t3.empty:
        st.download_button("📥 Download Excel", convert_df_to_excel(df_t3[t3_final_cols], "Current_Patients"), "Current_Patients.xlsx", key='dl3')
# ==========================================
# 🟢 TAB 4: PPT GENERATOR (SMART + CORPORATE + NAAT)
# ==========================================
with tab4:
    st.markdown("<h3 style='text-align: center; color: #27AE60;'>🚀 Enterprise PPT Report Generator</h3>", unsafe_allow_html=True)
    
    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1:
            all_inds = ["Outcome", "UDST", "Not Put On", "SLPA", "Consent", "ADT", "RBS", "ART", "CPT", "HIV"]
            sel_report = st.selectbox("📌 1. Select Report Type", all_inds)
            st.markdown("<div style='background-color:#e8f4f8; padding:10px; border-radius:5px;'><b>📅 Period 1 (Current)</b></div>", unsafe_allow_html=True)
            p1_name = st.text_input("Name for Period 1", "Q1 - 2026")
            p1_diag = st.date_input("Diagnosis Date (P1)", value=[])
            p1_init = st.date_input("Treatment Start Date (P1)", value=[])
            p1_out = st.date_input("Outcome Date (P1)", value=[])
        with c2:
            st.write("")
            st.write("")
            compare_mode = st.checkbox("📊 Enable Comparison (Period 2)")
            if compare_mode:
                st.markdown("<div style='background-color:#fef5e7; padding:10px; border-radius:5px;'><b>📅 Period 2 (Previous)</b></div>", unsafe_allow_html=True)
                p2_name = st.text_input("Name for Period 2", "Q2 - 2026")
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
        if len(diag) == 2: mask &= pd.to_datetime(df.get('Diagnosis Date'), errors='coerce').dt.date.between(diag[0], diag[1])
        if len(init) == 2: mask &= pd.to_datetime(df.get('Initiation Date'), errors='coerce').dt.date.between(init[0], init[1])
        if len(out) == 2: mask &= pd.to_datetime(df.get('Outcome Date'), errors='coerce').dt.date.between(out[0], out[1])
        return mask

    def generate_smart_ppt(df, report_name):
        try:
            from pptx import Presentation
            from pptx.util import Inches, Pt
            from pptx.dml.color import RGBColor
            from pptx.enum.text import PP_ALIGN
        except ImportError: return None, "⚠️ PPTX લાઈબ્રેરી ઇન્સ્ટોલ નથી!"

        prs = Presentation()
        m1 = apply_date_filters(df, p1_diag, p1_init, p1_out)
        m1 &= df.get('Pending Status', pd.Series(dtype=str)).astype(str).str.contains(report_name, na=False)
        df_p1 = df[m1].copy()

        df_p2 = pd.DataFrame()
        if compare_mode:
            m2 = apply_date_filters(df, p2_diag, p2_init, p2_out)
            m2 &= df.get('Pending Status', pd.Series(dtype=str)).astype(str).str.contains(report_name, na=False)
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
            if os.path.exists("images/amc.png"): slide.shapes.add_picture("images/amc.png", Inches(0.2), Inches(0.15), width=Inches(0.7))
            if os.path.exists("images/ntep.jpg"): slide.shapes.add_picture("images/ntep.jpg", Inches(9.1), Inches(0.15), width=Inches(0.7))
            title = slide.shapes.title
            title.text = title_text
            title.top = Inches(0.25); title.left = Inches(1.2); title.width = Inches(7.6)
            title.text_frame.paragraphs[0].font.size = Pt(26)
            title.text_frame.paragraphs[0].font.bold = True
            title.text_frame.paragraphs[0].font.color.rgb = RGBColor(44, 62, 80)
            
            if curr_df.empty and prev_df.empty: return
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
            table_shape = slide.shapes.add_table(rows, cols, Inches(0.8), Inches(1.3), Inches(8.4), Inches(0.4))
            table = table_shape.table
            if cols == 2: table.columns[0].width = Inches(5.4); table.columns[1].width = Inches(3.0)
            elif cols == 4: table.columns[0].width = Inches(4.0); table.columns[1].width = Inches(1.5); table.columns[2].width = Inches(1.5); table.columns[3].width = Inches(1.4)
            for i, c_name in enumerate(col_names):
                cell = table.cell(0, i)
                cell.text = c_name
                cell.fill.solid(); cell.fill.fore_color.rgb = RGBColor(44, 62, 80)
                cell.text_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)
                cell.text_frame.paragraphs[0].font.bold = True
                if i > 0: cell.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            target_idx = col_names.index(color_target)
            max_value = final_df.iloc[:, target_idx].max() if not final_df.empty else 0
            for i, (_, row) in enumerate(final_df.iterrows()):
                name_val = str(row[entity_col_name])
                table.cell(i+1, 0).text = name_val
                c1_p = table.cell(i+1, 1).text_frame.paragraphs[0]
                c1_p.text = str(int(row[p1_name]))
                c1_p.alignment = PP_ALIGN.CENTER
                if cols == 4:
                    c2_p = table.cell(i+1, 2).text_frame.paragraphs[0]
                    c2_p.text = str(int(row[p2_name]))
                    c2_p.alignment = PP_ALIGN.CENTER
                    c3_p = table.cell(i+1, 3).text_frame.paragraphs[0]
                    c3_p.text = str(int(row['Grand Total']))
                    c3_p.alignment = PP_ALIGN.CENTER
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
                pub_mask = temp_df.get('Facility Type', pd.Series(dtype=str)).astype(str).str.upper().isin(['PUBLIC', 'PHI'])
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
            add_slide_table(f"{st.session_state.target} Zone - {sel_report} Pending", tu_curr, tu_prev, 'TB Unit')
            tus = sorted(pd.concat([df_p1.get('TB Unit', pd.Series()), df_p2.get('TB Unit', pd.Series()) if compare_mode else pd.Series()]).dropna().unique())
            for tu in tus:
                phi_curr = get_summary(df_p1[df_p1.get('TB Unit') == tu], 'PHI', p1_name)
                phi_prev = get_summary(df_p2[df_p2.get('TB Unit') == tu], 'PHI', p2_name) if compare_mode else pd.DataFrame()
                add_slide_table(f"TU: {tu} - {sel_report} Pending", phi_curr, phi_prev, 'PHI')

        elif st.session_state.role == "ADMIN":
            z_curr = get_summary(df_p1, 'ZONE', p1_name)
            z_prev = get_summary(df_p2, 'ZONE', p2_name) if compare_mode else pd.DataFrame()
            add_slide_table(f"All Zones - {sel_report} Pending", z_curr, z_prev, 'ZONE')
            zones = sorted(pd.concat([df_p1.get('ZONE', pd.Series()), df_p2.get('ZONE', pd.Series()) if compare_mode else pd.Series()]).dropna().unique())
            for z in zones:
                phi_curr = get_summary(df_p1[df_p1.get('ZONE') == z], 'PHI', p1_name)
                phi_prev = get_summary(df_p2[df_p2.get('ZONE') == z], 'PHI', p2_name) if compare_mode else pd.DataFrame()
                add_slide_table(f"Zone: {z} - {sel_report} Pending", phi_curr, phi_prev, 'PHI')
        else:
            phi_curr = get_summary(df_p1, 'PHI', p1_name)
            phi_prev = get_summary(df_p2, 'PHI', p2_name) if compare_mode else pd.DataFrame()
            add_slide_table(f"{st.session_state.target} - {sel_report} Pending", phi_curr, df_p2, 'PHI')

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
    # 🎯 2. MNC CORPORATE TARGET ACHIEVEMENT DECK
    # ==========================================
    st.markdown("<br><hr style='margin: 30px 0; border: 2px solid #e8f4f8;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #2C3E50;'>📈 Corporate Performance Deck (Zone + UHC/CHC)</h3>", unsafe_allow_html=True)

    with st.container():
        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            st.markdown("<div style='background-color:#fef9e7; padding:10px; border-radius:5px;'><b>🗓️ 1. Date Selection</b></div>", unsafe_allow_html=True)
            target_dates = st.date_input("Select Dates to Sum (e.g., April 1 to April 5)", value=[], key="t_dates")
        with tc2:
            st.markdown("<div style='background-color:#e8f8f5; padding:10px; border-radius:5px;'><b>🔢 2. Target Multiplier</b></div>", unsafe_allow_html=True)
            working_days = st.number_input("Enter Total Working Days", min_value=1, max_value=31, value=5, key="t_wdays")
        with tc3:
            st.markdown("<div style='background-color:#ebedf0; padding:10px; border-radius:5px;'><b>⚙️ 3. Action</b></div>", unsafe_allow_html=True)
            st.write("")
            btn_generate_target = st.button("✨ Generate Full Deck ✨", use_container_width=True)

    def generate_corporate_target_ppt(selected_dates, w_days):
        try:
            from pptx import Presentation
            from pptx.util import Inches, Pt
            from pptx.dml.color import RGBColor
            from pptx.enum.text import PP_ALIGN
            import re
            
            def add_corporate_slide(prs_obj, title_text):
                slide = prs_obj.slides.add_slide(prs_obj.slide_layouts[5])
                if os.path.exists("images/amc.png"): slide.shapes.add_picture("images/amc.png", Inches(0.2), Inches(0.15), width=Inches(0.6))
                if os.path.exists("images/ntep.jpg"): slide.shapes.add_picture("images/ntep.jpg", Inches(9.2), Inches(0.15), width=Inches(0.6))
                title = slide.shapes.title; title.text = title_text
                title.top = Inches(0.25); title.left = Inches(1.0)
                title.width = Inches(8.0); title.height = Inches(0.8)
                title.text_frame.paragraphs[0].font.size = Pt(24); title.text_frame.paragraphs[0].font.bold = True
                title.text_frame.paragraphs[0].font.color.rgb = RGBColor(44, 62, 80)
                return slide

            def format_corporate_table(table_obj, df_data, col_widths, font_size=12):
                rows, cols = len(df_data) + 1, len(df_data.columns)
                for i, width in enumerate(col_widths): table_obj.columns[i].width = width
                for i, col_name in enumerate(df_data.columns):
                    cell = table_obj.cell(0, i); cell.text = col_name
                    cell.fill.solid(); cell.fill.fore_color.rgb = RGBColor(44, 62, 80)
                    cell.text_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)
                    cell.text_frame.paragraphs[0].font.bold = True; cell.text_frame.paragraphs[0].font.size = Pt(12)
                    if i > 1: cell.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
                for i in range(1, rows):
                    for j in range(cols):
                        cell = table_obj.cell(i, j)
                        for p in cell.text_frame.paragraphs: 
                            p.font.size = Pt(font_size)
                            if j > 1: p.alignment = PP_ALIGN.CENTER

            def extract_num(val):
                nums = re.findall(r'^(\d+)', str(val).strip())
                return int(nums[0]) if nums else 0

            def get_multi_color(pct):
                if pct >= 100: return RGBColor(46, 204, 113)
                elif pct >= 75: return RGBColor(171, 235, 198)
                elif pct >= 50: return RGBColor(249, 231, 159)
                elif pct >= 25: return RGBColor(245, 176, 65)
                else: return RGBColor(231, 76, 60)

            if len(selected_dates) == 2:
                date_list = pd.date_range(start=selected_dates[0], end=selected_dates[1]).tolist()
                target_date_strings = [f"{d.strftime('%b')} {d.day}, {d.year}" for d in date_list]
            else: return None, "⚠️ Please select a start and end date."

            prs = Presentation()
            fixed_targets = {"Central": 59, "North": 122, "East": 117, "South": 159, "West": 121, "North West": 77, "South West": 55, "AMC": 710}
            target_url = "https://docs.google.com/spreadsheets/d/19Whbn-0bGNxVcxiGmp9fCq44dKeNZXAAbPiXtVf3zcs/export?format=csv&gid=972568835"
            df_sheet1 = pd.read_csv(target_url, header=None)
            
            h_idx1 = 0
            for i in range(3):
                if any(td in df_sheet1.iloc[i].fillna("").astype(str).tolist() for td in target_date_strings):
                    h_idx1 = i; break
            
            header_row1 = df_sheet1.iloc[h_idx1].fillna("").astype(str)
            col_indices1 = [idx for idx, val in enumerate(header_row1) if val.replace("  ", " ").strip() in target_date_strings]
            
            if col_indices1:
                res1 = []
                for row_idx in range(h_idx1 + 1, len(df_sheet1)):
                    z_name = str(df_sheet1.iloc[row_idx, 0]).strip().title()
                    if z_name.upper() == "AMC": z_name = "AMC" 
                    if z_name in fixed_targets:
                        ach_total = sum([extract_num(df_sheet1.iloc[row_idx, c]) for c in col_indices1])
                        t_day = fixed_targets[z_name]
                        m_target = t_day * w_days
                        pct = round((ach_total / m_target) * 100, 1) if m_target > 0 else 0
                        res1.append({"ZONE": z_name, "TARGET PER DAY": t_day, "MONTH TARGET": m_target, "TOTAL ACHIEVED": ach_total, "ACHIEVEMENT %": pct})
                
                df_display1 = pd.DataFrame(res1)
                df_display1["ACHIEVEMENT %"] = df_display1["ACHIEVEMENT %"].astype(str) + "%"
                
                s1 = add_corporate_slide(prs, f"Cumulative Target Achievement (Days: {w_days})")
                t1_shape = s1.shapes.add_table(len(df_display1) + 1, len(df_display1.columns), Inches(0.5), Inches(1.3), Inches(9.0), Inches(0.4))
                format_corporate_table(t1_shape.table, df_display1, [Inches(2.0), Inches(1.5), Inches(1.8), Inches(1.7), Inches(2.0)])
                
                for i, row in df_display1.iterrows():
                    for j in range(len(df_display1.columns)):
                        cell = t1_shape.table.cell(i+1, j)
                        cell.text = str(row.iloc[j])
                        if row['ZONE'] == "AMC":
                            cell.fill.solid(); cell.fill.fore_color.rgb = RGBColor(235, 237, 239)
                            cell.text_frame.paragraphs[0].font.bold = True
                        if j == 4 and row['ZONE'].upper() != "AMC":
                            pct_val = float(str(row.iloc[j]).replace('%', ''))
                            cell.fill.solid(); cell.fill.fore_color.rgb = get_multi_color(pct_val)

            fac_url = "https://docs.google.com/spreadsheets/d/19Whbn-0bGNxVcxiGmp9fCq44dKeNZXAAbPiXtVf3zcs/export?format=csv&gid=0"
            df_fac = pd.read_csv(fac_url, header=None)
            
            h_idx2 = 0
            for i in range(4):
                if any(td in df_fac.iloc[i].fillna("").astype(str).tolist() for td in target_date_strings):
                    h_idx2 = i; break
            
            header_fac = df_fac.iloc[h_idx2].fillna("").astype(str)
            col_indices_fac = [idx for idx, val in enumerate(header_fac) if val.replace("  ", " ").strip() in target_date_strings]

            if col_indices_fac:
                fac_data = []
                for row_idx in range(h_idx2 + 1, len(df_fac)):
                    zone_guj = str(df_fac.iloc[row_idx, 0]).strip()
                    fac_name = str(df_fac.iloc[row_idx, 1]).strip()
                    if "કુલ" in fac_name or "કુલ" in zone_guj or fac_name in ["", "nan", "None"]: continue
                        
                    achieved_total = sum([extract_num(df_fac.iloc[row_idx, c]) for c in col_indices_fac])
                    fac_type, target_daily = "OTHER", 0
                    
                    if "અર્બન હેલ્થ સેન્ટર" in fac_name: fac_type, target_daily = "UHC", 4
                    elif "સામુહીક" in fac_name or "સામુહિક" in fac_name: fac_type, target_daily = "CHC", 16
                    
                    if fac_type in ["UHC", "CHC"]:
                        month_target = target_daily * w_days
                        ach_pct = round((achieved_total / month_target) * 100, 1) if month_target > 0 else 0
                        fac_data.append({"Zone": zone_guj, "Facility Name": fac_name, "Type": fac_type, "Target": month_target, "Achieved": achieved_total, "Achievement %": ach_pct})
                
                df_fac_processed = pd.DataFrame(fac_data)

                if not df_fac_processed.empty:
                    df_uhc = df_fac_processed[(df_fac_processed["Type"] == "UHC") & (df_fac_processed["Achievement %"] < 75)].sort_values("Achievement %").drop(columns=["Type"]).reset_index(drop=True)
                    df_uhc_display = df_uhc.copy()
                    df_uhc_display["Achievement %"] = df_uhc_display["Achievement %"].astype(str) + "%"
                    
                    chunk_size = 12
                    for i in range(0, len(df_uhc_display), chunk_size):
                        chunk = df_uhc_display.iloc[i:i+chunk_size]
                        s2 = add_corporate_slide(prs, f"📉 UHCs Requiring Attention (< 75%){' (Part ' + str(i//chunk_size + 1) + ')' if len(df_uhc_display)>chunk_size else ''}")
                        t2 = s2.shapes.add_table(len(chunk) + 1, len(chunk.columns), Inches(0.5), Inches(1.2), Inches(9.0), Inches(0.35))
                        format_corporate_table(t2.table, chunk, [Inches(1.5), Inches(4.0), Inches(1.0), Inches(1.0), Inches(1.5)], font_size=11)
                        for row_idx_c, (orig_idx, row) in enumerate(chunk.iterrows()):
                            for j in range(len(chunk.columns)):
                                cell = t2.table.cell(row_idx_c+1, j); cell.text = str(row.iloc[j])
                                for p in cell.text_frame.paragraphs: 
                                    p.font.size = Pt(11)
                                    if j > 1: p.alignment = PP_ALIGN.CENTER
                                if j == 4:
                                    cell.fill.solid(); cell.fill.fore_color.rgb = get_multi_color(df_uhc.iloc[orig_idx]["Achievement %"])

                if not df_fac_processed.empty:
                    df_chc = df_fac_processed[df_fac_processed["Type"] == "CHC"].sort_values("Achievement %", ascending=False).drop(columns=["Type"]).reset_index(drop=True)
                    df_chc_display = df_chc.copy()
                    df_chc_display["Achievement %"] = df_chc_display["Achievement %"].astype(str) + "%"
                    
                    for i in range(0, len(df_chc_display), 12):
                        chunk = df_chc_display.iloc[i:i+12]
                        s3 = add_corporate_slide(prs, f"🏥 All CHCs Performance Overview{' (Part ' + str(i//12 + 1) + ')' if len(df_chc_display)>12 else ''}")
                        t3 = s3.shapes.add_table(len(chunk) + 1, len(chunk.columns), Inches(0.5), Inches(1.2), Inches(9.0), Inches(0.35))
                        format_corporate_table(t3.table, chunk, [Inches(1.5), Inches(4.0), Inches(1.0), Inches(1.0), Inches(1.5)], font_size=11)
                        for row_idx_c, (orig_idx, row) in enumerate(chunk.iterrows()):
                            for j in range(len(chunk.columns)):
                                cell = t3.table.cell(row_idx_c+1, j); cell.text = str(row.iloc[j])
                                for p in cell.text_frame.paragraphs: 
                                    p.font.size = Pt(11)
                                    if j > 1: p.alignment = PP_ALIGN.CENTER
                                if j == 4:
                                    cell.fill.solid(); cell.fill.fore_color.rgb = get_multi_color(df_chc.iloc[orig_idx]["Achievement %"])
                                elif row_idx_c % 2 != 0: cell.fill.solid(); cell.fill.fore_color.rgb = RGBColor(242, 243, 244)
            
            out_io = io.BytesIO()
            prs.save(out_io)
            return out_io.getvalue(), "Success"
        except Exception as e: return None, f"⚠️ Error: {str(e)}"

    if btn_generate_target:
        if len(target_dates) != 2: st.error("⚠️ Please select both a Start Date and End Date.")
        else:
            with st.spinner("Fetching Live Sheet Data and generating Corporate Deck..."):
                target_ppt_bytes, t_status = generate_corporate_target_ppt(target_dates, working_days)
                if target_ppt_bytes:
                    st.success("✅ Corporate Presentation Deck Ready!")
                    st.download_button(label="📥 Download Corporate_Deck.pptx", data=target_ppt_bytes, file_name="Corporate_Performance_Deck.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation", key="dl_target_ppt")
                else: st.error(t_status)


    # ==========================================
    # 🎯 3. NAAT UTILIZATION REPORT DECK
    # ==========================================
    st.markdown("<br><hr style='margin: 30px 0; border: 2px solid #e8f4f8;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #E67E22;'>🔬 NAAT Utilization Report Generator</h3>", unsafe_allow_html=True)

    with st.container():
        nc1, nc2, nc3 = st.columns(3)
        with nc1:
            st.markdown("<div style='background-color:#fef9e7; padding:10px; border-radius:5px;'><b>🗓️ 1. Date Selection</b></div>", unsafe_allow_html=True)
            naat_dates = st.date_input("Select NAAT Dates", value=[], key="n_dates")
        with nc2:
            st.markdown("<div style='background-color:#e8f8f5; padding:10px; border-radius:5px;'><b>🔢 2. Divisor</b></div>", unsafe_allow_html=True)
            naat_wdays = st.number_input("Enter Working Days (for Average)", min_value=1, max_value=31, value=5, key="n_wdays")
        with nc3:
            st.markdown("<div style='background-color:#ebedf0; padding:10px; border-radius:5px;'><b>⚙️ 3. Action</b></div>", unsafe_allow_html=True)
            st.write("")
            btn_generate_naat = st.button("✨ Generate NAAT PPT ✨", use_container_width=True)

    def generate_naat_ppt(selected_dates, w_days):
        try:
            from pptx import Presentation
            from pptx.util import Inches, Pt
            from pptx.dml.color import RGBColor
            from pptx.enum.text import PP_ALIGN
            import re
            
            def add_corporate_slide(prs_obj, title_text):
                slide = prs_obj.slides.add_slide(prs_obj.slide_layouts[5])
                if os.path.exists("images/amc.png"): slide.shapes.add_picture("images/amc.png", Inches(0.2), Inches(0.15), width=Inches(0.6))
                if os.path.exists("images/ntep.jpg"): slide.shapes.add_picture("images/ntep.jpg", Inches(9.2), Inches(0.15), width=Inches(0.6))
                title = slide.shapes.title; title.text = title_text
                title.top = Inches(0.25); title.left = Inches(1.0)
                title.width = Inches(8.0); title.height = Inches(0.8)
                title.text_frame.paragraphs[0].font.size = Pt(24); title.text_frame.paragraphs[0].font.bold = True
                title.text_frame.paragraphs[0].font.color.rgb = RGBColor(44, 62, 80)
                return slide

            def format_corporate_table(table_obj, df_data, col_widths, font_size=12):
                rows, cols = len(df_data) + 1, len(df_data.columns)
                for i, width in enumerate(col_widths): table_obj.columns[i].width = width
                for i, col_name in enumerate(df_data.columns):
                    cell = table_obj.cell(0, i); cell.text = col_name
                    cell.fill.solid(); cell.fill.fore_color.rgb = RGBColor(44, 62, 80)
                    cell.text_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)
                    cell.text_frame.paragraphs[0].font.bold = True; cell.text_frame.paragraphs[0].font.size = Pt(12)
                    if i > 1: cell.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
                for i in range(1, rows):
                    for j in range(cols):
                        cell = table_obj.cell(i, j)
                        for p in cell.text_frame.paragraphs: 
                            p.font.size = Pt(font_size)
                            if j > 1: p.alignment = PP_ALIGN.CENTER
            
            if len(selected_dates) == 2:
                date_list = pd.date_range(start=selected_dates[0], end=selected_dates[1]).tolist()
            else: return None, "⚠️ Please select a start and end date."

            naat_url = "https://docs.google.com/spreadsheets/d/1a1F3BZsGjgM8-_JY0ohbvsODxM6cPPLksDRFlaVgB0s/export?format=csv&gid=806626302"
            df_naat = pd.read_csv(naat_url, header=None)
            df_naat[0] = df_naat[0].replace(["", "nan", "NaN", "None"], pd.NA).ffill()
            
            date_row = df_naat.iloc[0].replace(["", "nan", "NaN", "None"], pd.NA).ffill().astype(str).str.strip()
            header_row = df_naat.iloc[1].fillna("").astype(str).str.upper().str.strip()
            
            tested_cols = []
            for d in date_list:
                fmts = [d.strftime("%m/%d/%Y"), f"{d.month:02d}/{d.day:02d}/{d.year}", f"{d.month}/{d.day}/{d.year}", d.strftime("%d/%m/%Y")]
                match_indices = []
                for i, val in enumerate(date_row):
                    val_clean = val.split(" ")[0].strip()
                    if val_clean in fmts: match_indices.append(i)
                for idx in match_indices:
                    if "TESTED" in header_row[idx]:
                        tested_cols.append(idx); break
                            
            if not tested_cols: return None, "⚠️ Could not find 'NAAT TESTED' columns for selected dates."
                
            df_valid = df_naat.iloc[2:].copy()
            mask_tot = (df_valid[0].astype(str).str.upper().str.contains("TOTAL", na=False) | df_valid[1].astype(str).str.upper().str.contains("TOTAL", na=False) | df_valid[2].astype(str).str.upper().str.contains("TOTAL", na=False))
            df_valid = df_valid[~mask_tot]
            
            df_valid['Tested_Sum'] = 0
            for col in tested_cols: df_valid['Tested_Sum'] += pd.to_numeric(df_valid[col], errors='coerce').fillna(0)
            
            grouped = df_valid.groupby(0)['Tested_Sum'].sum().reset_index()
            grouped.columns = ['NAAT Site', 'Tested']
            
            def format_avg(val): return int(val) if float(val).is_integer() else round(float(val), 1)
            grouped['Tested'] = grouped['Tested'].astype(int)
            grouped['Average'] = (grouped['Tested'] / w_days).apply(format_avg)
            
            def clean_site(s):
                c = str(s).upper().replace("CBNAAT", "").replace("TRUNAAT", "").strip(" -,")
                return c if c not in ["NAN", "NONE", ""] else ""
            grouped['NAAT Site'] = grouped['NAAT Site'].apply(clean_site)
            grouped = grouped[grouped['NAAT Site'] != ""]
            
            zone_map_strict = {"MC- CIVIL HOSPITAL, AMC": "Central", "MC-GCS MEDICAL COLLEGE, AMC": "North", "MC GMERS SOLA": "North West", "DH SCL GEN. HOSP.": "North", "UCHC VATVA": "South", "UCHC SABARMATI": "West", "MC-NHL MEDICAL COLLEGE, AMC": "West", "UCHC THALTEJ": "North West", "NARENDRA MODI MC": "South", "FAISALNAGAR CHC": "South", "UCHC DANILIMDA": "South", "UCHC BEHERAMPURA": "South", "CHC VASTRAL": "East", "SDH ESIC MODEL HOSP.": "North", "UHC RANIP": "West", "MC-NARENDRA MODI MEDICAL COLLEGE": "South", "UCHC CHANDKHEDA": "West", "UCHC RAKHIAL": "North", "CHC SARKHEJ": "South West", "UCHC NARODA": "North", "UHC SAIJPUR": "North", "MC-DR. M K SHAH MEDICAL COLLEGE AND RESEARCH CENTER AMC": "West", "UHC SHAHPUR": "Central", "UHC STADIUM": "West", "UHC JAMALPUR": "Central", "UHC GHATLODIA": "North West", "UHC VIRATNAGAR": "East", "UCHC GOMTIPUR": "East", "UHC ISANPUR": "South", "UHC BHAIPURA": "East", "JODHPUR UHC": "South West", "UHC NAVRANGPURA": "West"}
            clean_zone_map = {re.sub(r'[^A-Z0-9]', '', k.replace("CBNAAT","").replace("TRUNAAT","").upper()): v for k,v in zone_map_strict.items()}

            def get_zone(site):
                c_site = re.sub(r'[^A-Z0-9]', '', str(site).replace("CBNAAT","").replace("TRUNAAT","").upper())
                for k, v in clean_zone_map.items():
                    if k in c_site or c_site in k: return v
                if "SOLA" in c_site: return "North West"
                if "NHL" in c_site or "SABARMATI" in c_site: return "West"
                if "GCS" in c_site or "SHARDABEN" in c_site: return "East"
                if "ASARWA" in c_site or "CIVIL" in c_site: return "Central"
                if "VATVA" in c_site or "MANINAGAR" in c_site or "KANKARIA" in c_site: return "South"
                return "AMC" 
                
            grouped.insert(0, 'Zone', grouped['NAAT Site'].apply(get_zone))
            grouped = grouped.sort_values(by=['Zone', 'Tested'], ascending=[True, False]).reset_index(drop=True)
            
            total_tested = int(grouped['Tested'].sum())
            total_avg = format_avg(total_tested / w_days)
            total_row = pd.DataFrame([{"Zone": "AMC", "NAAT Site": "TOTAL", "Tested": total_tested, "Average": total_avg}])
            grouped = pd.concat([grouped, total_row], ignore_index=True)
            
            prs = Presentation()
            chunk_size = 13
            for i in range(0, len(grouped), chunk_size):
                chunk = grouped.iloc[i:i+chunk_size]
                title_suffix = f" (Part {i//chunk_size + 1})" if len(grouped) > chunk_size else ""
                s = add_corporate_slide(prs, f"🔬 NAAT Utilization Report{title_suffix}")
                t_shape = s.shapes.add_table(len(chunk) + 1, len(chunk.columns), Inches(0.8), Inches(1.2), Inches(8.4), Inches(0.35))
                format_corporate_table(t_shape.table, chunk, [Inches(1.5), Inches(4.5), Inches(1.2), Inches(1.2)], font_size=11)
                
                for row_idx, (orig_idx, row) in enumerate(chunk.iterrows()):
                    is_total_row = (row['Zone'] == "AMC" and row['NAAT Site'] == "TOTAL")
                    for j in range(len(chunk.columns)):
                        cell = t_shape.table.cell(row_idx+1, j); cell.text = str(row.iloc[j])
                        if is_total_row:
                            cell.fill.solid(); cell.fill.fore_color.rgb = RGBColor(235, 237, 239)
                            for p in cell.text_frame.paragraphs: p.font.bold = True; p.font.size = Pt(11); p.alignment = PP_ALIGN.CENTER if j > 1 else None
                        else:
                            for p in cell.text_frame.paragraphs: p.font.size = Pt(11); p.alignment = PP_ALIGN.CENTER if j > 1 else None
                            if j == 3 and float(row['Average']) < 16: cell.fill.solid(); cell.fill.fore_color.rgb = RGBColor(241, 148, 138) 
                            elif row_idx % 2 != 0: cell.fill.solid(); cell.fill.fore_color.rgb = RGBColor(242, 243, 244) 
                            
            out_io = io.BytesIO()
            prs.save(out_io)
            return out_io.getvalue(), "Success"

        except Exception as e: return None, f"⚠️ Error: {str(e)}"

    if btn_generate_naat:
        if len(naat_dates) != 2: st.error("⚠️ Please select both a Start Date and End Date.")
        else:
            with st.spinner("Analyzing NAAT Data and generating PPT..."):
                naat_ppt_bytes, n_status = generate_naat_ppt(naat_dates, naat_wdays)
                if naat_ppt_bytes:
                    st.success("✅ NAAT Utilization Deck Ready!")
                    st.download_button(label="📥 Download NAAT_Report.pptx", data=naat_ppt_bytes, file_name="NAAT_Utilization_Report.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation", key="dl_naat_ppt")
                else: st.error(n_status)
# ==========================================
# 🟢 TAB 5: DIFFERENTIATED CARE (MINI BOXES, DYNAMIC MATRIX & COMPARISON ENGINE)
# ==========================================
with tab5:
    st.markdown("<h3 style='color: #1f618d;'>🏥 Differentiated Care Tracking System</h3>", unsafe_allow_html=True)
    
    if df_dc_new.empty:
        st.warning("⚠️ ડેટા મળ્યો નથી. ગુગલ શીટ અને લોગિન ઝોન ચેક કરો.")
    else:
        with st.expander("🔽 Filters & Dates (Applies to Current Status)", expanded=False):
            df_dc = df_dc_new.copy()
            c1, c2, c3 = st.columns(3)
            
            with c1:
                if st.session_state.role == "ADMIN":
                    s6_z = st.multiselect("Zone", sorted([x for x in df_dc['ZONE'].unique() if pd.notna(x) and x!=""]), key='z6')
                    if s6_z: df_dc = df_dc[df_dc['ZONE'].isin(s6_z)]
                
                # 🎯 DEPENDENT FILTER
                tu_opts = sorted([x for x in df_dc['TB Unit'].unique() if pd.notna(x) and x!=""])
                s6_tu = st.multiselect("TB Unit", tu_opts, key='tu6')
                if s6_tu: df_dc = df_dc[df_dc['TB Unit'].isin(s6_tu)]
                
                # 🎯 DEPENDENT FILTER
                phi_opts = sorted([x for x in df_dc['PHI'].unique() if pd.notna(x) and x!=""])
                s6_phi = st.multiselect("PHI", phi_opts, key='phi6')
                if s6_phi: df_dc = df_dc[df_dc['PHI'].isin(s6_phi)]
                
            with c2:
                s6_hf = st.multiselect("Facility Type", sorted([x for x in df_dc['Facility_Type'].unique() if pd.notna(x) and x!=""]), key='hf6')
                if s6_hf: df_dc = df_dc[df_dc['Facility_Type'].isin(s6_hf)]
                
                s6_case = st.multiselect("Type of Case", sorted([x for x in df_dc['Type_of_Case'].unique() if pd.notna(x) and x!=""]), key='case6')
                if s6_case: df_dc = df_dc[df_dc['Type_of_Case'].isin(s6_case)]
                
                s6_site = st.multiselect("Site of TBDisease", sorted([x for x in df_dc['Site_of_TBDisease'].unique() if pd.notna(x) and x!=""]), key='site6')
                if s6_site: df_dc = df_dc[df_dc['Site_of_TBDisease'].isin(s6_site)]
                
                s6_outcol = st.multiselect("Treatment Outcome", sorted([x for x in df_dc['Treatment_Outcome'].unique() if pd.notna(x) and x!=""]), key='outcol6')
                if s6_outcol: df_dc = df_dc[df_dc['Treatment_Outcome'].isin(s6_outcol)]

            with c3:
                diag_dt6 = st.date_input("Diagnosis Date Range", value=[], key="d1_6")
                init_dt6 = st.date_input("Initiation Date Range", value=[], key="d2_6")
                out_dt6 = st.date_input("Outcome Date Range", value=[], key="d3_6")
                
        if len(diag_dt6) == 2: df_dc = df_dc[pd.to_datetime(df_dc.get('Diagnosis Date'), errors='coerce').notna() & pd.to_datetime(df_dc.get('Diagnosis Date'), errors='coerce').dt.date.between(diag_dt6[0], diag_dt6[1])]
        if len(init_dt6) == 2: df_dc = df_dc[pd.to_datetime(df_dc.get('Initiation Date'), errors='coerce').notna() & pd.to_datetime(df_dc.get('Initiation Date'), errors='coerce').dt.date.between(init_dt6[0], init_dt6[1])]
        if len(out_dt6) == 2: df_dc = df_dc[pd.to_datetime(df_dc.get('Outcome Date'), errors='coerce').notna() & pd.to_datetime(df_dc.get('Outcome Date'), errors='coerce').dt.date.between(out_dt6[0], out_dt6[1])]

        st.markdown("<hr>", unsafe_allow_html=True)
        
        periods_map = {
            'BASELINE': ('BASELINE', 'Elig_BASELINE'),
            '1ST MONTH': ('1ST MONTH|1 MONTH', 'Elig_1ST_MONTH'),
            '2ND MONTH': ('2ND MONTH|2 MONTH', 'Elig_2ND_MONTH'),
            '3RD MONTH': ('3RD MONTH|3 MONTH', 'Elig_3RD_MONTH'),
            '4TH MONTH': ('4TH MONTH|4 MONTH', 'Elig_4TH_MONTH'),
            '5TH MONTH': ('5TH MONTH|5 MONTH', 'Elig_5TH_MONTH'),
            '6TH MONTH': ('6TH MONTH|6 MONTH', 'Elig_6TH_MONTH')
        }
        
        sel_period = st.radio("📌 Select Follow-up Period to View:", list(periods_map.keys()), horizontal=True)
        p_regex, elig_col = periods_map[sel_period]
        g_col = 'TB Unit' if st.session_state.role == "ZONE" or (st.session_state.role == "ADMIN" and 's6_z' in locals() and len(s6_z) > 0) else 'ZONE' if st.session_state.role == "ADMIN" else 'PHI'
        
        def get_dynamic_summary(df, group_col):
            if df.empty: return pd.DataFrame()
            grp = df.groupby(group_col)
            total_pts = grp.size()
            is_elig = df[elig_col].fillna('').astype(str).str.upper().str.contains("ELIG") & ~df[elig_col].fillna('').astype(str).str.upper().str.contains("NOT")
            eligible_pts = df[is_elig].groupby(group_col).size()
            due = df['Due_Status'].fillna('').astype(str).str.upper()
            not_comp = ~due.str.contains("COMPLETED", na=False)
            is_pending = is_elig & not_comp & due.str.contains(p_regex, na=False)
            pending_pts = df[is_pending].groupby(group_col).size()
            
            summary = pd.DataFrame({'Total Patient': total_pts, 'Eligible': eligible_pts, 'Pending': pending_pts}).fillna(0).astype(int)
            summary['Completed'] = summary['Eligible'] - summary['Pending']
            
            total_patient = summary['Total Patient'].sum()
            total_eligible = summary['Eligible'].sum()
            total_completed = summary['Completed'].sum()
            total_pending = summary['Pending'].sum()
            total_pct = (total_completed / total_eligible * 100) if total_eligible > 0 else 0
            
            summary['% Completed'] = ((summary['Completed'] / summary['Eligible']) * 100).fillna(0).round(1)
            summary = summary.reset_index()
            
            main_zones = ['CENTRAL', 'EAST', 'NORTH', 'NORTH WEST', 'SOUTH', 'SOUTH WEST', 'WEST']
            summary['sort_key'] = summary[group_col].apply(lambda x: main_zones.index(x) if x in main_zones else 998 if x == 'MAPPING NOT DONE' else 999)
            summary = summary.sort_values('sort_key').drop(columns=['sort_key'])
            
            total_row = pd.DataFrame({group_col: ['AMC TOTAL'], 'Total Patient': [total_patient], 'Eligible': [total_eligible], 'Completed': [total_completed], 'Pending': [total_pending], '% Completed': [round(total_pct, 1)]})
            return pd.concat([summary, total_row], ignore_index=True)

        summary_df = get_dynamic_summary(df_dc, g_col)
        
        main_zones = ['CENTRAL', 'EAST', 'NORTH', 'NORTH WEST', 'SOUTH', 'SOUTH WEST', 'WEST']
        
        # 🎯 7 MINI BOXES
        if st.session_state.role == "ADMIN" and ('s6_z' not in locals() or len(s6_z) == 0):
            st.markdown(f"##### 🎯 {sel_period} - Zone Wise % Completed")
            cols7 = st.columns(7)
            for i, z in enumerate(main_zones):
                z_row = summary_df[summary_df[g_col] == z]
                pct_val = 0
                if not z_row.empty: pct_val = z_row['% Completed'].values[0]
                
                if pct_val >= 75: bg_c, t_c = "#d4edda", "#155724" # Green
                elif pct_val >= 50: bg_c, t_c = "#fff3cd", "#856404" # Yellow
                else: bg_c, t_c = "#f8d7da", "#721c24" # Red
                
                card_html = f"""<div style="background-color: {bg_c}; color: {t_c}; border-radius: 5px; padding: 6px 1px; margin-bottom: 10px; text-align: center; border: 1px solid rgba(0,0,0,0.1);"><div style="font-size: 10px; font-weight: bold; text-transform: uppercase;">{z}</div><div style="font-size: 16px; font-weight: 900; margin-top: 2px;">{pct_val}%</div></div>"""
                with cols7[i]: st.markdown(card_html, unsafe_allow_html=True)

        st.markdown(f"##### 📊 {sel_period} Summary ({g_col} Wise)")

        # TARGETED TABLE COLORING
        def color_table(df):
            style_df = pd.DataFrame('', index=df.index, columns=df.columns)
            for i in df.index:
                zone_val = df.at[i, g_col]
                if zone_val in main_zones:
                    try:
                        val_str = str(df.at[i, '% Completed']).replace('%', '')
                        val = float(val_str)
                        if val >= 75:
                            style_df.at[i, '% Completed'] = 'background-color: #d4edda; color: #155724; font-weight: bold;'
                        elif val >= 50:
                            style_df.at[i, '% Completed'] = 'background-color: #fff3cd; color: #856404; font-weight: bold;'
                        else:
                            style_df.at[i, '% Completed'] = 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
                    except: pass
            return style_df

        sum_disp = summary_df.copy()
        sum_disp['% Completed'] = sum_disp['% Completed'].astype(str) + '%'
        
        styled_df = sum_disp.style.apply(color_table, axis=None)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

        st.markdown(f"##### 📋 {sel_period} Pending Line List")
        is_elig_ll = df_dc[elig_col].fillna('').astype(str).str.upper().str.contains("ELIG") & ~df_dc[elig_col].fillna('').astype(str).str.upper().str.contains("NOT")
        due_ll = df_dc['Due_Status'].fillna('').astype(str).str.upper()
        not_comp_ll = ~due_ll.str.contains("COMPLETED", na=False)
        is_pending_ll = is_elig_ll & not_comp_ll & due_ll.str.contains(p_regex, na=False)
        
        df_ll = df_dc[is_pending_ll].copy()
        if not df_ll.empty:
            ll_cols = ['ZONE', 'TB Unit', 'PHI', 'Type_of_Case', 'Episode ID', 'Patient Name', 'Diagnosis Date', 'Initiation Date', 'Outcome Date', 'Treatment_Outcome', 'Due_Status']
            df_ll_display = df_ll[ll_cols].rename(columns={'Type_of_Case': 'Patient Type', 'Treatment_Outcome': 'Outcome', 'Due_Status': 'Pending Status'})
            st.dataframe(df_ll_display, use_container_width=True, hide_index=True)
            st.download_button(f"📥 Download {sel_period} Pending List", convert_df_to_excel(df_ll_display, f"{sel_period}_Pending"), f"DiffCare_{sel_period}_Pending.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f'dl_ll_{sel_period}')
        else:
            st.success(f"🎉 No pending patients for {sel_period} in the selected criteria!")

        # -------------------------------------------------------------
        # 🎯 NEW ADDITION (MIDDLE): DYNAMIC COHORT MATRIX
        # -------------------------------------------------------------
        import datetime
        from dateutil.relativedelta import relativedelta
        
        st.markdown("<br><hr style='border: 1.5px solid #2C3E50;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color: #2C3E50;'>📊 Consolidated Monthly Pending Matrix (Dynamic Cohorts)</h4>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 13px; color: #555; margin-bottom: 10px;'><i>Calculates pending patients dynamically based on their specific diagnosis month relative to the review month.</i></div>", unsafe_allow_html=True)
        
        cm1, cm2 = st.columns([1, 2])
        with cm1:
            mat_fac = st.selectbox("🏥 Facility Type", ["Public", "Private", "All"], key="mat_fac_mid")
        with cm2:
            # Default to current month
            today_date = datetime.date.today()
            ref_date = st.date_input("📅 Select Current Review Month (e.g., April 2026)", value=today_date, key="mat_ref_dt")

        # Start isolated matrix logic
        df_mat = df_dc_new.copy()
        
        # Facility Filter
        if mat_fac == "Public":
            df_mat = df_mat[df_mat['Facility_Type'].astype(str).str.upper().isin(['PUBLIC', 'PHI'])]
        elif mat_fac == "Private":
            df_mat = df_mat[df_mat['Facility_Type'].astype(str).str.upper().isin(['PRIVATE'])]

        # Map offset logic: Baseline looks at -1 Month, 1st Month looks at -2 Months, etc.
        mat_periods = [
            ('Baseline', 'BASELINE', 'Elig_BASELINE', 1),
            ('1 MONTH', '1ST MONTH|1 MONTH', 'Elig_1ST_MONTH', 2),
            ('2 MONTH', '2ND MONTH|2 MONTH', 'Elig_2ND_MONTH', 3),
            ('3 MONTH', '3RD MONTH|3 MONTH', 'Elig_3RD_MONTH', 4),
            ('4 MONTH', '4TH MONTH|4 MONTH', 'Elig_4TH_MONTH', 5),
            ('5 MONTH', '5TH MONTH|5 MONTH', 'Elig_5TH_MONTH', 6),
            ('6 MONTH', '6TH MONTH|6 MONTH', 'Elig_6TH_MONTH', 7)
        ]
        
        zones_list = ['SOUTH', 'NORTH', 'EAST', 'WEST', 'CENTRAL', 'NORTH WEST', 'SOUTH WEST']
        
        def get_zone_mat(z):
            raw_z = str(z).upper().replace("ZONE", "").strip()
            for valid_z in zones_list:
                if valid_z in raw_z: return valid_z
            return "AMC"
        
        df_mat['Mat_Zone'] = df_mat['ZONE'].apply(get_zone_mat)
        
        mat_rows = []
        for z in zones_list:
            z_df = df_mat[df_mat['Mat_Zone'] == z]
            row = {'ZONE': z}
            
            for label, rx, elig_col, m_offset in mat_periods:
                # 🎯 The True Cohort Logic
                target_start = ref_date.replace(day=1) - relativedelta(months=m_offset)
                target_end = (target_start + relativedelta(months=1)) - datetime.timedelta(days=1)
                
                # Filter down to the exact diagnosis month for this specific period
                z_cohort = z_df[pd.to_datetime(z_df.get('Diagnosis Date'), errors='coerce').dt.date.between(target_start, target_end)]
                
                is_elig = z_cohort[elig_col].fillna('').astype(str).str.upper().str.contains("ELIG") & ~z_cohort[elig_col].fillna('').astype(str).str.upper().str.contains("NOT")
                elig_cnt = is_elig.sum()
                
                due = z_cohort['Due_Status'].fillna('').astype(str).str.upper()
                not_comp = ~due.str.contains("COMPLETED", na=False)
                is_pending = is_elig & not_comp & due.str.contains(rx, na=False)
                pend_cnt = is_pending.sum()
                
                pct = round((pend_cnt/elig_cnt*100) if elig_cnt>0 else 0)
                
                row[f'Ep_{label}'] = elig_cnt
                row[f'{label}'] = pend_cnt
                row[f'% {label}'] = f"{pct}%"
            mat_rows.append(row)
            
        # AMC Row
        amc_row = {'ZONE': 'AMC'}
        for label, rx, elig_col, m_offset in mat_periods:
            target_start = ref_date.replace(day=1) - relativedelta(months=m_offset)
            target_end = (target_start + relativedelta(months=1)) - datetime.timedelta(days=1)
            
            amc_cohort = df_mat[pd.to_datetime(df_mat.get('Diagnosis Date'), errors='coerce').dt.date.between(target_start, target_end)]
            
            is_elig = amc_cohort[elig_col].fillna('').astype(str).str.upper().str.contains("ELIG") & ~amc_cohort[elig_col].fillna('').astype(str).str.upper().str.contains("NOT")
            elig_cnt = is_elig.sum()
            
            due = amc_cohort['Due_Status'].fillna('').astype(str).str.upper()
            not_comp = ~due.str.contains("COMPLETED", na=False)
            is_pending = is_elig & not_comp & due.str.contains(rx, na=False)
            pend_cnt = is_pending.sum()
            
            pct = round((pend_cnt/elig_cnt*100) if elig_cnt>0 else 0)
            
            amc_row[f'Ep_{label}'] = elig_cnt
            amc_row[f'{label}'] = pend_cnt
            amc_row[f'% {label}'] = f"{pct}%"
            
        mat_rows.append(amc_row)
        
        df_matrix_final = pd.DataFrame(mat_rows)
        
        # Rename Ep_ columns uniquely but display as 'Episode ID'
        rename_dict = {}
        for i, (label, _, _, _) in enumerate(mat_periods):
            rename_dict[f'Ep_{label}'] = "Episode ID" + (" " * i)
        df_matrix_final = df_matrix_final.rename(columns=rename_dict)
        
        # Styling Engine for Matrix
        def style_matrix(styler):
            styler.set_properties(**{'text-align': 'center'})
            styler.set_properties(subset=['ZONE'], **{'text-align': 'left', 'font-weight': 'bold', 'background-color': '#f8f9fa'})
            
            # Apply color strictly to the % columns
            for label, _, _, _ in mat_periods:
                col_name = f'% {label}'
                def color_rule(val):
                    try:
                        v = float(val.replace('%', '').strip())
                        if v >= 10: return 'background-color: #F1948A; color: #721c24; font-weight: bold;' # Red
                        elif v >= 5: return 'background-color: #F9E79F; color: #856404; font-weight: bold;' # Yellow
                        else: return 'background-color: #ABEBC6; color: #155724; font-weight: bold;' # Green
                    except:
                        return ''
                styler.map(color_rule, subset=[col_name])
            return styler
        
        st.dataframe(df_matrix_final.style.pipe(style_matrix), use_container_width=True, hide_index=True)

        # -------------------------------------------------------------
        # 🎯 🔄 DIFF CARE COMPARISON ENGINE (BOTTOM)
        # -------------------------------------------------------------
        st.markdown("<br><hr>", unsafe_allow_html=True)
        st.markdown("<h4 style='color: #E67E22;'>🔄 Diff Care Comparison Engine (Old vs New Sheet)</h4>", unsafe_allow_html=True)
        
        cc1, cc2, cc3 = st.columns(3)
        df_dc_comp_new = df_dc_new.copy()
        df_dc_comp_old = df_dc_old.copy()
        
        with cc1:
            comp_zones = st.multiselect("Filter Zone (Comparison)", sorted([x for x in df_dc_comp_new['ZONE'].unique() if pd.notna(x) and x!=""]), key='dc_comp_zone')
            if comp_zones:
                df_dc_comp_new = df_dc_comp_new[df_dc_comp_new['ZONE'].isin(comp_zones)]
                df_dc_comp_old = df_dc_comp_old[df_dc_comp_old['ZONE'].isin(comp_zones)]
                
        with cc2:
            # 🎯 DEPENDENT FILTER
            tu_opts_comp = sorted([x for x in df_dc_comp_new['TB Unit'].unique() if pd.notna(x) and x!=""])
            comp_tus = st.multiselect("Filter TB Unit (Comparison)", tu_opts_comp, key='dc_comp_tu')
            if comp_tus:
                df_dc_comp_new = df_dc_comp_new[df_dc_comp_new['TB Unit'].isin(comp_tus)]
                df_dc_comp_old = df_dc_comp_old[df_dc_comp_old['TB Unit'].isin(comp_tus)]
                
        with cc3:
            comp_dates = st.date_input("Select Diagnosis Date Range", value=[], key="dc_comp_dates")
            
        run_comp = st.button("🚀 Generate Comparison Matrix", use_container_width=True)

        def parse_comp_date(dt_series):
            return pd.to_datetime(dt_series, format='%d-%m-%Y', errors='coerce').combine_first(pd.to_datetime(dt_series, errors='coerce'))

        if run_comp:
            if len(comp_dates) != 2:
                st.error("⚠️ Please select a valid Start and End Date for comparison.")
            else:
                with st.spinner("Analyzing Old and New Diff Care Sheets..."):
                    s_ts = pd.Timestamp(comp_dates[0])
                    e_ts = pd.Timestamp(comp_dates[1])
                    
                    new_dates = parse_comp_date(df_dc_comp_new.get('Diagnosis Date'))
                    old_dates = parse_comp_date(df_dc_comp_old.get('Diagnosis Date'))
                    
                    df_dc_comp_new = df_dc_comp_new[new_dates.notna() & new_dates.dt.date.between(s_ts.date(), e_ts.date())]
                    df_dc_comp_old = df_dc_comp_old[old_dates.notna() & old_dates.dt.date.between(s_ts.date(), e_ts.date())]

                    def get_dc_pend_dict(df):
                        pend = {}
                        if df.empty: return pend
                        for _, r in df.iterrows():
                            eid = str(r['Episode ID']).strip().upper()
                            due = str(r.get('Due_Status', '')).upper()
                            if "COMPLETED" in due:
                                pend[eid] = []
                                continue
                            cur_p = []
                            for p_name, p_reg in periods_map.items():
                                p_rx = p_reg[0] 
                                if re.search(p_rx, due): cur_p.append(p_name)
                            pend[eid] = cur_p
                        return pend

                    old_dict = get_dc_pend_dict(df_dc_comp_old)
                    new_dict = get_dc_pend_dict(df_dc_comp_new)
                    
                    all_comp_ids = set(list(old_dict.keys()) + list(new_dict.keys()))
                    dc_comp_rows = []
                    
                    for eid in all_comp_ids:
                        if eid in ["", "NAN", "NONE"]: continue
                        po = old_dict.get(eid, [])
                        pn = new_dict.get(eid, [])
                        row = {'Episode ID': eid}
                        has_act = False
                        
                        for p_name in list(periods_map.keys()):
                            in_old = p_name in po
                            in_new = p_name in pn
                            
                            if in_old and in_new: row[p_name] = "🟡 PERSISTENT"; has_act = True
                            elif not in_old and in_new: row[p_name] = "🔴 NEW"; has_act = True
                            elif in_old and not in_new: row[p_name] = "🟢 RESOLVED"; has_act = True
                            else: row[p_name] = ""
                            
                        if has_act:
                            r_new = df_dc_comp_new[df_dc_comp_new['Episode ID'] == eid]
                            r_old = df_dc_comp_old[df_dc_comp_old['Episode ID'] == eid]
                            base = r_new.iloc[0] if not r_new.empty else r_old.iloc[0]
                            row['ZONE'] = base.get('ZONE', '')
                            row['TB Unit'] = base.get('TB Unit', '')
                            row['PHI'] = base.get('PHI', '')
                            row['Patient Name'] = base.get('Patient Name', '')
                            row['Facility Type'] = base.get('Facility_Type', '')
                            row['Diagnosis Date'] = base.get('Diagnosis Date', '')
                            dc_comp_rows.append(row)
                            
                    df_final_comp = pd.DataFrame(dc_comp_rows)
                    
                    if not df_final_comp.empty:
                        front = ['ZONE', 'TB Unit', 'PHI', 'Episode ID', 'Patient Name', 'Facility Type', 'Diagnosis Date']
                        other = [c for c in df_final_comp.columns if c not in front]
                        df_final_comp = df_final_comp[front + other]
                        
                        st.success(f"✅ Comparison Generated Successfully for {comp_dates[0].strftime('%d-%b-%Y')} to {comp_dates[1].strftime('%d-%b-%Y')}!")
                        st.dataframe(df_final_comp, use_container_width=True, hide_index=True)
                        st.download_button("📥 Download Comparison Matrix", convert_df_to_excel(df_final_comp, "DC_Comparison"), f"DiffCare_Comparison_{comp_dates[0]}_to_{comp_dates[1]}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key='dl_dc_comp')
                    else:
                        st.info(f"👍 No differences (🔴 NEW or 🟢 RESOLVED) found between Old and New data for {comp_dates[0].strftime('%d-%b-%Y')} to {comp_dates[1].strftime('%d-%b-%Y')}.")
# ==========================================
# 🟢 TAB 6: STAFF DIRECTORY (HR COMMAND CENTER - MNC ENTERPRISE EDITION)
# ==========================================
with tab6:
    st.markdown("<h3 style='text-align: center; color: #1e293b; font-weight: 800; font-family: system-ui;'>👥 AMC NTEP Staff Directory</h3>", unsafe_allow_html=True)
    
    @st.cache_data(ttl=600)
    def load_staff_directory():
        import re
        base_url = "https://docs.google.com/spreadsheets/d/1uFaHWm7spYKfpe-yrKhe7SC6GafEFM41w45_TnJ1Miw/export?format=csv&gid="
        
        configs = [
            {"name": "MO-SUPERVISOR", "gid": "1725576011", "name_col": "NAME", "zone_col": "ZONE", "tu_col": None},
            {"name": "MO-MEDICAL COLLEGE", "gid": "1072071070", "name_col": "NAME", "zone_col": None, "tu_col": "TU"},
            {"name": "STS", "gid": "1743236661", "name_col": "NAME", "zone_col": "ZONE", "tu_col": "TB UNIT"},
            {"name": "STLS", "gid": "450506055", "name_col": "NAME", "zone_col": "ZONE", "tu_col": "TB UNIT"},
            {"name": "TBHV", "gid": "1273132313", "name_col": "TBHV", "zone_col": None, "tu_col": "TU"},
        ]
        
        all_staff = []
        for cfg in configs:
            try:
                df_raw = pd.read_csv(base_url + cfg["gid"])
                
                # 🎯 DYNAMIC HEADER DETECTION
                h_idx = -1
                if str(cfg["name_col"]).upper() in df_raw.columns.astype(str).str.strip().str.upper():
                    df_s = df_raw.copy()
                    df_s.columns = df_s.columns.astype(str).str.strip().str.upper()
                else:
                    for i in range(5):
                        vals = [str(v).upper().strip() for v in df_raw.iloc[i].values]
                        if str(cfg["name_col"]).upper() in vals:
                            h_idx = i; break
                    if h_idx != -1:
                        df_s = df_raw.iloc[h_idx+1:].copy()
                        df_s.columns = df_raw.iloc[h_idx].astype(str).str.strip().str.upper()
                    else:
                        df_s = df_raw.copy()
                        df_s.columns = df_s.columns.astype(str).str.strip().str.upper()

                df_clean = pd.DataFrame()
                
                name_c = str(cfg["name_col"]).upper()
                df_clean['NAME'] = df_s[name_c] if name_c in df_s.columns else ""
                
                zone_c = str(cfg["zone_col"]).upper()
                df_clean['RAW_ZONE'] = df_s[zone_c] if zone_c in df_s.columns else ""
                
                tu_c = str(cfg["tu_col"]).upper()
                df_clean['TB_UNIT'] = df_s[tu_c] if tu_c in df_s.columns else "N/A"
                
                df_clean['RAW_ZONE'] = df_clean['RAW_ZONE'].replace(["", "NAN", "NONE", "NaN", pd.NA], None).ffill()
                df_clean['TB_UNIT'] = df_clean['TB_UNIT'].replace(["", "NAN", "NONE", "NaN", pd.NA], None).ffill()
                
                contact_col = next((c for c in df_s.columns if "CONTACT" in c or "CONTECT" in c or "MOBILE" in c), None)
                df_clean['CONTACT NO'] = df_s[contact_col] if contact_col else "N/A"
                
                email_col = next((c for c in df_s.columns if "EMAIL" in c), None)
                df_clean['EMAIL'] = df_s[email_col] if email_col else "N/A"
                
                df_clean['SOURCE_SHEET'] = cfg["name"]
                all_staff.append(df_clean)
            except Exception as e:
                pass 
                
        if all_staff:
            final_df = pd.concat(all_staff, ignore_index=True)
            final_df = final_df.dropna(subset=['NAME'])
            final_df = final_df[final_df['NAME'].astype(str).str.strip() != ""]
            final_df = final_df[~final_df['NAME'].astype(str).str.upper().isin(["NAN", "NONE"])]
            
            # 🎯 STRICT ZONE MAPPING
            def assign_strict_zone(row):
                raw_z = str(row['RAW_ZONE']).upper().replace("ZONE", "").strip()
                tu = str(row['TB_UNIT']).upper().strip()
                search_string = f"{raw_z} {tu}"
                
                if any(x in search_string for x in ["SOUTH WEST", "JODHPUR", "SARKHEJ", "VEJALPUR", "BOPAL"]): return "South West"
                if any(x in search_string for x in ["NORTH WEST", "SOLA", "GHATLODIA", "CHANDLODIYA", "THALTEJ", "BODAKDEV", "GOTA"]): return "North West"
                if any(x in search_string for x in ["WEST", "VASNA", "PALDI", "SABARMATI", "NAVRANGPURA", "STADIUM", "VADAJ"]): return "West"
                if any(x in search_string for x in ["SOUTH", "DANILIMDA", "VATVA", "MANINAGAR", "ISANPUR", "BEHRAMPURA"]): return "South"
                if any(x in search_string for x in ["CENTRAL", "ASARVA", "SHAHPUR", "JAMALPUR", "DARIYAPUR", "CIVIL"]): return "Central"
                if any(x in search_string for x in ["EAST", "AMRAIWADI", "BHAIPURA", "VASTRAL", "GOMTIPUR", "VIRATNAGAR"]): return "East"
                if any(x in search_string for x in ["NORTH", "BAPUNAGAR", "SAIJPUR", "NARODA", "RAKHIAL", "INDIA COLONY"]): return "North"
                return "AMC"
                
            final_df['ZONE'] = final_df.apply(assign_strict_zone, axis=1)
            
            final_df['TB_UNIT'] = final_df['TB_UNIT'].astype(str).str.upper()
            final_df['TB_UNIT'] = final_df['TB_UNIT'].str.replace(r'I/C\s*', '', regex=True)
            final_df['TB_UNIT'] = final_df['TB_UNIT'].str.replace("/", ", ").str.replace("  ", " ").str.title()
            final_df['TB_UNIT'] = final_df['TB_UNIT'].replace(["", "Nan", "None", "N/A"], "N/A")
            
            # ==========================================
            # 🎯 CLEAN DESIGNATIONS & FILTERS
            # ==========================================
            final_df['DESIGNATION'] = ""
            final_df['FILTER_DESIG'] = ""
            final_df['EXTRA_CHARGE'] = ""

            final_df.loc[final_df['SOURCE_SHEET'] == 'MO-SUPERVISOR', 'DESIGNATION'] = "MEDICAL OFFICER SUPERVISOR"
            final_df.loc[final_df['SOURCE_SHEET'] == 'MO-SUPERVISOR', 'FILTER_DESIG'] = "MO-Supervisor"
            
            final_df.loc[final_df['SOURCE_SHEET'] == 'MO-MEDICAL COLLEGE', 'DESIGNATION'] = "MEDICAL OFFICER"
            final_df.loc[final_df['SOURCE_SHEET'] == 'MO-MEDICAL COLLEGE', 'FILTER_DESIG'] = "Medical Officer"
            
            final_df.loc[final_df['SOURCE_SHEET'] == 'STLS', 'DESIGNATION'] = "SENIOR TB LABORATORY SUPERVISOR (STLS)"
            final_df.loc[final_df['SOURCE_SHEET'] == 'STLS', 'FILTER_DESIG'] = "STLS"
            
            final_df.loc[final_df['SOURCE_SHEET'] == 'STS', 'DESIGNATION'] = "SENIOR TREATMENT SUPERVISOR (STS)"
            final_df.loc[final_df['SOURCE_SHEET'] == 'STS', 'FILTER_DESIG'] = "STS"
            
            final_df.loc[final_df['SOURCE_SHEET'] == 'TBHV', 'DESIGNATION'] = "TB HEALTH VISITOR (TBHV)"
            final_df.loc[final_df['SOURCE_SHEET'] == 'TBHV', 'FILTER_DESIG'] = "TBHV"

            # Custom Overrides for Zonal Heads
            chirag_mask = final_df['NAME'].astype(str).str.upper().str.contains("CHIRAG") & (final_df['SOURCE_SHEET'] == "MO-SUPERVISOR")
            final_df.loc[chirag_mask, 'EXTRA_CHARGE'] = "(Medical Officer DTC)"
            
            ushma_mask = final_df['NAME'].astype(str).str.upper().str.contains("USHMA") & (final_df['SOURCE_SHEET'] == "MO-SUPERVISOR")
            final_df.loc[ushma_mask, 'EXTRA_CHARGE'] = "(Also monitoring East & North Zone)"
            
            # 🎯 Falguni S. Panchal Hardcode Override
            falguni_mask = final_df['NAME'].astype(str).str.upper().str.contains("FALGUNI")
            final_df.loc[falguni_mask, 'ZONE'] = "HEAD OFFICE"
            final_df.loc[falguni_mask, 'TB_UNIT'] = "Arogya Bhavan"
            
            # DYNAMIC REPORTING MAPPING
            mo_sups = final_df[final_df['SOURCE_SHEET'] == "MO-SUPERVISOR"]
            zone_heads = {}
            for _, r in mo_sups.iterrows():
                z = r['ZONE']
                n = str(r['NAME']).title()
                if z not in zone_heads: zone_heads[z] = n
                elif n not in zone_heads[z]: zone_heads[z] += f" & {n}"

            def assign_hierarchy(sheet_name):
                if sheet_name == "MO-SUPERVISOR": return 1
                if sheet_name == "MO-MEDICAL COLLEGE": return 2
                if sheet_name == "STLS": return 3 
                if sheet_name == "STS": return 4
                if sheet_name == "TBHV": return 5
                return 99

            def assign_reporting(row):
                sheet = row['SOURCE_SHEET']
                z = row['ZONE']
                name = str(row['NAME']).upper()
                z_head = zone_heads.get(z, "Zonal MO-Supervisor")
                
                # Falguni Panchal Override
                if "FALGUNI" in name: return "City TB Officer & MO-DTC"
                
                if sheet == "MO-SUPERVISOR": return "City TB Officer (Dr. S. K. Patel)"
                elif sheet == "MO-MEDICAL COLLEGE": return f"City TB Officer & {z_head}"
                else: return z_head

            final_df['HIERARCHY'] = final_df['SOURCE_SHEET'].apply(assign_hierarchy)
            final_df['REPORTS_TO'] = final_df.apply(assign_reporting, axis=1)
            
            # 🎯 CRITICAL BUG FIX: Force fill NaN values BEFORE grouping so STLS don't get deleted
            final_df = final_df.fillna("N/A")
            
            # 🎯 IDENTITY MERGER
            def merge_tus(tu_series):
                tus = set()
                for tu_val in tu_series:
                    if str(tu_val).upper() not in ["N/A", "NAN", "NONE"]:
                        for item in str(tu_val).split(','):
                            if item.strip(): tus.add(item.strip().title())
                return ", ".join(sorted(tus)) if tus else "N/A"
            
            final_df = final_df.groupby(['NAME', 'DESIGNATION', 'FILTER_DESIG', 'EXTRA_CHARGE', 'CONTACT NO', 'EMAIL', 'HIERARCHY', 'REPORTS_TO']).agg({
                'ZONE': lambda x: ' & '.join(sorted(set(x))),
                'TB_UNIT': merge_tus,
                'SOURCE_SHEET': 'first'
            }).reset_index()
            
            final_df = final_df.sort_values(by=['HIERARCHY', 'ZONE', 'NAME']).reset_index(drop=True)
            return final_df
        return pd.DataFrame()

    with st.spinner("Loading Enterprise HR Data..."):
        df_staff = load_staff_directory()
    
    if df_staff.empty:
        st.warning("⚠️ Staff Directory data could not be loaded. Please check the Google Sheet link and GIDs.")
    else:
        if st.session_state.role == "ZONE":
            df_staff = df_staff[df_staff['ZONE'].astype(str).str.upper().str.contains(st.session_state.target.upper(), na=False)]
        
        st.markdown("""
        <style>
        div[data-testid="stTextInput"] input { border-radius: 20px; padding: 10px 20px; border: 1px solid #cbd5e1; }
        </style>
        """, unsafe_allow_html=True)
        
        sc1, sc2, sc3, sc4 = st.columns([2, 1, 1, 1])
        with sc1: search_q = st.text_input("🔍 Search Name, Number...", "")
        
        all_zones_raw = []
        for z_str in df_staff['ZONE']:
            for z in str(z_str).split(' & '): all_zones_raw.append(z.strip())
        zones = ["All Zones"] + sorted(list(set([z for z in all_zones_raw if z not in ["N/A", "NAN", ""]])))
        with sc2: sel_zone = st.selectbox("🏢 Filter Zone", zones)
        
        raw_tus = df_staff[df_staff['ZONE'].str.contains(sel_zone, case=False, na=False)]['TB_UNIT'] if sel_zone != "All Zones" else df_staff['TB_UNIT']
        all_tu_items = set()
        for tu_str in raw_tus.dropna():
            for t in str(tu_str).split(','):
                cleaned_t = t.strip()
                if cleaned_t and cleaned_t.upper() not in ["N/A", "NAN", "NONE"]: all_tu_items.add(cleaned_t)
                    
        with sc3:
            tus = ["All TB Units"] + sorted(list(all_tu_items))
            sel_tu = st.selectbox("🏥 Filter TB Unit", tus)
            
        with sc4:
            # Clean Designation Dropdown Menu
            desigs = ["All Designations", "MO-Supervisor", "Medical Officer", "STLS", "STS", "TBHV"]
            sel_desig = st.selectbox("👨‍⚕️ Designation", desigs)
        
        # APPLY FILTERS
        df_display = df_staff.copy()
        if search_q: df_display = df_display[df_display.apply(lambda row: row.astype(str).str.contains(search_q, case=False, na=False).any(), axis=1)]
        if sel_zone != "All Zones": df_display = df_display[df_display['ZONE'].str.contains(sel_zone, case=False, na=False)]
        if sel_tu != "All TB Units": df_display = df_display[df_display['TB_UNIT'].astype(str).str.contains(sel_tu, case=False, na=False)]
        if sel_desig != "All Designations": df_display = df_display[df_display['FILTER_DESIG'] == sel_desig]
        
        st.markdown(f"<div style='color: #64748b; margin-bottom: 20px; font-weight: 600; font-size: 14px;'>Found {len(df_display)} Profiles</div>", unsafe_allow_html=True)
        
        # 📇 MNC CORPORATE DIGITAL BUSINESS CARDS
        cols = st.columns(3)
        for idx, row in df_display.iterrows():
            name = str(row.get('NAME', 'N/A')).title()
            desig = str(row.get('DESIGNATION', 'N/A')).upper()
            extra = str(row.get('EXTRA_CHARGE', ''))
            zone = str(row.get('ZONE', 'N/A'))
            tu = str(row.get('TB_UNIT', 'N/A'))
            phone = str(row.get('CONTACT NO', 'N/A')).strip().replace('.0', '')
            email = str(row.get('EMAIL', 'N/A')).strip()
            reports_to = str(row.get('REPORTS_TO', 'N/A'))
            h_level = row.get('HIERARCHY', 99)
            
            if phone in ["N/A", "NAN", "NONE", ""]: phone = "Not Provided"
            if email in ["N/A", "NAN", "NONE", ""]: email = "Not Provided"
            
            clean_phone = "".join(filter(str.isdigit, phone))
            wa_link = f"https://wa.me/91{clean_phone}" if len(clean_phone) >= 10 else "#"
            call_link = f"tel:+91{clean_phone}" if len(clean_phone) >= 10 else "#"
            mail_link = f"mailto:{email}" if "@" in email else "#"
            
            border_color = "#e11d48" if h_level == 1 else "#f59e0b" if h_level == 2 else "#10b981" if h_level == 3 else "#0ea5e9" if h_level == 4 else "#8b5cf6"
            badge = "👑 ZONAL HEAD" if h_level == 1 else "⚕️ MEDICAL OFFICER" if h_level == 2 else "🧪 STLS" if h_level == 3 else "📋 STS" if h_level == 4 else "🩺 TBHV"
            
            if zone.upper() == "HEAD OFFICE":
                location_html = f"<b>{zone}</b>"
            else:
                location_html = f"<b>{zone} Zone</b>"
                
            if h_level > 1 and tu.upper() not in ["N/A", "NAN", "NONE"]:
                location_html += f" <span style='color:#cbd5e1;'>|</span> 🏥 {tu}"
                
            extra_html = f"<span style='color:#e11d48; display:block; margin-top:2px;'>{extra}</span>" if extra else ""
            
            card_html = f"""<div style="background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.04); margin-bottom: 20px; border-top: 5px solid {border_color}; font-family: system-ui, -apple-system, sans-serif; transition: transform 0.2s;">
<div style="margin-bottom: 12px;"><span style="background-color: #f1f5f9; color: #475569; padding: 4px 10px; border-radius: 12px; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;">{badge}</span></div>
<div style="font-size: 18px; font-weight: 800; color: #0f172a; margin-bottom: 4px; line-height: 1.2;">{name}</div>
<div style="font-size: 11px; color: #64748b; font-weight: 700; margin-bottom: 12px; letter-spacing: 0.3px;">{desig} {extra_html}</div>
<div style="font-size: 13px; color: #334155; margin-bottom: 6px; line-height: 1.4;">📍 {location_html}</div>
<div style="font-size: 13px; color: #334155; margin-bottom: 12px;">📞 <b>{phone}</b></div>
<div style="background-color: #f8fafc; padding: 10px; border-radius: 8px; margin-bottom: 15px; border-left: 3px solid #cbd5e1;">
<div style="font-size: 11px; color: #64748b; margin-bottom: 2px; text-transform: uppercase; font-weight: 700;">Reports To</div>
<div style="font-size: 12px; color: #0f172a; font-weight: 600;">{reports_to}</div>
</div>
<div style="display: flex; gap: 8px; justify-content: space-between;">"""
            if len(clean_phone) >= 10:
                card_html += f"""<a href="{call_link}" style="text-decoration: none; background-color: #f1f5f9; color: #334155; padding: 8px 0; border-radius: 20px; font-size: 12px; font-weight: 700; flex: 1; text-align: center; border: 1px solid #e2e8f0; transition: 0.2s;">📞 Call</a><a href="{wa_link}" target="_blank" style="text-decoration: none; background-color: #25D366; color: white; padding: 8px 0; border-radius: 20px; font-size: 12px; font-weight: 700; flex: 1; text-align: center; box-shadow: 0 2px 4px rgba(37,211,102,0.2);">💬 WhatsApp</a>"""
            if "@" in email:
                card_html += f"""<a href="{mail_link}" target="_blank" style="text-decoration: none; background-color: #3b82f6; color: white; padding: 8px 0; border-radius: 20px; font-size: 12px; font-weight: 700; flex: 1; text-align: center; box-shadow: 0 2px 4px rgba(59,130,246,0.2);">✉️ Email</a>"""
            card_html += "</div></div>"
            
            with cols[idx % 3]:
                st.markdown(card_html, unsafe_allow_html=True)
