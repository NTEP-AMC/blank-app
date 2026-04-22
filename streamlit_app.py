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

def clean_selection(selected_list): return [item.rsplit(" (", 1)[0] for item in selected_list]

b64_amc, b64_ntep = img_to_b64("images/amc.png"), img_to_b64("images/ntep.jpg")
st.markdown(f"<div style='display: flex; justify-content: space-between; align-items: center;'><img src='data:image/png;base64,{b64_amc}' height='75'><h3 style='margin:0; font-weight:900;'>AMC | NTEP</h3><img src='data:image/jpeg;base64,{b64_ntep}' height='75'></div>", unsafe_allow_html=True)
st.markdown("<div style='background-color:#1f618d; color:white; text-align:center; padding:12px; border-radius:5px; margin:15px 0;'>TB Monitoring Dashboard - Ahmedabad</div>", unsafe_allow_html=True)

# 🎯 NEW TABS: PPT Generator ઉમેરાયું 
tab1, tab2, tab3, tab4 = st.tabs(["📊 Master Dashboard", "🔄 Daily Comparison", "🏥 Current TB Patients", "🚀 Smart PPT Generator"])

with tab1:
    # (તમારો જૂનો Tab 1 નો બધો કોડ અહીં જ રહેશે, કોઈ ફેરફાર નહિ)
    st.info("💡 બાકીના રિપોર્ટ અને ફોર્મેટેડ એક્સેલ માટે ફિલ્ટર યુઝ કરો.")
    if not df_master.empty:
        st.dataframe(df_master.head(100), use_container_width=True, hide_index=True)

with tab2:
    st.info("💡 Daily Comparison Data")
    if not df_comp.empty:
        st.dataframe(df_comp.head(100), use_container_width=True, hide_index=True)

with tab3:
    st.info("💡 Active Patients Line List")
    if not df_curr_tb.empty:
        st.dataframe(df_curr_tb.head(100), use_container_width=True, hide_index=True)

# ==========================================
# 🟣 TAB 4: SMART PPT GENERATOR (NEW)
# ==========================================
with tab4:
    st.markdown("<h3 style='text-align: center; color: #27AE60;'>🚀 Automated PPT Report Generator</h3>", unsafe_allow_html=True)
    st.markdown("આ પેનલમાંથી તમે કોઈ પણ રિપોર્ટની 8-સ્લાઈડ વાળી મસ્ત કલરફુલ PPT એક ક્લિકમાં બનાવી શકો છો.")
    
    with st.container():
        c1, c2, c3 = st.columns(3)
        
        with c1:
            all_inds = ["Outcome", "UDST", "Not Put On", "SLPA", "Consent", "ADT", "RBS", "ART", "CPT", "HIV"]
            sel_report = st.selectbox("📌 1. Select Report Type", all_inds)
            
            # ડેટ કોલમ કયું વાપરવું?
            date_col_map = {"Outcome": "Outcome Date"}
            sel_date_col = date_col_map.get(sel_report, "Diagnosis Date")
            
        with c2:
            st.write(f"📅 2. Select Date Range (Filter on **{sel_date_col}**)")
            col_d1, col_d2 = st.columns(2)
            with col_d1: start_d = st.date_input("From Date", date(2025, 1, 1))
            with col_d2: end_d = st.date_input("To Date", date(2025, 3, 31))
            
        with c3:
            st.write("🎨 3. Color Scale Rule")
            color_rule = st.radio(
                "વધુ આંકડાને કયો કલર આપવો છે?",
                ["High is Bad (Red) 🔴", "High is Good (Green) 🟢"],
                help="જો પેન્ડિંગ રિપોર્ટ હોય તો 'High is Bad' રાખો જેથી સૌથી વધુ પેન્ડિંગ વાળા PHI લાલ દેખાય."
            )
            high_is_bad = True if "Bad" in color_rule else False

    # 🎯 PPT જનરેટ કરવાનું ફંક્શન
    def generate_smart_ppt(df, report_name, date_col, s_date, e_date, high_bad):
        try:
            from pptx import Presentation
            from pptx.util import Inches, Pt
            from pptx.dml.color import RGBColor
        except ImportError:
            return None, "⚠️ PPTX લાઈબ્રેરી ઇન્સ્ટોલ નથી!"

        prs = Presentation()
        
        # 1. ડેટા ફિલ્ટર કરો
        mask = (
            df['Pending Status'].astype(str).str.contains(report_name, na=False) &
            (df[date_col].notna()) &
            (df[date_col].dt.date >= s_date) &
            (df[date_col].dt.date <= e_date)
        )
        df_filt = df[mask].copy()

        # 2. કલર ગણવા માટેનું સ્માર્ટ લોજીક
        def get_bg_color(val, max_val):
            if max_val == 0 or pd.isna(val): return RGBColor(255, 255, 255) # White
            ratio = val / max_val
            if not high_bad: ratio = 1 - ratio # Rule ઊલટો કરી દો
            
            if ratio > 0.66: return RGBColor(241, 148, 138)    # Light Red
            elif ratio > 0.33: return RGBColor(249, 231, 159)  # Light Yellow
            else: return RGBColor(171, 235, 198)               # Light Green

        # 3. ટેબલ બનાવવાનું ફંક્શન
        def add_slide_table(title_text, data_df, col_names):
            slide = prs.slides.add_slide(prs.slide_layouts[5])
            title = slide.shapes.title
            title.text = title_text
            title.text_frame.paragraphs[0].font.size = Pt(28)
            
            if data_df.empty:
                tx = slide.shapes.add_textbox(Inches(2), Inches(3), Inches(5), Inches(1))
                tx.text_frame.text = "કોઈ દર્દી પેન્ડિંગ નથી."
                return
                
            rows = len(data_df) + 1
            cols = len(col_names)
            table_shape = slide.shapes.add_table(rows, cols, Inches(1.5), Inches(1.5), Inches(7.0), Inches(0.4))
            table = table_shape.table
            table.columns[0].width = Inches(4.5)
            table.columns[1].width = Inches(2.5)
            
            # હેડર
            for i, c_name in enumerate(col_names):
                cell = table.cell(0, i)
                cell.text = c_name
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(31, 97, 141) # Dark Blue Header
                cell.text_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)
                cell.text_frame.paragraphs[0].font.bold = True
                
            # ડેટા અને કલર સ્કેલ
            max_value = data_df[col_names[1]].max()
            for i, (_, row) in enumerate(data_df.iterrows()):
                name_val = str(row.iloc[0])
                count_val = row.iloc[1]
                
                # Name Column
                c1 = table.cell(i+1, 0)
                c1.text = name_val
                
                # Count Column
                c2 = table.cell(i+1, 1)
                c2.text = str(count_val)
                
                # પબ્લિક/પ્રાઇવેટ મુજબ કલર અને બોલ્ડ
                if "PRIVATE FACILITIES" in name_val:
                    c1.fill.solid(); c1.fill.fore_color.rgb = RGBColor(235, 237, 239) # Grey
                    c2.fill.solid(); c2.fill.fore_color.rgb = RGBColor(235, 237, 239)
                    c1.text_frame.paragraphs[0].font.bold = True
                    c2.text_frame.paragraphs[0].font.bold = True
                else:
                    # કલર સ્કેલ લગાવો
                    c2.fill.solid()
                    c2.fill.fore_color.rgb = get_bg_color(count_val, max_value)

        # સ્લાઈડ 1: All Zones
        z_sum = df_filt.groupby('ZONE').size().reset_index(name='Pending Count')
        z_sum = z_sum.sort_values(by='Pending Count', ascending=False)
        add_slide_table(f"All Zones - {sel_report} Pending", z_sum, ['Zone Name', f'{sel_report} Pending'])
        
        # સ્લાઈડ્સ 2 થી 8: PHI Wise (પબ્લિક પહેલા, પ્રાઇવેટ છેલ્લે ટોટલ)
        zones = sorted(df_filt['ZONE'].dropna().unique())
        for z in zones:
            z_df = df_filt[df_filt['ZONE'] == z]
            
            # પબ્લિક અને પ્રાઇવેટ અલગ પાડો
            pub_mask = z_df['Facility Type'].str.upper().isin(['PUBLIC', 'PHI'])
            pub_df = z_df[pub_mask]
            priv_df = z_df[~pub_mask]
            
            # પબ્લિકનું લિસ્ટ 
            pub_sum = pub_df.groupby('PHI').size().reset_index(name='Pending Count')
            pub_sum = pub_sum.sort_values(by='Pending Count', ascending=False)
            
            # પ્રાઇવેટનું સીધું ટોટલ
            priv_count = len(priv_df)
            if priv_count > 0:
                priv_row = pd.DataFrame({'PHI': ['PRIVATE FACILITIES (TOTAL)'], 'Pending Count': [priv_count]})
                final_phi_summary = pd.concat([pub_sum, priv_row], ignore_index=True)
            else:
                final_phi_summary = pub_sum
                
            add_slide_table(f"{z} Zone - {sel_report} Pending", final_phi_summary, ['PHI Name', f'{sel_report} Pending'])

        out_io = io.BytesIO()
        prs.save(out_io)
        return out_io.getvalue(), "Success"

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("✨ Generate & Download PPT ✨", use_container_width=True):
        with st.spinner("Generating beautiful PPT slides... Please wait..."):
            ppt_bytes, status = generate_smart_ppt(df_master, sel_report, sel_date_col, start_d, end_d, high_is_bad)
            
            if ppt_bytes:
                file_name = f"{sel_report}_Report_{start_d}_to_{end_d}.pptx"
                st.success("✅ PPT 100% તૈયાર છે! નીચેના બટન પર ક્લિક કરીને ડાઉનલોડ કરો.")
                st.download_button(label=f"📥 Download {file_name}", data=ppt_bytes, file_name=file_name, mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")
            else:
                st.error(status)
