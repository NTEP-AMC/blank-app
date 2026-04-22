import streamlit as st
import pandas as pd
import base64
import os
import io
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

# 🎯 ફંક્શન 1: એક્સેલ માટે
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

# 🎯 ફંક્શન 2: PPT જનરેટર (તમારા 8 સ્લાઈડ લોજીક મુજબ)
def generate_outcome_ppt(df_master):
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
    except ImportError:
        st.error("⚠️ PPTX લાઈબ્રેરી ઇન્સ્ટોલ કરેલ નથી. કૃપા કરીને requirements.txt માં 'python-pptx' ઉમેરો.")
        return None

    prs = Presentation()
    
    # સ્ટેપ 1: Jan 2025 થી March 2025 સુધીનો Outcome નો ડેટા ફિલ્ટર કરવો
    mask = (
        df_master['Pending Status'].astype(str).str.contains('Outcome', na=False) &
        (df_master['Outcome Date'] >= pd.to_datetime('2025-01-01', dayfirst=True)) &
        (df_master['Outcome Date'] <= pd.to_datetime('2025-03-31', dayfirst=True))
    )
    df_filtered = df_master[mask].copy()

    # ટેબલ બનાવવાનું ફંક્શન
    def add_table_slide(slide_title, data_df, cols):
        slide = prs.slides.add_slide(prs.slide_layouts[5]) # Title Only Layout
        title = slide.shapes.title
        title.text = slide_title
        title.text_frame.paragraphs[0].font.size = Pt(32)
        
        if data_df.empty:
            txBox = slide.shapes.add_textbox(Inches(2), Inches(3), Inches(5), Inches(1))
            txBox.text_frame.text = "કોઈ દર્દી પેન્ડિંગ નથી."
            return
            
        rows = len(data_df) + 1
        columns = len(cols)
        left = Inches(1.5)
        top = Inches(2.0)
        width = Inches(7.0)
        height = Inches(0.8)
        
        table_shape = slide.shapes.add_table(rows, columns, left, top, width, height)
        table = table_shape.table
        table.columns[0].width = Inches(4.5)
        table.columns[1].width = Inches(2.5)
        
        # હેડર
        for i, col_name in enumerate(cols):
            cell = table.cell(0, i)
            cell.text = col_name
            cell.text_frame.paragraphs[0].font.bold = True
            
        # ડેટા
        for i, (_, row) in enumerate(data_df.iterrows()):
            table.cell(i+1, 0).text = str(row.iloc[0])
            table.cell(i+1, 1).text = str(row.iloc[1])

    # સ્લાઈડ 1: All Zone Wise
    zone_summary = df_filtered.groupby('ZONE').size().reset_index(name='Outcome Pending (Q1 2025)')
    zone_summary = zone_summary.sort_values(by='Outcome Pending (Q1 2025)', ascending=False)
    add_table_slide("All Zones - Outcome Pending (Quarter 1 2025)", zone_summary, ['Zone Name', 'Outcome Pending (Q1 2025)'])
    
    # સ્લાઈડ્સ 2 થી 8: દરેક ઝોનના PHI મુજબ
    zones = sorted(df_filtered['ZONE'].dropna().unique())
    for zone in zones:
        phi_df = df_filtered[df_filtered['ZONE'] == zone]
        phi_summary = phi_df.groupby('PHI').size().reset_index(name='Outcome Pending (Q1 2025)')
        phi_summary = phi_summary.sort_values(by='Outcome Pending (Q1 2025)', ascending=False)
        add_table_slide(f"{zone} Zone - PHI Wise Outcome Pending (Q1 2025)", phi_summary, ['PHI Name', 'Outcome Pending (Q1 2025)'])
        
    output = io.BytesIO()
    prs.save(output)
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
except Exception as e:
    st.error("⚠️ ડેટા ઉપલબ્ધ નથી...")

def filter_by_role(df, role, target):
    if df.empty: return df
    if role == "TB_UNIT" and 'TB Unit' in df.columns: return df[df['TB Unit'].astype(str).str.strip().str.upper() == target]
    elif role == "ZONE" and 'ZONE' in df.columns: return df[df['ZONE'].astype(str).str.strip().str.upper().isin([target, 'N/A', 'NAN', 'NONE'])]
    return df

df_master = filter_by_role(df_master, st.session_state.role, st.session_state.target)
df_comp = filter_by_role(df_comp, st.session_state.role, st.session_state.target)
df_curr_tb = filter_by_role(df_curr_tb, st.session_state.role, st.session_state.target)

def draw_card(title, value, color, icon):
    return f"""<div style="background-color: {color}; border-radius: 8px; padding: 15px 5px; margin-bottom: 10px; color: white; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"><div style="font-size: 24px; margin-bottom: 5px;">{icon}</div><div style="font-size: 13px; font-weight: bold; text-transform: uppercase;">{title}</div><div style="font-size: 26px; font-weight: 900; margin-top: 8px;">{value}</div></div>"""

def get_options_with_counts(df, column_name, tab_name="tab1"):
    if df.empty or column_name not in df.columns: return []
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

tab1, tab2, tab3 = st.tabs(["📊 Master Dashboard", "🔄 Daily Comparison", "🏥 Current TB Patients"])

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
            with oc_cols[i % 4]: st.markdown(draw_card(k, v, colors.get(k, "#34495E"), "📌"), unsafe_allow_html=True
