import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from streamlit_option_menu import option_menu
import requests
from datetime import datetime, timedelta
import time
import asyncio
import json
from pathlib import Path
import os
from typing import Dict, Any
import base64
from comparative_analysis_agent import show_comparative_analysis_agent
from finance_ap_agent import show_ap_automation_agent
from hr_onboarding_email_agent import HROnboardingEmailAgent
from invoice_parsing_module import InvoiceFieldGenerator, InvoiceDatabase

# Page configuration
st.set_page_config(
    page_title="Replisense - Enterprise Agent Suite",
    page_icon="static/replicant.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
def load_css():
    st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .main {
        padding-top: 0rem;
    }
    
    /* Custom styling for the main content */
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 0;
        margin: -1rem -1rem 2rem -1rem;
        text-align: center;
        border-radius: 0 0 20px 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    
    .header-title {
        color: white;
        font-size: 3rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .header-subtitle {
        color: rgba(255,255,255,0.9);
        font-size: 1.2rem;
        margin-top: 0.5rem;
        font-weight: 300;
    }
    
    /* Department cards */
    .department-card {
        border-radius: 20px;
        padding: 2rem 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        border: none;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        height: 180px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        position: relative;
        overflow: hidden;
    }
    
    .department-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 15px 50px rgba(0,0,0,0.25);
    }
    
    .department-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(255,255,255,0.1);
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    
    .department-card:hover::before {
        opacity: 1;
    }
    
    .card-content {
        text-align: center;
        z-index: 1;
        position: relative;
    }
    
    .card-icon {
        font-size: 3rem;
        margin-bottom: 0.8rem;
        display: block;
        filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.2));
    }
    
    .card-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: white;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        letter-spacing: 0.5px;
    }
    
    /* Stats cards */
    .stats-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 8px 32px rgba(240, 147, 251, 0.3);
    }
    
    .stats-number {
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .stats-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    
    /* Sidebar styling - Overlay mode */
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
        border-right: 1px solid #e9ecef;
        position: fixed !important;
        left: 0 !important;
        top: 0 !important;
        height: 100vh !important;
        width: 21rem !important;
        z-index: 999999 !important;
        box-shadow: 2px 0 10px rgba(0,0,0,0.1) !important;
        transition: transform 0.3s ease !important;
    }
    
    /* Hide sidebar when collapsed */
    .sidebar[aria-expanded="false"] .sidebar-content {
        transform: translateX(-100%) !important;
    }
    
    /* Show sidebar when expanded */
    .sidebar[aria-expanded="true"] .sidebar-content {
        transform: translateX(0) !important;
    }
    
    /* Main content area - always full width */
    .main .block-container {
        padding-top: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
        margin-left: 0 !important;
        width: 100% !important;
        max-width: none !important;
    }
    
    /* Ensure main content doesn't get shifted */
    .main {
        margin-left: 0 !important;
        width: 100% !important;
    }
    
    /* Add overlay backdrop when sidebar is open */
    .sidebar[aria-expanded="true"]::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: rgba(0,0,0,0.3);
        z-index: 999998;
        backdrop-filter: blur(2px);
    }
    
    /* Additional classes for different Streamlit versions */
    .css-1d391kg, .css-1dp5vir {
        position: fixed !important;
        left: 0 !important;
        top: 0 !important;
        height: 100vh !important;
        width: 21rem !important;
        z-index: 999999 !important;
        transform: translateX(-100%);
        transition: transform 0.3s ease !important;
    }
    
    /* When sidebar is open */
    .css-1d391kg.css-1aumxhk, .css-1dp5vir.css-1aumxhk {
        transform: translateX(0) !important;
    }
    
    /* Ensure app container takes full width */
    .css-18e3th9, .css-1d391kg, .appview-container {
        margin-left: 0 !important;
        width: 100% !important;
        max-width: 100% !important;
    }
    
    /* Override any margin on main content */
    .css-1y4p8pa, .css-12oz5g7, .main {
        margin-left: 0 !important;
        padding-left: 1rem !important;
        width: 100% !important;
    }
    
    /* Welcome section */
    .welcome-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        color: white;
    }
    
    .welcome-title {
        font-size: 2rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    .welcome-text {
        font-size: 1.1rem;
        line-height: 1.6;
        opacity: 0.9;
    }
    
    /* Hide Streamlit branding but keep sidebar controls */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Ensure sidebar toggle is always visible */
    .css-1d391kg, .css-1dp5vir {
        visibility: visible !important;
    }
    
    /* Style the sidebar toggle button */
    button[kind="header"] {
        background-color: #667eea !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 8px 12px !important;
        margin: 10px !important;
    }
    
    /* Ensure hamburger menu is visible when sidebar is collapsed */
    .css-1v0mbdj {
        display: block !important;
        visibility: visible !important;
    }
    
    /* Additional CSS for sidebar toggle across Streamlit versions */
    [data-testid="collapsedControl"] {
        display: block !important;
        visibility: visible !important;
    }
    
    /* Style for sidebar toggle button */
    [data-testid="collapsedControl"] button {
        background-color: #667eea !important;
        color: white !important;
        border-radius: 8px !important;
    }
    
    /* Ensure sidebar controls are always accessible */
    .css-1cypcdb, .css-1d391kg, .css-1dp5vir, .css-1v0mbdj {
        visibility: visible !important;
        display: block !important;
    }
    
    /* Agent card hover effects */
    .agent-card {
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .agent-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 20px 40px rgba(0,0,0,0.2) !important;
    }
    
    /* Professional button styling */
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        background: linear-gradient(90deg, #764ba2 0%, #667eea 100%);
    }
    
    /* Department header enhancement */
    .department-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 3rem 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 15px 35px rgba(102, 126, 234, 0.3);
    }
    
    /* Status badge styling */
    .status-active {
        background: linear-gradient(90deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
    }
    
    .status-coming-soon {
        background: linear-gradient(90deg, #f59e0b 0%, #d97706 100%);
        color: white;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
    }
    
    </style>
    """, unsafe_allow_html=True)

    # Inject logo into all headers with class .main-header
    try:
        logo_path = Path("static/replicant.png")
        if logo_path.exists():
            logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()
            st.markdown(f"""
            <style>
            .main-header {{
                position: relative;
            }}
            .main-header::before {{
                content: "";
                position: absolute;
                top: 12px;
                left: 16px;
                width: 64px;
                height: 64px;
                background-image: url('data:image/png;base64,{logo_b64}');
                background-size: contain;
                background-repeat: no-repeat;
                border-radius: 8px;
                opacity: 0.95;
            }}
            </style>
            """, unsafe_allow_html=True)
    except Exception:
        pass

# Department configurations
DEPARTMENTS = {
    "Finance": {
        "icon": "💰",
        "description": "AI-powered financial analysis, budgeting, forecasting, and automated reporting for strategic decision making.",
        "gradient": ["#667eea", "#764ba2"]
    },
    "Procurement": {
        "icon": "🛒",
        "description": "Smart procurement automation, vendor management, cost optimization, and supply chain intelligence.",
        "gradient": ["#f093fb", "#f5576c"]
    },
    "Human Resources": {
        "icon": "👥",
        "description": "Intelligent recruitment, employee engagement analytics, performance tracking, and HR automation.",
        "gradient": ["#4facfe", "#00f2fe"]
    },
    "Administration": {
        "icon": "⚙️",
        "description": "Streamlined admin processes, document management, compliance tracking, and operational efficiency.",
        "gradient": ["#43e97b", "#38f9d7"]
    },
    "Marketing": {
        "icon": "📢",
        "description": "Campaign automation, customer insights, market analysis, and brand performance tracking.",
        "gradient": ["#fc466b", "#3f5efb"]
    }
}

def create_department_card(dept_name, dept_info):
    """Create a styled department card"""
    return f"""
    <div class="department-card" style="background: linear-gradient(135deg, {dept_info['gradient'][0]} 0%, {dept_info['gradient'][1]} 100%);">
        <div class="card-content">
            <div class="card-icon">{dept_info['icon']}</div>
            <div class="card-title">{dept_name}</div>
        </div>
    </div>
    """

def create_stats_card(number, label, color="#667eea"):
    """Create a statistics card"""
    return f"""
    <div class="stats-card" style="background: linear-gradient(135deg, {color} 0%, {color}CC 100%);">
        <div class="stats-number">{number}</div>
        <div class="stats-label">{label}</div>
    </div>
    """

def main():
    # Load custom CSS
    load_css()
    
    # Sidebar Navigation
    with st.sidebar:
        # Centered brand logo and title (embed as base64 to avoid broken path issues)
        try:
            _logo_path = Path("static/replicant.png")
            _logo_b64 = base64.b64encode(_logo_path.read_bytes()).decode() if _logo_path.exists() else None
        except Exception:
            _logo_b64 = None

        if _logo_b64:
            st.markdown(
                f"""
            <div style="text-align: center; padding: 1.5rem 0 2rem 0;">
                <img src="data:image/png;base64,{_logo_b64}" width="64" height="64" style="display:block; margin: 0 auto 0.6rem auto;" />
                <h2 style="color: #667eea; margin: 0; font-weight: 800; font-size: 2rem; letter-spacing: 0.5px;">Replisense</h2>
                <p style="color: #7f8c8d; font-size: 0.95rem; margin: 0.5rem 0 0 0;">Enterprise AI Suite</p>
            </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
            <div style="text-align: center; padding: 1.5rem 0 2rem 0;">
                <h2 style="color: #667eea; margin: 0; font-weight: 800; font-size: 2rem; letter-spacing: 0.5px;">Replisense</h2>
                <p style="color: #7f8c8d; font-size: 0.95rem; margin: 0.5rem 0 0 0;">Enterprise AI Suite</p>
            </div>
                """,
                unsafe_allow_html=True,
            )
        
        selected = option_menu(
            menu_title=None,
            options=["Home", "Departments", "Analytics", "Settings", "Support"],
            icons=["house", "building", "bar-chart", "gear", "headset"],
            menu_icon="cast",
            default_index=0,
            orientation="vertical",
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#667eea", "font-size": "18px"},
                "nav-link": {
                    "font-size": "16px",
                    "text-align": "left",
                    "margin": "5px 0",
                    "padding": "12px 20px",
                    "border-radius": "10px",
                    "font-weight": "500",
                    "background-color": "transparent"
                },
                "nav-link-selected": {
                    "background-color": "#667eea", 
                    "color": "white",
                    "font-weight": "600"
                },
            }
        )
    

    
    if selected == "Home":
        # Page header
        st.markdown("""
        <div class="main-header">
            <h1 class="header-title">🏠 Welcome to Replisense</h1>
            <p class="header-subtitle">Enterprise-Grade AI Agent Suite for Modern Businesses</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Welcome section
        st.markdown("""
        <div class="welcome-section">
            <h2 class="welcome-title">The Future of Enterprise Intelligence</h2>
            <p class="welcome-text">
                Replisense revolutionizes how enterprises operate by deploying specialized AI agents across every department. 
                Our intelligent automation suite empowers your teams with data-driven insights, predictive analytics, 
                and seamless workflow automation - all while maintaining the highest standards of security and compliance.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Quick stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(create_stats_card("8", "AI Agents", "#667eea"), unsafe_allow_html=True)
        
        with col2:
            st.markdown(create_stats_card("99.9%", "Uptime", "#2ecc71"), unsafe_allow_html=True)
        
        with col3:
            st.markdown(create_stats_card("500+", "Enterprises", "#e74c3c"), unsafe_allow_html=True)
        
        with col4:
            st.markdown(create_stats_card("24/7", "Support", "#f39c12"), unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Department management tabs (moved from Departments section)
        st.markdown("## 🏢 Department AI Agents")
        st.markdown("Explore and configure AI agents for each department.")
        
        # Department selection
        dept_tabs = st.tabs(list(DEPARTMENTS.keys()))
        
        for i, (dept_name, dept_info) in enumerate(DEPARTMENTS.items()):
            with dept_tabs[i]:
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 2rem;">
                        <div style="font-size: 5rem;">{dept_info['icon']}</div>
                        <h3>{dept_name}</h3>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"### {dept_name} AI Agent")
                    st.markdown(dept_info['description'])
                    
                    st.markdown("#### Features:")
                    if dept_name == "Finance":
                        features = ["Budget Analysis", "Financial Forecasting", "Expense Tracking", "Risk Assessment"]
                    elif dept_name == "Procurement":
                        features = ["Email Quote Parsing", "Vendor Analysis", "Cost Optimization", "Supply Chain Management", "Contract Intelligence"]
                    elif dept_name == "Human Resources":
                        features = ["Talent Acquisition", "Performance Analytics", "Employee Engagement", "Compliance Tracking"]
                    else:
                        features = ["Process Automation", "Data Analytics", "Workflow Optimization", "Performance Monitoring"]
                    
                    for feature in features:
                        st.markdown(f"✅ {feature}")
    
    elif selected == "Departments":
        # Check if we should show procurement department or its sub-agents
        if st.session_state.get('show_email_agent', False):
            show_email_parsing_agent()
        elif st.session_state.get('show_email_config', False):
            show_email_configuration()
        elif st.session_state.get('show_procurement_dept', False):
            show_procurement_department()
        elif st.session_state.get('show_invoice_agent', False):
            show_invoice_parsing_agent()
        elif st.session_state.get('show_quotation_agent', False):
            show_quotation_parsing_agent()
        elif st.session_state.get('show_comparative_agent', False):
            show_comparative_analysis_agent()
        elif st.session_state.get('show_finance_dept', False):
            show_finance_department()
        elif st.session_state.get('show_finance_ap_agent', False):
            show_ap_automation_agent()
        elif st.session_state.get('show_hr_dept', False):
            show_hr_department()
        elif st.session_state.get('show_hr_onboarding_agent', False):
            show_hr_onboarding_agent()
        else:
            # Page header
            st.markdown("""
            <div class="main-header">
                <h1 class="header-title">🏢 Department Management</h1>
                <p class="header-subtitle">Configure and manage AI agents for each department</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Department overview cards (moved from Home section)
            st.markdown("## 🏢 Department Solutions")
            st.markdown("Explore our specialized AI agents designed for each department:")
            
            # Create department cards in a grid
            cols = st.columns(2)
            dept_list = list(DEPARTMENTS.items())
            
            for i, (dept_name, dept_info) in enumerate(dept_list):
                with cols[i % 2]:
                    st.markdown(create_department_card(dept_name, dept_info), unsafe_allow_html=True)
                    if st.button(f"Explore {dept_name}", key=f"dept_btn_{dept_name}", use_container_width=True):
                        if dept_name == "Procurement":
                            st.session_state.show_procurement_dept = True
                            # Clear other states to ensure clean navigation
                            if 'show_email_agent' in st.session_state:
                                st.session_state.show_email_agent = False
                            if 'show_email_config' in st.session_state:
                                st.session_state.show_email_config = False
                            if 'show_quotation_agent' in st.session_state:
                                st.session_state.show_quotation_agent = False
                            st.rerun()
                        elif dept_name == "Quotation Parsing":
                            st.session_state.show_quotation_agent = True
                            st.session_state.show_procurement_dept = False
                            st.rerun()
                        elif dept_name == "Finance":
                            st.session_state.show_finance_dept = True
                            # Clear others
                            st.session_state.show_procurement_dept = False
                            st.rerun()
                        elif dept_name == "Human Resources":
                            st.session_state.show_hr_dept = True
                            st.rerun()
                        else:
                            st.success(f"🚀 {dept_name} Agent will be available soon!")
    
    elif selected == "Analytics":
        # Page header
        st.markdown("""
        <div class="main-header">
            <h1 class="header-title">📊 Enterprise Analytics</h1>
            <p class="header-subtitle">Real-time insights and performance monitoring</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Sample analytics data
        col1, col2 = st.columns(2)
        
        with col1:
            # Sample performance chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                y=[85, 88, 92, 89, 94, 97],
                mode='lines+markers',
                name='AI Efficiency',
                line=dict(color='#667eea', width=3),
                marker=dict(size=8)
            ))
            fig.update_layout(
                title="AI Agent Performance Trends",
                xaxis_title="Month",
                yaxis_title="Efficiency %",
                template="plotly_white",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Sample department usage
            departments = list(DEPARTMENTS.keys())[:6]
            usage = [23, 19, 15, 12, 18, 13]
            
            fig2 = px.pie(
                values=usage,
                names=departments,
                title="Agent Usage by Department",
                color_discrete_sequence=['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe']
            )
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, use_container_width=True)
        
        # Recent activities
        st.markdown("### 📋 Recent Agent Activities")
        activities_data = {
            "Time": ["2 mins ago", "5 mins ago", "12 mins ago", "18 mins ago", "25 mins ago"],
            "Department": ["Finance", "HR", "Sales", "Marketing", "Manufacturing"],
            "Agent": ["Budget Analyzer", "Talent Scout", "Lead Scorer", "Campaign Optimizer", "Quality Controller"],
            "Activity": ["Generated monthly report", "Screened 15 candidates", "Scored 23 new leads", "Optimized ad spend", "Detected quality anomaly"],
            "Status": ["✅ Completed", "✅ Completed", "✅ Completed", "✅ Completed", "⚠️ Alert"]
        }
        st.dataframe(pd.DataFrame(activities_data), use_container_width=True)
    
    elif selected == "Settings":
        # Page header
        st.markdown("""
        <div class="main-header">
            <h1 class="header-title">⚙️ System Configuration</h1>
            <p class="header-subtitle">Manage application settings and preferences</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🔧 General Settings")
            st.selectbox("Default Language", ["English", "Spanish", "French", "German"])
            st.selectbox("Time Zone", ["UTC", "EST", "PST", "CET"])
            st.slider("Auto-save Interval (minutes)", 1, 60, 5)
            st.checkbox("Enable Email Notifications", True)
            st.checkbox("Enable Dark Mode", False)
        
        with col2:
            st.markdown("### 🔒 Security Settings")
            st.selectbox("Authentication Method", ["SSO", "OAuth", "LDAP", "Multi-Factor"])
            st.slider("Session Timeout (hours)", 1, 24, 8)
            st.checkbox("Enable Audit Logging", True)
            st.checkbox("Require Password Change", False)
            st.text_input("Admin Email", "admin@company.com")
        
        st.markdown("### 🤖 Agent Configuration")
        st.slider("Maximum Concurrent Agents", 1, 20, 8)
        st.selectbox("Default AI Model", ["GPT-4", "Claude-3", "Gemini-Pro"])
        st.slider("Response Timeout (seconds)", 5, 120, 30)
        
        if st.button("Save Configuration", type="primary"):
            st.success("Configuration saved successfully!")
    
    elif selected == "Support":
        # Page header
        st.markdown("""
        <div class="main-header">
            <h1 class="header-title">🎧 Support Center</h1>
            <p class="header-subtitle">Get help and contact our support team</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 📞 Contact Support")
            with st.form("support_form"):
                name = st.text_input("Name")
                email = st.text_input("Email")
                priority = st.selectbox("Priority", ["Low", "Medium", "High", "Critical"])
                category = st.selectbox("Category", ["Technical Issue", "Feature Request", "Billing", "General Inquiry"])
                message = st.text_area("Message", height=150)
                
                if st.form_submit_button("Submit Ticket", type="primary"):
                    st.success("Support ticket submitted successfully! We'll get back to you within 24 hours.")
        
        with col2:
            st.markdown("### 📚 Quick Links")
            st.markdown("""
            - 📖 [Documentation](https://docs.replisense.com)
            - 🎥 [Video Tutorials](https://learn.replisense.com)
            - 💬 [Community Forum](https://community.replisense.com)
            - 📧 support@replisense.com
            - 📞 +1 (555) 123-4567
            """)
            
            st.markdown("### 🕐 Support Hours")
            st.markdown("""
            **Business Hours:**
            Monday - Friday: 9 AM - 6 PM EST
            
            **Critical Issues:**
            24/7 Support Available
            """)
    
    # Note: Email Parsing Agent and Configuration are now handled within the Departments section

def show_procurement_department():
    """Display the Procurement Department main dashboard with all agents"""
    st.markdown("""
    <div class="main-header">
        <h1 class="header-title">🛒 Procurement Department</h1>
        <p class="header-subtitle">AI-Powered Procurement Automation & Intelligence</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Back button
    if st.button("← Back to Departments", key="back_to_main"):
        st.session_state.show_procurement_dept = False
        # Clear other states
        if 'show_email_agent' in st.session_state:
            st.session_state.show_email_agent = False
        if 'show_email_config' in st.session_state:
            st.session_state.show_email_config = False
        if 'show_quotation_agent' in st.session_state:
            st.session_state.show_quotation_agent = False
        if 'show_invoice_agent' in st.session_state:
            st.session_state.show_invoice_agent = False
        if 'show_comparative_agent' in st.session_state:
            st.session_state.show_comparative_agent = False
        st.rerun()
    
    # Department overview
    st.markdown("## 📊 Department Overview")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="stats-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <div class="stats-number">3</div>
            <div class="stats-label">Active Agents</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="stats-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <div class="stats-number">15</div>
            <div class="stats-label">Suppliers</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="stats-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <div class="stats-number">24/7</div>
            <div class="stats-label">Monitoring</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # AI Agents Section
    st.markdown("## 🤖 AI Procurement Agents")
    st.markdown("Select an agent to configure and manage procurement processes")
    
    # Create agent cards
    agents_data = [
        {
            "name": "Email Quote Parser",
            "icon": "📧",
            "description": "Automatically scan email inbox for quotations and organize by indent IDs. Supports Gmail, Outlook, Yahoo, and custom IMAP servers.",
            "features": ["Multi-provider Email Support", "Automatic Quote Extraction", "Indent ID Recognition", "File Organization"],
            "status": "active",
            "gradient": ["#667eea", "#764ba2"],
            "action": "email_agent"
        },
        {
            "name": "Quotation Parsing Agent",
            "icon": "📋",
            "description": "Parse quotation documents and extract structured data including supplier details, pricing, line items, and terms & conditions.",
            "features": ["Document Parsing", "Structured Data Extraction", "Database Storage", "Indent ID Integration"],
            "status": "active",
            "gradient": ["#f093fb", "#f5576c"],
            "action": "quotation_agent"
        },
        {
            "name": "Comparative Analysis Agent",
            "icon": "🔍",
            "description": "Compare quotations and generate comprehensive analysis reports with vendor comparison and recommendations.",
            "features": ["Multi-Vendor Comparison", "Parameter Selection", "Price Analysis", "Recommendation Engine"],
            "status": "active",
            "gradient": ["#4facfe", "#00f2fe"],
            "action": "comparative_agent"
        },
        {
            "name": "Email Invoice Parser",
            "icon": "🧾",
            "description": "Parse invoices from email attachments by PO number and store structured data. Supports Gmail, Outlook, Yahoo, and custom IMAP servers.",
            "features": ["PO-based Email Search", "Invoice Extraction", "JSON Database", "Line Items & Taxes"],
            "status": "active",
            "gradient": ["#43e97b", "#38f9d7"],
            "action": "invoice_agent"
        },
        {
            "name": "Vendor Analysis Agent",
            "icon": "📊",
            "description": "Analyze vendor performance, pricing trends, and delivery metrics to optimize supplier relationships and procurement decisions.",
            "features": ["Performance Analytics", "Price Comparison", "Risk Assessment", "Supplier Scoring"],
            "status": "coming_soon",
            "gradient": ["#4facfe", "#00f2fe"],
            "action": "vendor_agent"
        },
        {
            "name": "Contract Intelligence",
            "icon": "📄",
            "description": "AI-powered contract analysis, compliance monitoring, and automated renewal alerts for procurement contracts.",
            "features": ["Contract Analysis", "Compliance Tracking", "Renewal Alerts", "Risk Detection"],
            "status": "coming_soon",
            "gradient": ["#a8edea", "#fed6e3"],
            "action": "contract_agent"
        }
    ]
    
    # Display agents in rows of 2
    for i in range(0, len(agents_data), 2):
        cols = st.columns(2)
        
        for j, col in enumerate(cols):
            if i + j < len(agents_data):
                agent = agents_data[i + j]
                
                with col:
                    create_agent_card(agent)

def show_finance_department():
    """Display the Finance Department dashboard with agents"""
    st.markdown("""
    <div class="main-header">
        <h1 class="header-title">💰 Finance Department</h1>
        <p class="header-subtitle">AP Automation, posting packages and reconciliation</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("← Back to Departments", key="back_to_main_fin"):
        st.session_state.show_finance_dept = False
        if 'show_finance_ap_agent' in st.session_state:
            st.session_state.show_finance_ap_agent = False
        st.rerun()

    st.markdown("## 🤖 Finance Agents")
    agents = [
        {
            "name": "Accounts Payable Automation Agent",
            "icon": "🏦",
            "description": "Parse invoices/GRN/DC/E-Way Bills from email, perform 3-way match, and prepare posting packages.",
            "features": ["PO-based Email Search", "Invoice/GRN/DC/EWB Parsing", "3-Way Match", "ERP Export (CSV/JSON)"],
            "status": "active",
            "gradient": ["#667eea", "#764ba2"],
            "action": "finance_ap_agent",
        }
    ]

    for agent in agents:
        with st.container():
            st.markdown(f"### {agent['icon']} {agent['name']}")
            st.markdown(agent['description'])
            st.markdown("**Key Features:**")
            for f in agent['features']:
                st.markdown(f"• {f}")
            if st.button(f"🚀 Launch {agent['name']}", key="launch_fin_ap", type="primary"):
                st.session_state.show_finance_ap_agent = True
                st.session_state.show_finance_dept = False
                st.rerun()

def show_hr_department():
    """Display the Human Resources Department dashboard with agents"""
    st.markdown("""
    <div class="main-header">
        <h1 class="header-title">👥 Human Resources</h1>
        <p class="header-subtitle">Automated onboarding document collection and organization</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("← Back to Departments", key="back_to_main_hr"):
        st.session_state.show_hr_dept = False
        if 'show_hr_onboarding_agent' in st.session_state:
            st.session_state.show_hr_onboarding_agent = False
        st.rerun()

    st.markdown("## 🤖 HR Agents")
    agents = [
        {
            "name": "HR Onboarding Agent",
            "icon": "📥",
            "description": "Parse all candidate documents from email by Employee ID and store them in organized folders.",
            "features": ["Employee ID-based Search", "Attachment Collection", "Folder Organization", "Summary JSON"],
            "status": "active",
            "gradient": ["#4facfe", "#00f2fe"],
            "action": "hr_onboarding_agent",
        }
    ]

    for agent in agents:
        with st.container():
            st.markdown(f"### {agent['icon']} {agent['name']}")
            st.markdown(agent['description'])
            st.markdown("**Key Features:**")
            for f in agent['features']:
                st.markdown(f"• {f}")
            if st.button(f"🚀 Launch {agent['name']}", key="launch_hr_onboarding", type="primary"):
                st.session_state.show_hr_onboarding_agent = True
                st.session_state.show_hr_dept = False
                st.rerun()

def show_hr_onboarding_agent():
    """HR Onboarding Agent UI to fetch and store documents by Employee ID"""
    st.markdown("""
    <div class="main-header">
        <h1 class="header-title">📥 HR Onboarding Agent</h1>
        <p class="header-subtitle">Parse candidate documents by Employee ID from email and organize storage</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("← Back to HR Department", key="back_to_hr_dept"):
        st.session_state.show_hr_onboarding_agent = False
        st.session_state.show_hr_dept = True
        st.rerun()

    # Config section
    st.markdown("## 🔧 Agent Configuration")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### Email Configuration")
        try:
            with open("email_config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            st.success(f"✅ Email configured: {cfg.get('email_address','Not set')}")
            st.info(f"📧 Provider: {cfg.get('provider','Unknown').title()}")
            status = "🟢 Ready to scan emails"
        except Exception:
            st.warning("⚠️ Email not configured")
            status = "🔴 Setup required"
        st.info(f"**Status:** {status}")
    with col2:
        st.markdown("### Quick Actions")
        if st.button("⚙️ Configure Email", key="config_email_hr", type="primary"):
            st.session_state.show_email_config = True
            st.session_state.show_hr_onboarding_agent = False
            st.rerun()

    # Search and parse by Employee ID
    st.markdown("### 👤 Step 1: Enter Employee ID")
    employee_id = st.text_input("Employee ID in email subject", placeholder="e.g., EMP-10023")
    if not employee_id:
        st.info("Enter an Employee ID to continue.")
        return

    st.markdown("### 📧 Step 2: Scan Email for Onboarding Documents")
    if st.button("🔍 Scan by Employee ID", key="scan_hr_docs", type="primary"):
        agent = HROnboardingEmailAgent()
        with st.spinner("Scanning mailbox..."):
            result = asyncio.run(agent.process_emails_by_employee_id(employee_id))
        if result and not result.get('error'):
            st.success(f"Found {result.get('total_documents', 0)} attachments tagged to Employee ID {employee_id}")
            st.session_state.hr_scan_result = result
        else:
            st.error(f"Scan error: {result.get('error','Unknown error') if result else 'Unknown'}")

    # Display results
    scan = st.session_state.get('hr_scan_result')
    if scan and scan.get('documents'):
        rows = []
        for doc in scan['documents']:
            rows.append({
                "Email Subject": doc.get('email_subject','')[:60] + '...',
                "Sender": doc.get('sender',''),
                "Date": doc.get('date',''),
                "Filename": doc.get('filename',''),
                "Path": doc.get('saved_path',''),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # View HR records
    st.markdown("### 📊 View Onboarding Documents")
    agent = HROnboardingEmailAgent()
    emp_ids = agent.get_all_employee_ids()
    if emp_ids:
        selected_emp = st.selectbox("Select Employee ID", options=emp_ids, index=emp_ids.index(employee_id) if employee_id in emp_ids else 0)
        emp_docs = agent.get_documents_by_employee_id(selected_emp)
        if emp_docs and emp_docs.get('documents'):
            table = []
            for r in emp_docs['documents']:
                table.append({
                    "Filename": r.get('filename',''),
                    "Processed": r.get('date',''),
                    "Path": r.get('saved_path',''),
                    "Sender": r.get('sender',''),
                })
            st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)

def create_agent_card(agent):
    """Create a professional agent card using Streamlit components"""
    
    # Create a styled container
    with st.container():
        # Status badge
        if agent["status"] == "active":
            status_color = "🟢"
            status_text = "ACTIVE"
        else:
            status_color = "🟡"
            status_text = "COMING SOON"
        
        # Card header with icon and title
        st.markdown(f"""
        <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, {agent['gradient'][0]} 0%, {agent['gradient'][1]} 100%); 
                    border-radius: 15px; margin: 1rem 0; color: white; box-shadow: 0 8px 25px rgba(0,0,0,0.15);">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">{agent['icon']}</div>
            <h3 style="margin: 0.5rem 0; font-weight: 700; font-size: 1.3rem;">{agent['name']}</h3>
            <div style="background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 15px; 
                        font-size: 0.8rem; font-weight: 600; display: inline-block; margin: 0.5rem 0;">
                {status_color} {status_text}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Description
        st.markdown(f"**Description:** {agent['description']}")
        
        # Features
        st.markdown("**Key Features:**")
        for feature in agent['features']:
            st.markdown(f"• {feature}")
        
        # Action button
        st.markdown("<br>", unsafe_allow_html=True)
        
        if agent["status"] == "active":
            if st.button(f"🚀 Launch {agent['name']}", key=f"launch_{agent['action']}", use_container_width=True, type="primary"):
                if agent["action"] == "email_agent":
                    st.session_state.show_email_agent = True
                    st.session_state.show_procurement_dept = False
                    st.rerun()
                elif agent["action"] == "quotation_agent":
                    st.session_state.show_quotation_agent = True
                    st.session_state.show_procurement_dept = False
                    st.rerun()
                elif agent["action"] == "invoice_agent":
                    st.session_state.show_invoice_agent = True
                    st.session_state.show_procurement_dept = False
                    st.rerun()
                elif agent["action"] == "comparative_agent":
                    st.session_state.show_comparative_agent = True
                    st.session_state.show_procurement_dept = False
                    st.rerun()
        else:
            if st.button(f"📅 Notify When Ready", key=f"notify_{agent['action']}", use_container_width=True):
                st.success(f"✅ You'll be notified when {agent['name']} is available!")
        
        # Add spacing
        st.markdown("<br>", unsafe_allow_html=True)

def show_email_parsing_agent():
    """Display the Email Parsing Agent interface"""
    st.markdown("""
    <div class="main-header">
        <h1 class="header-title">📧 Email Parsing Agent</h1>
        <p class="header-subtitle">Purchase & Procurement Department - Gmail Quote Parser</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Back button
    if st.button("← Back to Procurement Department", key="back_to_dept"):
        st.session_state.show_email_agent = False
        st.session_state.show_procurement_dept = True
        st.rerun()
    
    # Agent status and configuration
    st.markdown("## 🔧 Agent Configuration")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Email Configuration")
        
        config_file = Path("email_config.json")
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                email_address = config_data.get('email_address', 'Not set')
                provider = config_data.get('provider', 'Unknown')
                
                st.success(f"✅ Email configured: {email_address}")
                st.info(f"📧 Provider: {provider.title()}")
                auth_status = "🟢 Ready to scan emails"
            except Exception as e:
                st.error(f"❌ Configuration file corrupted: {str(e)}")
                auth_status = "🔴 Setup required"
        else:
            st.warning("⚠️ Email not configured")
            auth_status = "🟡 Click 'Configure Email' to setup"
            st.markdown("""
            **Supported Email Providers:**
            - Gmail (gmail.com)
            - Outlook/Hotmail (outlook.com, hotmail.com)
            - Yahoo Mail (yahoo.com)
            - Custom IMAP servers
            """)
        
        st.info(f"**Status:** {auth_status}")
    
    with col2:
        st.markdown("### Quick Actions")
        
        if st.button("⚙️ Configure Email", key="config_email", type="primary"):
            st.session_state.show_email_config = True
            st.session_state.show_email_agent = False
            st.rerun()
        
        if st.button("🔍 Test Connection", key="test_connection"):
            try:
                from email_parsing_agent import EmailParsingAgent
                agent = EmailParsingAgent()
                
                with st.spinner("Testing email connection..."):
                    success = asyncio.run(agent.connect_to_email())
                    if success:
                        st.success("Email connection successful!")
                        agent.disconnect_from_email()
                    else:
                        st.error("Email connection failed! Check your configuration.")
            except Exception as e:
                st.error(f"Connection test error: {str(e)}")
    
    # View Stored Quotes section
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("## 📊 View Stored Quotes")
    
    with st.form("view_quotes_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            from_date = st.date_input("From Date", value=datetime.now() - timedelta(days=30))
        
        with col2:
            to_date = st.date_input("To Date", value=datetime.now())
        
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)  # Spacer
            if st.form_submit_button("📊 View Stored Quotes", type="secondary"):
                st.session_state.view_quotes_triggered = True
                st.session_state.date_range = {'from_date': from_date, 'to_date': to_date}
    
    # View Stored Quotes Results Container
    with st.container():
        if st.session_state.get('view_quotes_triggered', False):
            # Add clear button for view quotes
            if st.button("❌ Clear View Quotes Results", key="clear_view_quotes", type="secondary"):
                st.session_state.view_quotes_triggered = False
                st.rerun()
            
            show_stored_quotes_table(
                st.session_state.date_range['from_date'],
                st.session_state.date_range['to_date']
            )
    
    # Email scanning section
    st.markdown("## 📧 Email Scanning")
    
    with st.form("scan_emails_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            days_back = st.number_input("Days to scan back", min_value=1, max_value=90, value=30)
        
        with col2:
            specific_indent = st.text_input("Specific Indent ID (optional)", placeholder="e.g., 1234")
        
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)  # Spacer
            if st.form_submit_button("🔍 Scan Emails", type="primary"):
                # Set flag to trigger centered scanning status display
                st.session_state.scanning_triggered = True
                st.session_state.scan_params = {'days_back': days_back, 'specific_indent': specific_indent}
    
    # Email Scanning Results Container
    with st.container():
        if st.session_state.get('scanning_triggered', False):
            # Add clear button for scan results
            if st.button("❌ Clear Scan Results", key="clear_scan_results", type="secondary"):
                st.session_state.scanning_triggered = False
                st.rerun()
            
            scan_emails_action_fullwidth(
                st.session_state.scan_params['days_back'], 
                st.session_state.scan_params['specific_indent']
            )
    
    # Results section
    show_email_scan_results()

def show_email_configuration():
    """Display email configuration form"""
    st.markdown("""
    <div class="main-header">
        <h1 class="header-title">⚙️ Email Configuration</h1>
        <p class="header-subtitle">Setup your email account for quote parsing</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Back button
    if st.button("← Back to Email Agent", key="back_to_agent"):
        st.session_state.show_email_config = False
        st.session_state.show_email_agent = True
        st.rerun()
    
    st.markdown("## 📧 Email Account Setup")
    
    with st.form("email_config_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            provider = st.selectbox(
                "Email Provider",
                ["gmail", "outlook", "yahoo", "custom"],
                format_func=lambda x: {
                    "gmail": "Gmail",
                    "outlook": "Outlook/Hotmail",
                    "yahoo": "Yahoo Mail",
                    "custom": "Custom IMAP Server"
                }[x]
            )
            
            email_address = st.text_input(
                "Email Address",
                placeholder="your.email@gmail.com"
            )
            
            password = st.text_input(
                "Password / App Password",
                type="password",
                help="For Gmail/Outlook, use App Password instead of regular password"
            )
        
        with col2:
            st.markdown("### 🔒 Security Notes")
            st.info("""
            **App Passwords Recommended:**
            - Gmail: Enable 2FA, then create App Password
            - Outlook: Use App Password from account settings
            - Yahoo: Generate App Password for IMAP access
            """)
            
            if provider == "custom":
                st.markdown("### Custom IMAP Settings")
                imap_server = st.text_input("IMAP Server", placeholder="imap.yourserver.com")
                imap_port = st.number_input("IMAP Port", value=993)
                use_ssl = st.checkbox("Use SSL", value=True)
            else:
                imap_server = None
                imap_port = None
                use_ssl = True
        
        submitted = st.form_submit_button("💾 Save Configuration", type="primary")
        
        if submitted:
            if not email_address or not password:
                st.error("Please provide both email and password!")
            else:
                try:
                    from email_parsing_agent import EmailParsingAgent, EmailConfig
                    
                    config = EmailConfig(
                        provider=provider,
                        email_address=email_address,
                        password=password,
                        imap_server=imap_server,
                        imap_port=imap_port,
                        use_ssl=use_ssl
                    )
                    
                    agent = EmailParsingAgent()
                    
                    if agent.save_email_config(config):
                        st.success("✅ Email configuration saved successfully!")
                        
                        # Test connection
                        with st.spinner("Testing connection..."):
                            if asyncio.run(agent.connect_to_email()):
                                st.success("✅ Connection test successful!")
                                agent.disconnect_from_email()
                                st.session_state.show_email_config = False
                                st.session_state.show_email_agent = True
                                st.rerun()
                            else:
                                st.error("❌ Connection test failed! Please check your settings.")
                    else:
                        st.error("Failed to save configuration!")
                        
                except Exception as e:
                    st.error(f"Configuration error: {str(e)}")

def scan_emails_action_fullwidth(days_back: int, specific_indent: str = ""):
    """Handle email scanning action with full-width centered status messages"""
    try:
        from email_parsing_agent import EmailParsingAgent
        
        agent = EmailParsingAgent()
        
        # Check if email is configured
        if not agent.email_config:
            st.error("❌ Email not configured! Please configure your email first.")
            st.session_state.scanning_triggered = False
            return
        
        # Add some spacing
        st.markdown("---")
        
        # Show scanning status with plain text
        if specific_indent:
            st.info(f"🔍 Scanning emails for indent ID: {specific_indent}")
        else:
            st.info(f"🔍 Scanning all emails from last {days_back} days...")
        
        # Perform the actual scanning with spinner
        with st.spinner("Scanning emails..."):
            if specific_indent:
                result = asyncio.run(agent.process_emails_by_indent(specific_indent))
                st.session_state.last_scan_result = [result] if result.get('success', True) else []
            else:
                results = asyncio.run(agent.scan_all_emails(days_back=days_back))
                st.session_state.last_scan_result = results
        
        # Cleanup connection
        agent.disconnect_from_email()
        
        # Show completion status with plain text
        if st.session_state.get('last_scan_result'):
            st.success(f"✅ Scan completed! Found {len(st.session_state.last_scan_result)} indent groups.")
        else:
            st.warning("⚠️ No quote emails found in the specified timeframe.")
        
        # Don't reset the scanning trigger here - let user clear it manually
            
    except Exception as e:
        st.error(f"❌ Scan failed: {str(e)}")
        # Don't reset the scanning trigger here - let user clear it manually

def scan_emails_action_centered(days_back: int, specific_indent: str = ""):
    """Handle email scanning action with centered status messages"""
    try:
        from email_parsing_agent import EmailParsingAgent
        
        agent = EmailParsingAgent()
        
        # Check if email is configured
        if not agent.email_config:
            # Show error message centered
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.error("❌ Email not configured! Please configure your email first.")
            return
        
        # Show scanning status centered
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if specific_indent:
                st.info(f"🔍 Scanning emails for indent ID: {specific_indent}")
            else:
                st.info(f"🔍 Scanning all emails from last {days_back} days...")
        
        # Perform the actual scanning with spinner
        with st.spinner("Scanning emails..."):
            if specific_indent:
                result = asyncio.run(agent.process_emails_by_indent(specific_indent))
                st.session_state.last_scan_result = [result] if result.get('success', True) else []
            else:
                results = asyncio.run(agent.scan_all_emails(days_back=days_back))
                st.session_state.last_scan_result = results
        
        # Cleanup connection
        agent.disconnect_from_email()
        
        # Show completion status centered
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.session_state.get('last_scan_result'):
                st.success(f"✅ Scan completed! Found {len(st.session_state.last_scan_result)} indent groups.")
            else:
                st.warning("⚠️ No quote emails found in the specified timeframe.")
            
    except Exception as e:
        # Show error message centered
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.error(f"❌ Scan failed: {str(e)}")

def scan_emails_action(days_back: int, specific_indent: str = ""):
    """Handle email scanning action (legacy function for compatibility)"""
    try:
        from email_parsing_agent import EmailParsingAgent
        
        agent = EmailParsingAgent()
        
        # Check if email is configured
        if not agent.email_config:
            st.error("❌ Email not configured! Please configure your email first.")
            return
        
        with st.spinner("Scanning emails..."):
            if specific_indent:
                st.info(f"Scanning emails for indent ID: {specific_indent}")
                result = asyncio.run(agent.process_emails_by_indent(specific_indent))
                st.session_state.last_scan_result = [result] if result.get('success', True) else []
            else:
                st.info(f"Scanning all emails from last {days_back} days...")
                results = asyncio.run(agent.scan_all_emails(days_back=days_back))
                st.session_state.last_scan_result = results
        
        # Cleanup connection
        agent.disconnect_from_email()
        
        if st.session_state.get('last_scan_result'):
            st.success(f"✅ Scan completed! Found {len(st.session_state.last_scan_result)} indent groups.")
        else:
            st.warning("No quote emails found in the specified timeframe.")
            
    except Exception as e:
        st.error(f"Scan failed: {str(e)}")

def show_email_scan_results():
    """Display email scan results"""
    if not st.session_state.get('last_scan_result'):
        return
    
    st.markdown("## 📊 Scan Results")
    
    results = st.session_state.last_scan_result
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    total_emails = sum(r.get('total_emails', 0) for r in results)
    total_quotes = sum(r.get('total_quotes', 0) for r in results)
    unique_indents = len(results)
    
    with col1:
        st.metric("Indent Groups", unique_indents)
    with col2:
        st.metric("Total Emails", total_emails)
    with col3:
        st.metric("Quote Files", total_quotes)
    
    # Detailed results
    for result in results:
        indent_id = result.get('indent_id', 'Unknown')
        
        with st.expander(f"📋 Indent ID: {indent_id} ({result.get('total_quotes', 0)} quotes)"):
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown(f"**Emails Processed:** {result.get('total_emails', 0)}")
                st.markdown(f"**Quote Files:** {result.get('total_quotes', 0)}")
                st.markdown(f"**Processed:** {result.get('processed_date', 'Unknown')}")
            
            with col2:
                if st.button(f"📁 Open Folder", key=f"open_{indent_id}"):
                    folder_path = Path("quotes_storage") / "by_indent_id" / f"indent_{indent_id}"
                    if folder_path.exists():
                        st.success(f"Folder: {folder_path.absolute()}")
                    else:
                        st.error("Folder not found")
            
            # Show individual quotes
            quotes = result.get('quotes', [])
            if quotes:
                quote_data = []
                for quote in quotes:
                    quote_data.append({
                        'Email Subject': quote.get('email_subject', '')[:50] + '...',
                        'Sender': quote.get('sender', ''),
                        'Date': quote.get('date', ''),
                        'Filename': quote.get('filename', ''),
                        'Confidence': quote.get('quote_data', {}).get('confidence_score', 0)
                    })
                
                df = pd.DataFrame(quote_data)
                st.dataframe(df, use_container_width=True)

def show_stored_quotes_table(from_date, to_date):
    """Display stored quotes in table format filtered by date range"""
    try:
        from email_parsing_agent import EmailParsingAgent
        
        agent = EmailParsingAgent()
        
        # Add divider and status message
        st.markdown("---")
        st.info(f"📊 Loading stored quotes from {from_date} to {to_date}...")
        
        # Get all indent IDs
        indent_ids = agent.get_all_indent_ids()
        
        if not indent_ids:
            st.warning("⚠️ No stored quotes found. Run an email scan first.")
            # Don't reset the trigger here - let user clear it manually
            return
        
        # Collect all attachments from all indent IDs
        all_attachments = []
        
        for indent_id in indent_ids:
            quotes_data = agent.get_quotes_by_indent(indent_id)
            
            if 'quotes' in quotes_data:
                for quote in quotes_data['quotes']:
                    try:
                        # Parse quote date
                        quote_date = datetime.fromisoformat(quote.get('date', ''))
                        quote_date_only = quote_date.date()
                        
                        # Check if attachment is within date range
                        if from_date <= quote_date_only <= to_date:
                            quote_data = quote.get('quote_data', {})
                            
                            all_attachments.append({
                                'Indent ID': indent_id,
                                'Email Subject': quote.get('email_subject', 'Unknown')[:50] + '...',
                                'Sender': quote.get('sender', 'Unknown'),
                                'Date': quote_date.strftime('%Y-%m-%d %H:%M'),
                                'Filename': quote.get('filename', 'Unknown'),
                                'File Path': quote.get('saved_path', 'N/A'),
                                'File Size (KB)': f"{quote.get('size', 0) / 1024:.1f}" if quote.get('size') else 'N/A'
                            })
                    except Exception as e:
                        # Skip invalid quotes
                        continue
        
        if not all_attachments:
            st.warning(f"⚠️ No attachments found in the date range {from_date} to {to_date}.")
        else:
            # Success message
            st.success(f"✅ Found {len(all_attachments)} attachments in the selected date range.")
            
            # Create DataFrame and display table
            df = pd.DataFrame(all_attachments)
            
            # Sort by date (newest first)
            df = df.sort_values('Date', ascending=False)
            
            # Display the table with full width
            st.markdown("### 📊 Email Attachments Database")
            st.dataframe(
                df, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "File Size (KB)": st.column_config.NumberColumn(
                        "File Size (KB)",
                        help="Size of the attachment file in kilobytes",
                        min_value=0,
                    )
                }
            )
            
            # Summary statistics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Attachments", len(all_attachments))
            
            with col2:
                unique_indents = len(df['Indent ID'].unique())
                st.metric("Unique Indents", unique_indents)
            
            with col3:
                unique_senders = len(df['Sender'].unique())
                st.metric("Unique Senders", unique_senders)
            
            with col4:
                total_size_kb = sum([float(size.replace(' KB', '')) for size in df['File Size (KB)'] if size != 'N/A'])
                st.metric("Total Size (KB)", f"{total_size_kb:.1f}")
        
        # Reset the view trigger
        st.session_state.view_quotes_triggered = False
        
    except Exception as e:
        st.error(f"❌ Error loading attachments: {str(e)}")
        st.session_state.view_quotes_triggered = False

def show_stored_quotes():
    """Display all stored quotes"""
    try:
        from email_parsing_agent import EmailParsingAgent
        
        agent = EmailParsingAgent()
        indent_ids = agent.get_all_indent_ids()
        
        if not indent_ids:
            st.info("No stored quotes found. Run an email scan first.")
            return
        
        st.markdown("### 📁 Stored Quotes by Indent ID")
        
        for indent_id in indent_ids:
            quotes_data = agent.get_quotes_by_indent(indent_id)
            
            if quotes_data and not quotes_data.get('error'):
                with st.expander(f"Indent ID: {indent_id}"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.json(quotes_data)
                    
                    with col2:
                        folder_path = Path("quotes_storage") / "by_indent_id" / f"indent_{indent_id}"
                        st.markdown(f"**Folder:** `{folder_path}`")
                        
                        if st.button(f"Delete {indent_id}", key=f"delete_{indent_id}"):
                            # In production, add confirmation dialog
                            st.warning("Delete functionality not implemented for safety")
    
    except ImportError:
        st.error("Email parsing agent not available.")
    except Exception as e:
        st.error(f"Error loading stored quotes: {str(e)}")

def show_quotation_parsing_agent():
    """Display the Quotation Parsing Agent interface"""
    st.markdown("""
    <div class="main-header">
        <h1 class="header-title">📋 Quotation Parsing Agent</h1>
        <p class="header-subtitle">Purchase & Procurement Department - Document Quote Parser</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Back button
    if st.button("← Back to Procurement Department", key="back_to_dept_quotation"):
        st.session_state.show_quotation_agent = False
        st.session_state.show_procurement_dept = True
        st.rerun()
    
    # Agent status and configuration
    st.markdown("## 🔧 Agent Configuration")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Quotation Parsing Configuration")
        
        # Check if GROQ API key is configured
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            st.success(f"✅ GROQ API configured")
            st.info(f"🤖 AI Model: Llama3-70B")
            auth_status = "🟢 Ready to parse quotations"
        else:
            st.warning("⚠️ GROQ API key not configured")
            auth_status = "🔴 Setup required"
            st.markdown("""
            **Setup Required:**
            - Add GROQ_API_KEY to your environment variables
            - Get API key from https://console.groq.com/
            """)
        
        st.info(f"**Status:** {auth_status}")
    
    with col2:
        st.markdown("### Quick Actions")
        
        if st.button("🔍 Test AI Connection", key="test_ai_connection"):
            try:
                from quotation_parsing_agent import QuotationFieldGenerator
                generator = QuotationFieldGenerator()
                st.success("✅ AI connection successful!")
            except Exception as e:
                st.error(f"❌ AI connection failed: {str(e)}")
    
    # Search Email Database Section
    st.markdown("## 📧 Search Email Database")
    
    with st.form("search_email_database_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_indent_id = st.text_input("Indent ID", placeholder="e.g., 1234", help="Enter the indent ID to search for")
        
        with col2:
            from_date = st.date_input("From Date", value=datetime.now() - timedelta(days=30))
        
        with col3:
            to_date = st.date_input("To Date", value=datetime.now())
        
        if st.form_submit_button("🔍 Search Email Database", type="primary"):
            if not search_indent_id:
                st.error("❌ Please enter an Indent ID")
            else:
                st.session_state.search_email_triggered = True
                st.session_state.search_params = {
                    'indent_id': search_indent_id,
                    'from_date': from_date,
                    'to_date': to_date
                }
    
    # Display search results
    if st.session_state.get('search_email_triggered', False):
        show_email_search_results(
            st.session_state.search_params['indent_id'],
            st.session_state.search_params['from_date'],
            st.session_state.search_params['to_date']
        )
    
    # View Parsed Quotations Section
    st.markdown("## 📊 View Parsed Quotations")
    
    with st.form("view_parsed_quotations_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            parsed_search_indent_id = st.text_input("Search by Indent ID", placeholder="e.g., 1234", key="parsed_search_indent")
        
        with col2:
            parsed_from_date = st.date_input("From Date", value=datetime.now() - timedelta(days=30), key="parsed_from_date")
        
        with col3:
            parsed_to_date = st.date_input("To Date", value=datetime.now(), key="parsed_to_date")
        
        if st.form_submit_button("📊 View Parsed Quotations", type="secondary"):
            st.session_state.view_parsed_quotations_triggered = True
            st.session_state.parsed_search_params = {
                'indent_id': parsed_search_indent_id,
                'from_date': parsed_from_date,
                'to_date': parsed_to_date
            }
    
    # Display parsed quotations
    if st.session_state.get('view_parsed_quotations_triggered', False):
        show_parsed_quotations_table(
            st.session_state.parsed_search_params['indent_id'],
            st.session_state.parsed_search_params['from_date'],
            st.session_state.parsed_search_params['to_date']
        )


def show_invoice_parsing_agent():
    """Display the Email Invoice Parser interface (PO-based)"""
    from invoice_email_parsing_agent import InvoiceEmailParsingAgent
    from fileparser import FileParser
    st.markdown("""
    <div class="main-header">
        <h1 class="header-title">🧾 Email Invoice Parser</h1>
        <p class="header-subtitle">Procurement - Parse invoices by PO number from email attachments</p>
    </div>
    """, unsafe_allow_html=True)

    # Back button
    if st.button("← Back to Procurement Department", key="back_to_dept_invoice"):
        st.session_state.show_invoice_agent = False
        st.session_state.show_procurement_dept = True
        st.rerun()

    agent = InvoiceEmailParsingAgent()
    inv_db = InvoiceDatabase()

    # Agent status and configuration
    st.markdown("## 🔧 Agent Configuration")
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Email Configuration")
        config_file = Path("email_config.json")
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                email_address = config_data.get('email_address', 'Not set')
                provider = config_data.get('provider', 'Unknown')
                st.success(f"✅ Email configured: {email_address}")
                st.info(f"📧 Provider: {provider.title()}")
                auth_status = "🟢 Ready to scan emails"
            except Exception as e:
                st.error(f"❌ Configuration file corrupted: {str(e)}")
                auth_status = "🔴 Setup required"
        else:
            st.warning("⚠️ Email not configured")
            auth_status = "🟡 Click 'Configure Email' to setup"
            st.markdown("""
            **Supported Email Providers:**
            - Gmail (gmail.com)
            - Outlook/Hotmail (outlook.com, hotmail.com)
            - Yahoo Mail (yahoo.com)
            - Custom IMAP servers
            """)
        st.info(f"**Status:** {auth_status}")

    with col2:
        st.markdown("### Quick Actions")
        if st.button("⚙️ Configure Email", key="config_email_invoice", type="primary"):
            st.session_state.show_email_config = True
            st.session_state.show_invoice_agent = False
            st.rerun()
        if st.button("🔍 Test Connection", key="test_connection_invoice"):
            try:
                with st.spinner("Testing email connection..."):
                    success = asyncio.run(agent.connect_to_email())
                    if success:
                        st.success("Email connection successful!")
                        agent.disconnect_from_email()
                    else:
                        st.error("Email connection failed! Check your configuration.")
            except Exception as e:
                st.error(f"Connection test error: {str(e)}")

    # Search Invoices by PO
    st.markdown("## 📧 Search Email by PO Number")
    with st.form("search_invoice_email_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            po_number = st.text_input("PO Number", placeholder="e.g., PO-2024-001")
        with col2:
            from_date = st.date_input("From Date", value=datetime.now() - timedelta(days=30))
        with col3:
            to_date = st.date_input("To Date", value=datetime.now())
        if st.form_submit_button("🔍 Search Invoices", type="primary"):
            if not po_number:
                st.error("❌ Please enter a PO Number")
            else:
                st.session_state.invoice_search_triggered = True
                st.session_state.invoice_search_params = {"po_number": po_number, "from_date": from_date, "to_date": to_date}

    if st.session_state.get('invoice_search_triggered', False):
        st.markdown("---")
        params = st.session_state.invoice_search_params
        st.info(f"📧 Searching emails for PO: {params['po_number']}")
        with st.spinner("Scanning mailbox..."):
            result = asyncio.run(agent.process_emails_by_po(params['po_number']))
        if result and not result.get('error'):
            st.success(f"✅ Found {result.get('total_invoices', 0)} invoice attachments for PO {params['po_number']}")
            # Table
            rows = []
            for inv in result.get('invoices', []):
                rows.append({
                    "PO Number": params['po_number'],
                    "Email Subject": inv.get('email_subject', '')[:60] + '...',
                    "Sender": inv.get('sender', ''),
                    "Date": inv.get('date', ''),
                    "Filename": inv.get('filename', ''),
                    "File Path": inv.get('saved_path', ''),
                    "File Size (KB)": f"{(inv.get('size', 0) or 0)/1024:.1f}",
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Select and parse
            st.markdown("### 🔍 Select Invoice to Parse")
            with st.form("parse_invoice_form"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    options = list(range(len(result.get('invoices', []))))
                    selected_index = st.selectbox(
                        "Choose invoice to parse:",
                        options=options,
                        format_func=lambda i: f"{result['invoices'][i]['filename']} - {result['invoices'][i]['email_subject'][:30]}..."
                    )
                with col2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.form_submit_button("🔍 Parse Selected Invoice", type="primary"):
                        inv = result['invoices'][selected_index]
                        st.session_state.parse_invoice_triggered = True
                        st.session_state.parse_invoice_params = {
                            "po_number": params['po_number'],
                            "email_subject": inv.get('email_subject', ''),
                            "sender": inv.get('sender', ''),
                            "filename": inv.get('filename', ''),
                            "file_path": inv.get('saved_path', ''),
                            "email_date": inv.get('date', ''),
                        }

        # Clear button for search
        st.markdown("---")
        if st.button("🗑️ Clear Invoice Search Results", key="clear_invoice_search"):
            st.session_state.invoice_search_triggered = False
            st.session_state.parse_invoice_triggered = False
            st.rerun()

    # Parse selected invoice
    if st.session_state.get('parse_invoice_triggered', False):
        params = st.session_state.parse_invoice_params
        st.markdown("---")
        st.info(f"🧾 Parsing invoice: {params['filename']}")
        # Extract text
        from fileparser import FileParser
        parser = FileParser()
        if not os.path.exists(params['file_path']):
            st.error(f"❌ File not found: {params['file_path']}")
        else:
            parsed = asyncio.run(parser.parse_file_async(params['file_path']))
            if not parsed.get('success'):
                st.error(f"❌ File parsing failed: {parsed.get('error', 'Unknown error')}")
            else:
                raw_text = parsed.get('raw_text', '')
                generator = InvoiceFieldGenerator()
                with st.spinner("Extracting structured invoice fields..."):
                    invoice_data = asyncio.run(generator.generate_async(raw_text, params['filename']))
                if invoice_data.get('success'):
                    st.success(f"✅ Invoice parsed successfully! Confidence: {invoice_data.get('confidence_score', 0):.2f}")
                    # Attach email metadata
                    invoice_data['email_subject'] = params['email_subject']
                    invoice_data['sender'] = params['sender']
                    invoice_data['email_date'] = params['email_date']
                    # Save in DB
                    try:
                        inv_db.save_invoice(params['po_number'], params['filename'], invoice_data)
                        st.success("💾 Saved to invoice database")
                    except Exception as e:
                        st.error(f"❌ Failed to save invoice: {e}")

                    # Display
                    st.markdown("### 📄 Parsed Invoice Summary")
                    cols = st.columns(3)
                    with cols[0]:
                        st.info(f"Invoice #: {invoice_data.get('invoice_number','')}")
                        st.info(f"PO #: {invoice_data.get('po_number','')}")
                        st.info(f"Date: {invoice_data.get('invoice_date','')}")
                    with cols[1]:
                        st.info(f"Supplier: {invoice_data.get('supplier_name','')}")
                        st.info(f"Email: {invoice_data.get('supplier_email','')}")
                    with cols[2]:
                        st.metric("Total", f"{invoice_data.get('total_amount','')} {invoice_data.get('currency','')}")
                        st.metric("Tax", f"{invoice_data.get('tax_amount','')} {invoice_data.get('currency','')}")

                    if invoice_data.get('line_items'):
                        st.markdown("#### 📦 Line Items")
                        st.dataframe(pd.DataFrame(invoice_data['line_items']), use_container_width=True, hide_index=True)

    # View parsed invoices
    st.markdown("## 📊 View Parsed Invoices")
    with st.form("view_parsed_invoices_form"):
        col1, col2 = st.columns(2)
        with col1:
            search_po = st.text_input("Search by PO Number", placeholder="e.g., PO-2024-001")
        with col2:
            only_po = st.checkbox("Show only this PO", value=True)
        if st.form_submit_button("📊 View Invoices", type="secondary"):
            st.session_state.view_invoices_triggered = True
            st.session_state.view_invoices_params = {"search_po": search_po, "only_po": only_po}

    if st.session_state.get('view_invoices_triggered', False):
        st.markdown("---")
        params = st.session_state.view_invoices_params
        invoices = inv_db.get_invoices_by_po(params['search_po']) if params.get('search_po') else inv_db.get_all_invoices()
        if not invoices:
            st.warning("No invoices found.")
        else:
            rows = []
            for inv in invoices:
                rows.append({
                    "PO Number": inv.get('po_number',''),
                    "Invoice #": inv.get('invoice_number',''),
                    "Supplier": inv.get('supplier_name',''),
                    "Total Amount": inv.get('total_amount',''),
                    "Currency": inv.get('currency',''),
                    "Processed Date": inv.get('processed_date',''),
                    "Filename": inv.get('filename',''),
                    "Email Subject": inv.get('email_subject','')[:60] + '...'
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        if st.button("🗑️ Clear Results", key="clear_view_invoices"):
            st.session_state.view_invoices_triggered = False
            st.rerun()

def show_email_search_results(indent_id: str, from_date, to_date):
    """Display email search results with option to parse documents"""
    try:
        from email_parsing_agent import EmailParsingAgent
        
        agent = EmailParsingAgent()
        
        # Add divider and status message
        st.markdown("---")
        st.info(f"📧 Searching email database for indent ID: {indent_id}")
        
        # Get all indent IDs
        indent_ids = agent.get_all_indent_ids()
        
        if not indent_ids:
            st.warning("⚠️ No stored emails found. Run an email scan first.")
            return
        
        # Get quotations for specific indent ID
        quotes_data = agent.get_quotes_by_indent(indent_id)
        
        if 'quotes' not in quotes_data or not quotes_data['quotes']:
            st.warning(f"⚠️ No attachments found for indent ID: {indent_id}")
            return
        
        # Filter by date range
        filtered_quotes = []
        for quote in quotes_data['quotes']:
            try:
                quote_date = datetime.fromisoformat(quote.get('date', ''))
                quote_date_only = quote_date.date()
                
                if from_date <= quote_date_only <= to_date:
                    filtered_quotes.append(quote)
            except:
                # Include if date parsing fails
                filtered_quotes.append(quote)
        
        if not filtered_quotes:
            st.warning(f"⚠️ No attachments found in the date range {from_date} to {to_date} for indent ID: {indent_id}")
            return
        
        st.success(f"✅ Found {len(filtered_quotes)} attachments for indent ID: {indent_id}")
        
        # Display results in a table
        st.markdown("### 📧 Email Attachments Found")
        
        # Create DataFrame for display
        display_data = []
        for quote in filtered_quotes:
            display_data.append({
                'Email Subject': quote.get('email_subject', 'Unknown')[:50] + '...',
                'Sender': quote.get('sender', 'Unknown'),
                'Date': datetime.fromisoformat(quote.get('date', '')).strftime('%Y-%m-%d %H:%M'),
                'Filename': quote.get('filename', 'Unknown'),
                'File Path': quote.get('saved_path', 'N/A'),
                'File Size (KB)': f"{quote.get('size', 0) / 1024:.1f}" if quote.get('size') else 'N/A'
            })
        
        df = pd.DataFrame(display_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Parse options
        st.markdown("### 🔍 Select Document to Parse")
        
        # Create selection interface
        with st.form("parse_selection_form"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                selected_index = st.selectbox(
                    "Choose document to parse:",
                    options=range(len(filtered_quotes)),
                    format_func=lambda x: f"{filtered_quotes[x]['filename']} - {filtered_quotes[x]['email_subject'][:30]}...",
                    help="Select a document to parse with AI"
                )
            
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("🔍 Parse Selected Document", type="primary"):
                    if 0 <= selected_index < len(filtered_quotes):
                        selected_quote = filtered_quotes[selected_index]
                        st.session_state.parse_document_triggered = True
                        st.session_state.parse_document_params = {
                            'indent_id': indent_id,
                            'email_subject': selected_quote['email_subject'],
                            'sender': selected_quote['sender'],
                            'filename': selected_quote['filename'],
                            'file_path': selected_quote['saved_path'],
                            'email_date': selected_quote['date']
                        }
        
        # Parse the selected document
        if st.session_state.get('parse_document_triggered', False):
            parse_selected_document(
                st.session_state.parse_document_params['indent_id'],
                st.session_state.parse_document_params['email_subject'],
                st.session_state.parse_document_params['sender'],
                st.session_state.parse_document_params['filename'],
                st.session_state.parse_document_params['file_path'],
                st.session_state.parse_document_params['email_date']
            )
        
        # Add clear results button
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🗑️ Clear Search Results", key="clear_email_search_results"):
                st.session_state.search_email_triggered = False
                st.session_state.parse_document_triggered = False
                st.rerun()
        
    except Exception as e:
        st.error(f"❌ Error searching email database: {str(e)}")

def parse_selected_document(indent_id: str, email_subject: str, sender: str, filename: str, file_path: str, email_date: str):
    """Parse the selected document from email database"""
    try:
        from quotation_parsing_agent import QuotationFieldGenerator, QuotationDatabase
        from fileparser import FileParser
        
        # Initialize components
        generator = QuotationFieldGenerator()
        database = QuotationDatabase()
        file_parser = FileParser()
        
        # Add divider and status message
        st.markdown("---")
        st.info(f"📋 Parsing document: {filename}")
        st.info(f"📧 From: {sender}")
        st.info(f"📅 Email Date: {datetime.fromisoformat(email_date).strftime('%Y-%m-%d %H:%M')}")
        
        # Parse file content
        with st.spinner("Extracting text from document..."):
            # Check if file exists
            if not os.path.exists(file_path):
                st.error(f"❌ File not found: {file_path}")
                return
            
            # Check file size
            file_size = os.path.getsize(file_path)
            st.info(f"📄 File size: {file_size / 1024:.1f} KB")
            
            parsed_data = asyncio.run(file_parser.parse_file_async(file_path))
            
            if not parsed_data.get('success', False):
                st.error(f"❌ File parsing failed: {parsed_data.get('error', 'Unknown error')}")
                return
            
            raw_text = parsed_data.get('raw_text', '')
            
            if not raw_text.strip():
                st.error("❌ No text content extracted from file")
                return
        
        # Extract structured quotation data
        with st.spinner("Extracting structured data..."):
            quotation_data = asyncio.run(generator.generate_async(raw_text, filename))
            
            if quotation_data.get('success', False):
                st.success(f"✅ Quotation parsed successfully! Confidence: {quotation_data.get('confidence_score', 0):.2f}")
                
                # Add email metadata to quotation data
                quotation_data['email_subject'] = email_subject
                quotation_data['sender'] = sender
                quotation_data['email_date'] = email_date
                
                # Save to database
                try:
                    if database.save_quotation(indent_id, filename, quotation_data):
                        st.success(f"✅ Quotation saved to database")
                    else:
                        st.error("❌ Failed to save quotation to database")
                        st.info("💡 Check the console/logs for detailed error information")
                except Exception as db_error:
                    st.error(f"❌ Database error: {str(db_error)}")
                    st.info("💡 Check the console/logs for detailed error information")
                
                # Display extracted data
                display_quotation_data(quotation_data)
                
            else:
                st.error(f"❌ Quotation parsing failed: {quotation_data.get('error', 'Unknown error')}")
            
    except Exception as e:
        st.error(f"❌ Error parsing document: {str(e)}")

def display_quotation_data(quotation_data: Dict[str, Any]):
    """Display extracted quotation data in a structured format"""
    
    # Main quotation details
    st.markdown("### 📋 Extracted Quotation Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Supplier Information")
        if quotation_data.get('supplier_name'):
            st.info(f"**Supplier:** {quotation_data['supplier_name']}")
        if quotation_data.get('supplier_contact'):
            st.info(f"**Contact:** {quotation_data['supplier_contact']}")
        if quotation_data.get('supplier_email'):
            st.info(f"**Email:** {quotation_data['supplier_email']}")
        if quotation_data.get('supplier_phone'):
            st.info(f"**Phone:** {quotation_data['supplier_phone']}")
    
    with col2:
        st.markdown("#### Client Information")
        if quotation_data.get('client_name'):
            st.info(f"**Client:** {quotation_data['client_name']}")
        if quotation_data.get('client_contact'):
            st.info(f"**Contact:** {quotation_data['client_contact']}")
        if quotation_data.get('delivery_location'):
            st.info(f"**Delivery:** {quotation_data['delivery_location']}")
    
    # Financial information
    st.markdown("#### 💰 Financial Details")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if quotation_data.get('total_amount'):
            st.metric("Total Amount", f"{quotation_data['total_amount']} {quotation_data.get('currency', '')}")
    
    with col2:
        if quotation_data.get('tax_amount'):
            st.metric("Tax Amount", f"{quotation_data['tax_amount']} {quotation_data.get('currency', '')}")
    
    with col3:
        if quotation_data.get('discount_amount'):
            st.metric("Discount", f"{quotation_data['discount_amount']} {quotation_data.get('currency', '')}")
    
    # Line items
    if quotation_data.get('line_items'):
        st.markdown("#### 📦 Line Items")
        line_items_df = pd.DataFrame(quotation_data['line_items'])
        st.dataframe(line_items_df, use_container_width=True, hide_index=True)
    
    # Terms and conditions
    if quotation_data.get('terms_conditions'):
        st.markdown("#### 📄 Terms & Conditions")
        for i, term in enumerate(quotation_data['terms_conditions'], 1):
            st.markdown(f"{i}. {term}")

def show_parsed_quotations_table(indent_id: str, from_date, to_date):
    """Display parsed quotations from the JSON database"""
    try:
        from quotation_parsing_agent import QuotationDatabase
        
        database = QuotationDatabase()
        
        # Add divider and status message
        st.markdown("---")
        st.info(f"📊 Loading parsed quotations from JSON database...")
        
        # Get database statistics
        stats = database.get_database_stats()
        
        # Display database statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Quotations", stats.get('total_quotations', 0))
        
        with col2:
            st.metric("Unique Indents", stats.get('unique_indents', 0))
        
        with col3:
            st.metric("Unique Suppliers", stats.get('unique_suppliers', 0))
        
        with col4:
            st.metric("Total Value", f"{stats.get('total_value', 0):,.2f}")
        
        # Get quotations based on search criteria
        if indent_id:
            quotations = database.get_quotations_by_indent(indent_id)
            st.info(f"📊 Found {len(quotations)} quotations for indent ID: {indent_id}")
        else:
            quotations = database.get_all_quotations()
            st.info(f"📊 Showing all {len(quotations)} quotations from database")
        
        if not quotations:
            st.warning("⚠️ No parsed quotations found in database")
            return
        
        # Convert to DataFrame format
        all_quotations = []
        for quotation in quotations:
            try:
                # Parse the processed date
                processed_date = datetime.fromisoformat(quotation.get('processed_date', ''))
                
                # Filter by date range if specified
                if from_date and to_date:
                    if not (from_date <= processed_date.date() <= to_date):
                        continue
                
                all_quotations.append({
                    'Indent ID': quotation.get('indent_id', 'Unknown'),
                    'Filename': quotation.get('filename', 'Unknown'),
                    'Email Subject': quotation.get('email_subject', 'Unknown')[:50] + '...',
                    'Sender': quotation.get('sender', 'Unknown'),
                    'Processed Date': processed_date.strftime('%Y-%m-%d %H:%M'),
                    'Quotation Number': quotation.get('quotation_number', 'N/A'),
                    'Supplier Name': quotation.get('supplier_name', 'N/A'),
                    'Client Name': quotation.get('client_name', 'N/A'),
                    'Total Amount': quotation.get('total_amount', 'N/A'),
                    'Currency': quotation.get('currency', 'N/A'),
                    'Confidence Score': f"{quotation.get('confidence_score', 0):.2f}",
                    'Requires Review': 'Yes' if quotation.get('requires_review') else 'No',
                    'Line Items Count': len(quotation.get('line_items', [])),
                    'Terms Count': len(quotation.get('terms_conditions', []))
                })
            except Exception as e:
                # Skip invalid quotations
                continue
        
        if not all_quotations:
            st.warning("⚠️ No valid quotations found in database")
            return
        
        # Display the table
        st.markdown("### 📊 Parsed Quotations Database")
        
        df = pd.DataFrame(all_quotations)
        st.dataframe(
            df,
            column_config={
                "Email Subject": st.column_config.TextColumn("Email Subject", width="medium"),
                "Sender": st.column_config.TextColumn("Sender", width="medium"),
                "Processed Date": st.column_config.DatetimeColumn("Processed Date", format="DD-MM-YYYY HH:mm"),
                "Total Amount": st.column_config.NumberColumn("Total Amount", format="%.2f"),
                "Confidence Score": st.column_config.NumberColumn("Confidence", format="%.2f"),
                "Requires Review": st.column_config.SelectboxColumn("Review", options=["Yes", "No"])
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Show database file info
        st.info(f"💾 Database file: {database.db_path}")
        st.info(f"📅 Database created: {stats.get('database_created', 'Unknown')}")
        st.info(f"🔄 Last updated: {stats.get('last_updated', 'Unknown')}")
        
        # Add clear results button
        if st.button("🗑️ Clear Results", key="clear_parsed_quotations"):
            st.session_state.view_parsed_quotations_triggered = False
            st.rerun()
        
    except Exception as e:
        st.error(f"❌ Error loading parsed quotations: {str(e)}")
        st.info("💡 Check the console/logs for detailed error information")

if __name__ == "__main__":
    main() 