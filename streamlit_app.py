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
        m = pd.read_csv("Master_Line_List.csv")
        for c in ['Diagnosis Date', 'Initiation Date', 'Outcome Date']:
            if c in m.columns: m[c] = pd.to_datetime(m[c], errors='coerce') 
            
        c_mat = pd.read_csv("Comparison_Matrix.csv")
        if not c_mat.empty and not m.empty:
            dates_df = m[['Episode ID', 'Diagnosis Date', 'Initiation Date', 'Outcome Date']].drop_duplicates('Episode ID')
            c_mat = c_mat.merge(dates_df, on='Episode ID', how='left')

        curr = pd.read_csv("Current_TB_Patients.csv")
        t_df = pd.read_csv("Update_Timestamps.csv")
        
        out_df = pd.read_csv("Outcome_Cohort.csv")
        for c in ['Diagnosis Date', 'Initiation Date', 'Outcome Date']:
            if c in out_df.columns: out_df[c] = pd.to_datetime(out_df[c], errors='coerce') 
            
        return m, c_mat, curr, t_df, out_df
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# 🎯 TAB 6 LIVE FETCH (SMART MAPPING)
@st.cache_data(ttl=300) 
def load_diff_care_live():
    try:
        sheet_id = "1hkJBnJOuxcVu233f6e2_0cOE-BM7bdDOyHuzrlGogMU"
        gid = "1152778583"
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        df = pd.read_csv(url)

        header_map = {}
        for c in df.columns:
            cl = str(c).upper().strip()
            if "SPECTRUM_CURRENT_TBU" in cl: header_map['TB Unit'] = c
            elif "SPECTRUM_CURRENT_HF" in cl and "TYPE" not in cl: header_map['PHI'] = c
            elif "EPISODE_ID" in cl: header_map['Episode ID'] = c
            elif "FOLLOW UP DUE" in cl: header_map['Due_Status'] = c
            elif "DIAGNOSIS_DATE" in cl: header_map['Diagnosis Date'] = c
            elif "INITIATION_DATE" in cl: header_map['Initiation Date'] = c
            elif "OUTCOME DATE" in cl or "DATE_OF_TREATMENT_OUTCOME" in cl: header_map['Outcome Date'] = c
        
        zone_col = df.columns[43] if len(df.columns) > 43 else None # Column AR

        elig_cols = [c for c in df.columns if str(c).upper().strip() in ['BASELINE', '1 MONTH', '2 MONTH', '3 MONTH', '4 MONTH', '5 MONTH', '6 MONTH']]

        diff_data = []
        for _, row in df.iterrows():
            is_elig = False
            for c in elig_cols:
                val = str(row.get(c, '')).strip().upper()
                if "ELIG" in val and "NOT" not in val:
                    is_elig = True
                    break
            if is_elig:
                tu = str(row.get(header_map.get('TB Unit', ''), '')).upper().strip()
                phi = str(row.get(header_map.get('PHI', ''), '')).strip().upper()
                zone = str(row[zone_col]).strip().upper() if zone_col else "N/A"
                due_val = str(row.get(header_map.get('Due_Status', ''), '')).strip().upper()
                eid = str(row.get(header_map.get('Episode ID', ''), '')).strip().upper()
                d_val = str(row.get(header_map.get('Diagnosis Date', ''), '')).strip()
                i_val = str(row.get(header_map.get('Initiation Date', ''), '')).strip()
                o_val = str(row.get(header_map.get('Outcome Date', ''), '')).strip()

                diff_data.append({
                    'ZONE': zone, 'TB Unit': tu, 'PHI': phi, 'Episode ID': eid, 'Due_Status': due_val,
                    'Diagnosis Date': d_val, 'Initiation Date': i_val, 'Outcome Date': o_val
                })

        df_final = pd.DataFrame(diff_data)
        if not df_final.empty:
            for c in ['Diagnosis Date', 'Initiation Date', 'Outcome Date']:
                df_final[c] = pd.to_datetime(df_final[c], errors='coerce')
        return df_final
    except:
        return pd.DataFrame()

df_master_raw, df_comp_raw, df_curr_tb_raw, df_time, df_outcome_full_raw = load_all_data()
df_dc_raw = load_diff_care_live()

def filter_by_role(df, role, target):
    if df.empty: return df
    target_up = str(target).upper().strip()
    if role == "TB_UNIT" and 'TB Unit' in df.columns:
        return df[df['TB Unit'].astype(str).str.upper().str.contains(target_up, na=False)]
    elif role == "ZONE" and 'ZONE' in df.columns:
        return df[df['ZONE'].astype(str).str.upper().str.contains(target_up, na=False) | df['ZONE'].isin(['N/A', 'NAN'])]
    return df

df_master = filter_by_role(df_master_raw.copy(), st.session_state.role, st.session_state.target)
df_comp = filter_by_role(df_comp_raw.copy(), st.session_state.role, st.session_state.target)
df_curr_tb = filter_by_role(df_curr_tb_raw.copy(), st.session_state.role, st.session_state.target)
df_outcome_full = filter_by_role(df_outcome_full_raw.copy(), st.session_state.role, st.session_state.target)
df_dc_main = filter_by_role(df_dc_raw.copy(), st.session_state.role, st.session_state.target)

def draw_card(title, value, color, icon):
    return f"""<div style="background-color: {color}; border-radius: 8px; padding: 15px 5px; margin-bottom: 10px; color: white; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"><div style="font-size: 24px; margin-bottom: 5px;">{icon}</div><div style="font-size: 13px; font-weight: bold; text-transform: uppercase;">{title}</div><div style="font-size: 26px; font-weight: 900; margin-top: 8px;">{value}</div></div>"""

def clean_selection(selected_list): return [item.rsplit(" (", 1)[0] for item in selected_list]

def get_options_with_counts(df, column_name):
    if df.empty or column_name not in df.columns: return []
    counts = df[column_name].value_counts()
    return [f"{val} ({int(count)})" for val, count in counts.items() if str(val) not in ["nan", "", "None", "N/A"]]

b64_amc, b64_ntep = img_to_b64("images/amc.png"), img_to_b64("images/ntep.jpg")
st.markdown(f"<div style='display: flex; justify-content: space-between; align-items: center;'><img src='data:image/png;base64,{b64_amc}' height='75'><h3 style='margin:0; font-weight:900;'>AMC | NTEP</h3><img src='data:image/jpeg;base64,{b64_ntep}' height='75'></div>", unsafe_allow_html=True)
st.markdown("<div style='background-color:#1f618d; color:white; text-align:center; padding:12px; border-radius:5px; margin:15px 0;'>TB Monitoring Dashboard - Ahmedabad</div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Master", "🔄 Daily Comparison", "🏥 Patients", "🚀 Smart PPT", "📊 Success Rate", "🏥 Diff. Care"])

# ... (Tabs 1 to 4 code simplified for space) ...
with tab1:
    st.dataframe(df_master, use_container_width=True, hide_index=True)

with tab2:
    st.markdown("#### 🔄 Daily Comparison")
    with st.expander("🔽 Filters & Dates", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1: diag_dt2 = st.date_input("Diagnosis Date Range", value=[], key="d1_2")
        with c2: init_dt2 = st.date_input("Initiation Date Range", value=[], key="d2_2")
        with c3: out_dt2 = st.date_input("Outcome Date Range", value=[], key="d3_2")
        
    df_c = df_comp.copy()
    if len(diag_dt2) == 2: df_c = df_c[df_c['Diagnosis Date'].notna() & df_c['Diagnosis Date'].dt.date.between(diag_dt2[0], diag_dt2[1])]
    if len(init_dt2) == 2: df_c = df_c[df_c['Initiation Date'].notna() & df_c['Initiation Date'].dt.date.between(init_dt2[0], init_dt2[1])]
    if len(out_dt2) == 2: df_c = df_c[df_c['Outcome Date'].notna() & df_c['Outcome Date'].dt.date.between(out_dt2[0], out_dt2[1])]
    st.dataframe(df_c, use_container_width=True, hide_index=True)

with tab3:
    st.dataframe(df_curr_tb, use_container_width=True, hide_index=True)

# ==========================================
# 🟢 TAB 5: SUCCESS RATE (REVISED LOGIC)
# ==========================================
with tab5:
    st.markdown("<h3 style='color: #1f618d;'>📊 Success Rate & Death Rate (KPIs)</h3>", unsafe_allow_html=True)
    df_out = df_outcome_full.copy()
    with st.expander("🔽 Filters", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c2:
            regimen_opts = get_options_with_counts(df_out, 'TB_regimen')
            def_regs = [r for r in regimen_opts if "2HRZE/4HRE" in r]
            s5_reg = st.multiselect("TB Regimen", regimen_opts, default=def_regs, key='reg5')
            if s5_reg:
                sel_regs = clean_selection(s5_reg)
                if any("2HRZE/4HRE" in r for r in sel_regs): sel_regs.extend(["N/A", "", "NAN"])
                df_out = df_out[df_out['TB_regimen'].fillna("N/A").isin(sel_regs)]
        with c3:
            diag_dt5 = st.date_input("Diagnosis/Notification Date", value=[], key="d1_5")
            if len(diag_dt5) == 2: df_out = df_out[df_out['Diagnosis Date'].notna() & df_out['Diagnosis Date'].dt.date.between(diag_dt5[0], diag_dt5[1])]

    df_out['Treatment Outcome'] = df_out['Treatment Outcome'].fillna('').astype(str).upper()
    df_out['Is_Success'] = df_out['Treatment Outcome'].str.contains('CURED|COMPLETE', na=False)
    df_out['Is_Dead'] = df_out['Treatment Outcome'].str.contains('DIED', na=False)

    def get_rate_table(df_group, group_col):
        if df_group.empty: return pd.DataFrame()
        grp = df_group.groupby(group_col)
        summary = pd.DataFrame({
            'TOTAL PATIENTS': grp.size(), 
            'SUCCESSFULLY TREATED': grp['Is_Success'].sum(),
            'DIED': grp['Is_Dead'].sum()
        }).reset_index()
        summary['SUCCESS %'] = ((summary['SUCCESSFULLY TREATED'] / summary['TOTAL PATIENTS']) * 100).fillna(0).round(0).astype(int).astype(str) + '%'
        summary['DEATH %'] = ((summary['DIED'] / summary['TOTAL PATIENTS']) * 100).fillna(0).round(0).astype(int).astype(str) + '%'
        
        # Add AMC TOTAL
        total_row = pd.DataFrame({group_col: ['AMC TOTAL'], 'TOTAL PATIENTS': [summary['TOTAL PATIENTS'].sum()], 'SUCCESSFULLY TREATED': [summary['SUCCESSFULLY TREATED'].sum()], 'DIED': [summary['DIED'].sum()]})
        total_row['SUCCESS %'] = ((total_row['SUCCESSFULLY TREATED'] / total_row['TOTAL PATIENTS']) * 100).fillna(0).round(0).astype(int).astype(str) + '%'
        total_row['DEATH %'] = ((total_row['DIED'] / total_row['TOTAL PATIENTS']) * 100).fillna(0).round(0).astype(int).astype(str) + '%'
        return pd.concat([summary, total_row], ignore_index=True)

    st.dataframe(get_rate_table(df_out, 'ZONE'), use_container_width=True, hide_index=True)

# ==========================================
# 🟢 TAB 6: DIFFERENTIATED CARE (THE "92" FIX)
# ==========================================
with tab6:
    st.markdown("<h3 style='color: #1f618d;'>🏥 Differentiated Care Pendency Report</h3>", unsafe_allow_html=True)
    if df_dc_main.empty:
        st.warning("⚠️ ડેટા મળ્યો નથી. ગુગલ શીટ અને લોગિન ઝોન ચેક કરો.")
    else:
        with st.expander("🔽 Filters & Dates", expanded=True):
            c1, c2, c3 = st.columns(3)
            df_dc = df_dc_main.copy()
            with c3:
                diag_dt6 = st.date_input("Diagnosis Date (Notification Month)", value=[], key="d1_6")
            if len(diag_dt6) == 2:
                df_dc = df_dc[df_dc['Diagnosis Date'].notna() & df_dc['Diagnosis Date'].dt.date.between(diag_dt6[0], diag_dt6[1])]

        def get_dc_summary(temp_df, group_col):
            if temp_df.empty: return pd.DataFrame()
            due = temp_df['Due_Status'].fillna('').astype(str).upper()
            not_comp = ~due.str.contains("COMPLETED", na=False)
            summary = temp_df.groupby(group_col).size().reset_index(name='TOTAL ELIGIBLE')
            periods = {'BASELINE': 'BASELINE', '1ST MONTH': '1ST MONTH|1 MONTH', '2ND MONTH': '2ND MONTH|2 MONTH', '3RD MONTH': '3RD MONTH|3 MONTH', '4TH MONTH': '4TH MONTH|4 MONTH', '5TH MONTH': '5TH MONTH|5 MONTH', '6TH MONTH': '6TH MONTH|6 MONTH'}
            for p_name, p_regex in periods.items():
                summary[p_name] = temp_df[not_comp & due.str.contains(p_regex, na=False)].groupby(group_col).size().reindex(summary[group_col], fill_value=0).values
            
            # Add AMC Total
            total_row = pd.DataFrame({group_col: ['AMC TOTAL'], 'TOTAL ELIGIBLE': [summary['TOTAL ELIGIBLE'].sum()]})
            for p in periods.keys(): total_row[p] = [summary[p].sum()]
            return pd.concat([summary, total_row], ignore_index=True)

        st.dataframe(get_dc_summary(df_dc, 'ZONE'), use_container_width=True, hide_index=True)
