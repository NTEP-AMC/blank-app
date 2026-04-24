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
            df = df.iloc[1:].reset_index(drop=True) 

            def cx_col(col_let):
                num = 0
                for c in col_let.upper(): num = num * 26 + (ord(c) - ord('A') + 1)
                return num - 1

            max_col = cx_col('DD')
            if len(df.columns) <= max_col:
                for i in range(len(df.columns), max_col + 1): df[i] = ""

            ci_idx, tu_idx, phi_idx = cx_col('CI'), cx_col('A'), cx_col('C')
            id_idx, name_idx, zone_idx = cx_col('G'), cx_col('H'), cx_col('AR')
            diag_idx, init_idx, out_idx = cx_col('CJ'), cx_col('CK'), cx_col('CL')
            hf_idx, case_idx, site_idx, out_col_idx = cx_col('B'), cx_col('Z'), cx_col('AA'), cx_col('AD')
            cx_base, cy_1m, cz_2m, da_3m, db_4m, dc_5m, dd_6m = cx_col('CX'), cx_col('CY'), cx_col('CZ'), cx_col('DA'), cx_col('DB'), cx_col('DC'), cx_col('DD')

            diff_data = []
            for _, row in df.iterrows():
                elig_base = str(row.iloc[cx_base]).strip().upper() if cx_base < len(row) else ""
                elig_1m = str(row.iloc[cy_1m]).strip().upper() if cy_1m < len(row) else ""
                elig_2m = str(row.iloc[cz_2m]).strip().upper() if cz_2m < len(row) else ""
                elig_3m = str(row.iloc[da_3m]).strip().upper() if da_3m < len(row) else ""
                elig_4m = str(row.iloc[db_4m]).strip().upper() if db_4m < len(row) else ""
                elig_5m = str(row.iloc[dc_5m]).strip().upper() if dc_5m < len(row) else ""
                elig_6m = str(row.iloc[dd_6m]).strip().upper() if dd_6m < len(row) else ""

                is_elig = False
                for val in [elig_base, elig_1m, elig_2m, elig_3m, elig_4m, elig_5m, elig_6m]:
                    if "ELIG" in val and "NOT" not in val:
                        is_elig = True; break
                        
                if is_elig:
                    tu = str(row.iloc[tu_idx]).upper().replace("-", "").strip() if tu_idx < len(row) else ""
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

                    phi = str(row.iloc[phi_idx]).strip().upper() if phi_idx < len(row) else ""
                    zone = str(row.iloc[zone_idx]).strip().upper() if zone_idx < len(row) else "N/A"
                    if zone in ["", "NAN", "NONE", "NULL", "N/A"]: zone = 'MAPPING NOT DONE'
                    
                    due_val = str(row.iloc[ci_idx]).strip().upper() if ci_idx < len(row) else ""
                    eid = str(row.iloc[id_idx]).strip().upper() if id_idx < len(row) else ""
                    pname = str(row.iloc[name_idx]).strip().upper() if name_idx < len(row) else ""
                    
                    d_val = str(row.iloc[diag_idx]).strip() if diag_idx < len(row) else ""
                    i_val = str(row.iloc[init_idx]).strip() if init_idx < len(row) else ""
                    o_val = str(row.iloc[out_idx]).strip() if out_idx < len(row) else ""
                    
                    hf_val = str(row.iloc[hf_idx]).strip().upper() if hf_idx < len(row) else ""
                    case_val = str(row.iloc[case_idx]).strip().upper() if case_idx < len(row) else ""
                    site_val = str(row.iloc[site_idx]).strip().upper() if site_idx < len(row) else ""
                    out_col_val = str(row.iloc[out_col_idx]).strip().upper() if out_col_idx < len(row) else ""

                    diff_data.append({
                        'ZONE': zone, 'TB Unit': tu, 'PHI': phi, 'Episode ID': eid, 'Patient Name': pname,
                        'Due_Status': due_val, 'Diagnosis Date': d_val, 'Initiation Date': i_val, 'Outcome Date': o_val,
                        'Facility_Type': hf_val, 'Type_of_Case': case_val, 
                        'Site_of_TBDisease': site_val, 'Treatment_Outcome': out_col_val,
                        'Elig_BASELINE': elig_base, 'Elig_1ST_MONTH': elig_1m, 'Elig_2ND_MONTH': elig_2m,
                        'Elig_3RD_MONTH': elig_3m, 'Elig_4TH_MONTH': elig_4m, 'Elig_5TH_MONTH': elig_5m, 'Elig_6TH_MONTH': elig_6m
                    })

            df_final = pd.DataFrame(diff_data)
            if not df_final.empty:
                for c in ['Diagnosis Date', 'Initiation Date', 'Outcome Date']:
                    df_final[c] = pd.to_datetime(df_final[c], errors='coerce')
            return df_final

        url_new = "https://docs.google.com/spreadsheets/d/1hkJBnJOuxcVu233f6e2_0cOE-BM7bdDOyHuzrlGogMU/export?format=csv&gid=1152778583"
        url_old = "https://docs.google.com/spreadsheets/d/1zdf96eisZHzdk5ECFSI7eeOtNQoOXk3QRUUROtIZQmc/export?format=csv&gid=1152778583"
        return fetch_sheet(url_new), fetch_sheet(url_old)
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame()

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
            # 🎯 DEPENDENT FILTER: TB Unit updates based on Zone
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
            # 🎯 DEPENDENT FILTER: PHI updates based on TB Unit
            s_phi = clean_selection(st.multiselect("Filter PHI", get_options_with_counts(df_disp, 'PHI', 'tab1'), key='phi1'))
            if s_phi: df_disp = df_disp[df_disp['PHI'].isin(s_phi)]
            
            inds = ["Outcome", "UDST", "Not Put On", "SLPA", "Consent", "ADT", "RBS", "ART", "CPT", "HIV"]
            f_rep = st.multiselect("Report Type", inds, key='rep1')
            
        with c3:
            diag_dt = st.date_input("Diagnosis Date Range", value=[], key="d1")
            init_dt = st.date_input("Initiation Date Range", value=[], key="d2")
            out_dt = st.date_input("Outcome Date Range", value=[], key="d3")
            
        if len(diag_dt) == 2: df_disp = df_disp[pd.to_datetime(df_disp.get('Diagnosis Date'), errors='coerce').notna() & pd.to_datetime(df_disp.get('Diagnosis Date'), errors='coerce').dt.date.between(diag_dt[0], diag_dt[1])]
        if len(init_dt) == 2: df_disp = df_disp[pd.to_datetime(df_disp.get('Initiation Date'), errors='coerce').notna() & pd.to_datetime(df_disp.get('Initiation Date'), errors='coerce').dt.date.between(init_dt[0], init_dt[1])]
        if len(out_dt) == 2: df_disp = df_disp[pd.to_datetime(df_disp.get('Outcome Date'), errors='coerce').notna() & pd.to_datetime(df_disp.get('Outcome Date'), errors='coerce').dt.date.between(out_dt[0], out_dt[1])]
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
        excel_data1 = convert_df_to_excel(df_disp, "Master_Report")
        st.download_button("📥 Download Formatted Excel", excel_data1, "Master_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key='dl1')

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

        if len(diag_dt2) == 2: df_c = df_c[pd.to_datetime(df_c.get('Diagnosis Date'), errors='coerce').notna() & pd.to_datetime(df_c.get('Diagnosis Date'), errors='coerce').dt.date.between(diag_dt2[0], diag_dt2[1])]
        if len(init_dt2) == 2: df_c = df_c[pd.to_datetime(df_c.get('Initiation Date'), errors='coerce').notna() & pd.to_datetime(df_c.get('Initiation Date'), errors='coerce').dt.date.between(init_dt2[0], init_dt2[1])]
        if len(out_dt2) == 2: df_c = df_c[pd.to_datetime(df_c.get('Outcome Date'), errors='coerce').notna() & pd.to_datetime(df_c.get('Outcome Date'), errors='coerce').dt.date.between(out_dt2[0], out_dt2[1])]

    if s2_ind or s2_stat:
        mask = pd.Series(False, index=df_c.index)
        for ind in (s2_ind if s2_ind else [c for c in df_c.columns if c not in ignore_cols]):
            if ind in df_c.columns: mask = mask | df_c[ind].isin(s2_stat if s2_stat else ["🔴 NEW", "🟢 RESOLVED", "🟡 PERSISTENT"])
        df_c = df_c[mask]
        
    ind_cols_in_df = [c for c in df_c.columns if c not in ignore_cols]
    if ind_cols_in_df:
        new_c = (df_c[ind_cols_in_df] == "🔴 NEW").sum().sum()
        res_c = (df_c[ind_cols_in_df] == "🟢 RESOLVED").sum().sum()
        per_c = (df_c[ind_cols_in_df] == "🟡 PERSISTENT").sum().sum()
    else:
        new_c, res_c, per_c = 0, 0, 0
    
    st.markdown("##### 📈 Daily Action Status")
    cc1, cc2, cc3, cc4 = st.columns(4)
    with cc1: st.markdown(draw_card("TOTAL PENDENCY", new_c + per_c, "#1f618d", "📄"), unsafe_allow_html=True)
    with cc2: st.markdown(draw_card("🔴 NEW", new_c, "#E74C3C", "🚨"), unsafe_allow_html=True)
    with cc3: st.markdown(draw_card("🟡 PERSISTENT", per_c, "#F1C40F", "⏳"), unsafe_allow_html=True)
    with cc4: st.markdown(draw_card("🟢 RESOLVED", res_c, "#27AE60", "✅"), unsafe_allow_html=True)

    display_cols = [c for c in df_c.columns if c not in ['Diagnosis Date', 'Initiation Date', 'Outcome Date']]
    st.dataframe(df_c[display_cols], use_container_width=True, hide_index=True)
    
    if not df_c.empty:
        excel_data2 = convert_df_to_excel(df_c[display_cols], "Comparison_Matrix")
        st.download_button("📥 Download Formatted Excel", excel_data2, "Comparison_Matrix.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key='dl2')

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
    c_t3, _, _, _ = st.columns(4)
    with c_t3: st.markdown(draw_card("Total Active Patients", len(df_t3), "#16A085", "🏥"), unsafe_allow_html=True)

    t3_final_cols = [c for c in ['ZONE', 'TB Unit', 'PHI', 'Facility Type', 'Episode ID', 'Patient Name', 'Type of Case', 'TB_regimen', 'Diagnosis Date', 'Initiation Date', 'Outcome Date'] if c in df_t3.columns]
    st.dataframe(df_t3[t3_final_cols], use_container_width=True, hide_index=True)
    if not df_t3.empty:
        excel_data3 = convert_df_to_excel(df_t3[t3_final_cols], "Current_Patients")
        st.download_button("📥 Download Formatted Excel", excel_data3, "Current_Patients.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key='dl3')

# ==========================================
# 🟢 TAB 4: PPT GENERATOR (100% RESTORED)
# ==========================================
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
        if len(diag) == 2: mask &= pd.to_datetime(df.get('Diagnosis Date'), errors='coerce').dt.date.between(diag[0], diag[1])
        if len(init) == 2: mask &= pd.to_datetime(df.get('Initiation Date'), errors='coerce').dt.date.between(init[0], init[1])
        if len(out) == 2: mask &= pd.to_datetime(df.get('Outcome Date'), errors='coerce').dt.date.between(out[0], out[1])
        return mask

    def generate_smart_ppt(df, report_name):
        try:
            from pptx import Presentation
            from pptx.util import Inches, Pt
            from pptx.dml.color import RGBColor
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
            add_slide_table(f"{st.session_state.target} Zone - {sel_report} Pending (TU Wise)", tu_curr, tu_prev, 'TB Unit')
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
            add_slide_table(f"{st.session_state.target} - {sel_report} Pending", phi_curr, prev_df, 'PHI')

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
# 🟢 TAB 5: DIFFERENTIATED CARE (FINAL UI)
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
                
            with c2:
                # 🎯 DEPENDENT FILTER
                phi_opts = sorted([x for x in df_dc['PHI'].unique() if pd.notna(x) and x!=""])
                s6_phi = st.multiselect("PHI", phi_opts, key='phi6')
                if s6_phi: df_dc = df_dc[df_dc['PHI'].isin(s6_phi)]
                
                s6_hf = st.multiselect("Facility Type", sorted([x for x in df_dc['Facility_Type'].unique() if pd.notna(x) and x!=""]), key='hf6')
                if s6_hf: df_dc = df_dc[df_dc['Facility_Type'].isin(s6_hf)]
                
            with c3:
                comp_dates = st.date_input("Diagnosis Date Range", value=[], key="dc_main_dates")
                
        if len(comp_dates) == 2: df_dc = df_dc[pd.to_datetime(df_dc.get('Diagnosis Date'), errors='coerce').notna() & pd.to_datetime(df_dc.get('Diagnosis Date'), errors='coerce').dt.date.between(comp_dates[0], comp_dates[1])]

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
            
            # 🎯 Sorting Logic: 7 Zones -> MAPPING NOT DONE -> AMC TOTAL
            main_zones = ['CENTRAL', 'EAST', 'NORTH', 'NORTH WEST', 'SOUTH', 'SOUTH WEST', 'WEST']
            summary['sort_key'] = summary[group_col].apply(lambda x: main_zones.index(x) if x in main_zones else 998 if x == 'MAPPING NOT DONE' else 999)
            summary = summary.sort_values('sort_key').drop(columns=['sort_key'])
            
            total_row = pd.DataFrame({group_col: ['AMC TOTAL'], 'Total Patient': [total_patient], 'Eligible': [total_eligible], 'Completed': [total_completed], 'Pending': [total_pending], '% Completed': [round(total_pct, 1)]})
            return pd.concat([summary, total_row], ignore_index=True)

        summary_df = get_dynamic_summary(df_dc, g_col)
        
        main_zones = ['CENTRAL', 'EAST', 'NORTH', 'NORTH WEST', 'SOUTH', 'SOUTH WEST', 'WEST']
        
        # 🎯 7 MINI BOXES (With Dynamic Colors)
        if st.session_state.role == "ADMIN" and ('s6_z' not in locals() or len(s6_z) == 0):
            st.markdown(f"##### 🎯 {sel_period} - Zone Wise % Completed")
            cols7 = st.columns(7)
            for i, z in enumerate(main_zones):
                z_row = summary_df[summary_df[g_col] == z]
                pct_val = 0
                if not z_row.empty: pct_val = z_row['% Completed'].values[0]
                
                if pct_val >= 75: bg_c, t_c = "#d4edda", "#155724" # લીલો
                elif pct_val >= 50: bg_c, t_c = "#fff3cd", "#856404" # પીળો
                else: bg_c, t_c = "#f8d7da", "#721c24" # લાલ
                
                card_html = f"""<div style="background-color: {bg_c}; color: {t_c}; border-radius: 5px; padding: 6px 1px; margin-bottom: 10px; text-align: center; border: 1px solid rgba(0,0,0,0.1);"><div style="font-size: 10px; font-weight: bold; text-transform: uppercase;">{z}</div><div style="font-size: 16px; font-weight: 900; margin-top: 2px;">{pct_val}%</div></div>"""
                with cols7[i]: st.markdown(card_html, unsafe_allow_html=True)

        st.markdown(f"##### 📊 {sel_period} Summary ({g_col} Wise)")

        # 🎯 TARGETED COLORING ON TABLE (Only % Completed column for 7 zones)
        def apply_row_style(row):
            styles = [''] * len(row)
            if row[g_col] in main_zones:
                try:
                    val = float(str(row['% Completed']).replace('%', ''))
                    idx = list(row.index).index('% Completed')
                    if val >= 75: styles[idx] = 'background-color: #d4edda; color: #155724; font-weight: bold;'
                    elif val >= 50: styles[idx] = 'background-color: #fff3cd; color: #856404; font-weight: bold;'
                    else: styles[idx] = 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
                except: pass
            return styles

        sum_disp = summary_df.copy()
        sum_disp['% Completed'] = sum_disp['% Completed'].astype(str) + '%'
        
        styled_df = sum_disp.style.apply(apply_row_style, axis=1)
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
        # 🎯 🔄 DIFF CARE COMPARISON ENGINE (OLD VS NEW)
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
                    
                    new_dates = parse_comp_date(df_new_comp.get('Diagnosis Date'))
                    old_dates = parse_comp_date(df_old_comp.get('Diagnosis Date'))
                    
                    df_new_comp = df_new_comp[new_dates.notna() & new_dates.dt.date.between(s_ts.date(), e_ts.date())]
                    df_old_comp = df_old_comp[old_dates.notna() & old_dates.dt.date.between(s_ts.date(), e_ts.date())]

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

                    old_dict = get_dc_pend_dict(df_old_comp)
                    new_dict = get_dc_pend_dict(df_new_comp)
                    
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
                            r_new = df_new_comp[df_new_comp['Episode ID'] == eid]
                            r_old = df_old_comp[df_old_comp['Episode ID'] == eid]
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
