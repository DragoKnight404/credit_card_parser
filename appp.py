import streamlit as st
import fitz  # PyMuPDF
import json
import re
from io import BytesIO
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="Credit Card Statement Parser",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for modern UI
st.markdown("""
    <style>
    /* Global styles */
    .main {
        background-color: #f8f9fa;
    }
    
    /* Header */
    .app-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .app-header h1 {
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .app-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1.1rem;
        margin-top: 0.5rem;
    }
    
    /* Stats cards */
    .stats-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }
    
    .stat-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid;
        transition: transform 0.2s;
    }
    
    .stat-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    }
    
    .stat-card.success { border-left-color: #10b981; }
    .stat-card.warning { border-left-color: #f59e0b; }
    .stat-card.info { border-left-color: #3b82f6; }
    .stat-card.primary { border-left-color: #8b5cf6; }
    
    .stat-value {
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        color: #1f2937;
    }
    
    .stat-label {
        font-size: 0.875rem;
        color: #6b7280;
        margin-top: 0.25rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Statement card */
    .statement-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 1px solid #e5e7eb;
        transition: all 0.3s;
    }
    
    .statement-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    }
    
    .statement-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        cursor: pointer;
        padding: 0.5rem;
        border-radius: 8px;
        transition: background 0.2s;
    }
    
    .statement-header:hover {
        background: #f9fafb;
    }
    
    .bank-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.875rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .bank-hdfc { background: #004C8F; color: white; }
    .bank-icici { background: #F37021; color: white; }
    .bank-sbi { background: #22409A; color: white; }
    .bank-axis { background: #A41E35; color: white; }
    .bank-kotak { background: #ED1C24; color: white; }
    
    .statement-info {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1rem;
        margin-top: 1rem;
        padding: 1rem;
        background: #f9fafb;
        border-radius: 8px;
    }
    
    .info-item {
        display: flex;
        flex-direction: column;
    }
    
    .info-label {
        font-size: 0.75rem;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.25rem;
    }
    
    .info-value {
        font-size: 1rem;
        color: #1f2937;
        font-weight: 500;
    }
    
    .amount-highlight {
        font-size: 1.5rem;
        font-weight: 700;
        color: #8b5cf6;
    }
    
    /* Action buttons */
    .action-buttons {
        display: flex;
        gap: 0.5rem;
        margin-top: 1rem;
    }
    
    .btn-custom {
        padding: 0.5rem 1rem;
        border-radius: 8px;
        border: none;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
        text-decoration: none;
        display: inline-block;
    }
    
    .btn-primary {
        background: #8b5cf6;
        color: white;
    }
    
    .btn-primary:hover {
        background: #7c3aed;
    }
    
    .btn-secondary {
        background: #e5e7eb;
        color: #1f2937;
    }
    
    .btn-secondary:hover {
        background: #d1d5db;
    }
    
    /* Upload section */
    .upload-section {
        background: white;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 2rem;
        border: 2px dashed #d1d5db;
        text-align: center;
    }
    
    /* Transactions table */
    .transaction-table {
        margin-top: 1rem;
        overflow-x: auto;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Helper Functions (same as before)
def extract_text_from_pdf(pdf_file):
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()
        return full_text
    except Exception as e:
        return None

def identify_bank(pdf_text):
    text_lower = pdf_text.lower()
    if "hdfc bank" in text_lower:
        return "HDFC"
    elif "icici bank" in text_lower:
        return "ICICI"
    elif "sbi card" in text_lower:
        return "SBI"
    elif "axis bank" in text_lower:
        return "AXIS"
    elif "kotak mahindra bank" in text_lower:
        return "KOTAK"
    else:
        return "UNKNOWN"

def clean_amount(amount_str):
    if not amount_str:
        return None
    return re.sub(r"[₹,]|Rs\.", "", amount_str).strip()

# Parser Functions (keeping all the original parsers)
def parse_hdfc(pdf_text):
    data = {
        "bank_name": "HDFC",
        "customer_name": None,
        "customer_address": None,
        "card_last_4": None,
        "card_type": None,
        "billing_cycle": None,
        "payment_due_date": None,
        "total_balance_due": None,
        "transactions": []
    }
    
    name_addr_match = re.search(r"((?:Mr|Ms|Mrs)\..*?)\s*Card Number:", pdf_text, re.DOTALL)
    if name_addr_match:
        full_block = name_addr_match.group(1).strip()
        lines = [line.strip() for line in full_block.split('\n') if line.strip()]
        if lines:
            data["customer_name"] = lines[0]
            if len(lines) > 1:
                data["customer_address"] = " ".join(lines[1:])

    match = re.search(r"Card Number: XXXX XXXX XXXX\s*(\d{4})", pdf_text)
    if match:
        data["card_last_4"] = match.group(1)

    match = re.search(r"Card Type:\s*([\w\s]+)\s*Billing Cycle:", pdf_text)
    if match:
        data["card_type"] = match.group(1).strip()

    match = re.search(r"Billing Cycle:\s*([\w\s,-]+)\s*Payment Due Date:", pdf_text, re.DOTALL)
    if match:
        data["billing_cycle"] = match.group(1).strip()

    match = re.search(r"Payment Due Date:\s*([\w\s,]+)\s*Total Balance Due:", pdf_text, re.DOTALL)
    if match:
        data["payment_due_date"] = match.group(1).strip()

    match = re.search(r"Total Balance Due:\s*₹\s*([\d,]+\.\d{2})", pdf_text)
    if match:
        data["total_balance_due"] = clean_amount(match.group(1))
        
    transaction_pattern = re.compile(r"([A-Za-z]{3}\s\d{2},\s\d{4})\s+(.*?)\s+([\d,]+\.\d{2})")
    matches = transaction_pattern.findall(pdf_text)
    
    for match in matches:
        date, description, amount = match
        if description.lower() != "transaction details" and "total balance due:" not in description.lower():
            data["transactions"].append({
                "date": date.strip(),
                "description": description.strip(),
                "amount": clean_amount(amount)
            })
            
    return data

def parse_icici(pdf_text):
    data = {
        "bank_name": "ICICI",
        "customer_name": None,
        "customer_address": None,
        "card_last_4": None,
        "card_type": None,
        "billing_cycle": None,
        "payment_due_date": None,
        "total_balance_due": None,
        "transactions": []
    }

    name_addr_match = re.search(r"((?:Mr|Ms|Mrs)\..*?)\s*Statement for Card:", pdf_text, re.DOTALL)
    if name_addr_match:
        full_block = name_addr_match.group(1).strip()
        lines = [line.strip() for line in full_block.split('\n') if line.strip()]
        if lines:
            data["customer_name"] = lines[0]
            if len(lines) > 1:
                data["customer_address"] = " ".join(lines[1:])

    match = re.search(r"Statement for Card:\s*XXXX-(\d{4})", pdf_text)
    if match:
        data["card_last_4"] = match.group(1)

    match = re.search(r"Card:\s*([\w\s]+)\s*Statement Period:", pdf_text, re.DOTALL)
    if match:
        data["card_type"] = match.group(1).strip()

    match = re.search(r"Statement Period:\s*([\d/]+\s+to\s+[\d/]+)", pdf_text)
    if match:
        data["billing_cycle"] = match.group(1).strip()

    match = re.search(r"Due Date:\s*(\d{2}/\d{2}/\d{4})", pdf_text)
    if match:
        data["payment_due_date"] = match.group(1).strip()

    match = re.search(r"Total Due:\s*Rs\.\s*([\d,]+\.\d{2})", pdf_text, re.DOTALL)
    if match:
        data["total_balance_due"] = clean_amount(match.group(1))

    transaction_pattern = re.compile(r"(\d{2}/\d{2}/\d{4})\s+([\w\s]+?)\s+([\d,]+\.\d{2})")
    matches = transaction_pattern.findall(pdf_text)
    
    for match in matches:
        date, description, amount = match
        if description.lower().strip() != "description":
            data["transactions"].append({
                "date": date.strip(),
                "description": description.strip(),
                "amount": clean_amount(amount)
            })

    return data

def parse_sbi(pdf_text):
    data = {
        "bank_name": "SBI",
        "customer_name": None,
        "customer_address": None,
        "card_last_4": None,
        "card_type": None,
        "billing_cycle": None,
        "payment_due_date": None,
        "total_balance_due": None,
        "transactions": []
    }

    name_addr_match = re.search(r"To,\s*(.*?)\s*Card Number", pdf_text, re.DOTALL)
    if name_addr_match:
        full_block = name_addr_match.group(1).strip()
        lines = [line.strip() for line in full_block.split('\n') if line.strip()]
        if lines:
            data["customer_name"] = lines[0]
            if len(lines) > 1:
                data["customer_address"] = " ".join(lines[1:])

    match = re.search(r"Card Number\s*XXXX XXXX XXXX (\d{4})\s*\((.*?)\)", pdf_text, re.DOTALL)
    if match:
        data["card_last_4"] = match.group(1).strip()
        data["card_type"] = match.group(2).strip()

    match = re.search(r"Billing Period\s*(\d{2}-[A-Za-z]{3}-\d{4}\s+to\s+\d{2}-[A-Za-z]{3}-\d{4})", pdf_text, re.DOTALL)
    if match:
        data["billing_cycle"] = match.group(1).strip()

    match = re.search(r"Payment Due Date\s*(\d{2}-[A-Za-z]{3}-\d{4})", pdf_text, re.DOTALL)
    if match:
        data["payment_due_date"] = match.group(1).strip()

    match = re.search(r"Total Amount Due\s*INR\s*([\d,]+\.\d{2})", pdf_text, re.DOTALL)
    if match:
        data["total_balance_due"] = clean_amount(match.group(1))

    transaction_pattern = re.compile(r"(\d{2}-[A-Za-z]{3}-\d{4})\s+(.*?)\s+([\d,]+\.\d{2})")
    matches = transaction_pattern.findall(pdf_text)
    
    for match in matches:
        date, description, amount = match
        if description.lower().strip() not in ["description", "particulars"]:
            data["transactions"].append({
                "date": date.strip(),
                "description": description.strip(),
                "amount": clean_amount(amount)
            })

    return data

def parse_axis(pdf_text):
    data = {
        "bank_name": "AXIS",
        "customer_name": None,
        "customer_address": None,
        "card_last_4": None,
        "card_type": None,
        "billing_cycle": None,
        "payment_due_date": None,
        "total_balance_due": None,
        "transactions": []
    }

    name_addr_match = re.search(r"Credit Card Statement\s*(.*?)\s*Card:", pdf_text, re.DOTALL)
    if name_addr_match:
        full_block = name_addr_match.group(1).strip()
        lines = [line.strip() for line in full_block.split('\n') if line.strip()]
        if lines:
            data["customer_name"] = lines[0]
            if len(lines) > 1:
                data["customer_address"] = " ".join(lines[1:])

    match = re.search(r"Card:\s*([\w\s]+?)\s+ending in\s*(\d{4})", pdf_text, re.DOTALL)
    if match:
        data["card_type"] = match.group(1).strip()
        data["card_last_4"] = match.group(2).strip()

    match = re.search(r"Statement Period\s*([\d/]+\s*-\s*[\d/]+)", pdf_text, re.DOTALL)
    if match:
        data["billing_cycle"] = match.group(1).strip()

    match = re.search(r"Payment Due Date\s*(\d{2}/\d{2}/\d{2})", pdf_text, re.DOTALL)
    if match:
        data["payment_due_date"] = match.group(1).strip()

    match = re.search(r"Total Amount Due\s*₹\s*([\d,]+\.\d{2})", pdf_text, re.DOTALL)
    if match:
        data["total_balance_due"] = clean_amount(match.group(1))

    transaction_pattern = re.compile(r"(\d{2}/\d{2}/\d{2})\s+(.*?)\s+([\d,]+\.\d{2})")
    matches = transaction_pattern.findall(pdf_text)
    
    for match in matches:
        date, description, amount = match
        if description.lower().strip() != "particulars":
            data["transactions"].append({
                "date": date.strip(),
                "description": description.strip(),
                "amount": clean_amount(amount)
            })

    return data

def parse_kotak(pdf_text):
    data = {
        "bank_name": "KOTAK",
        "customer_name": None,
        "customer_address": None,
        "card_last_4": None,
        "card_type": None,
        "billing_cycle": None,
        "payment_due_date": None,
        "total_balance_due": None,
        "transactions": []
    }

    name_addr_match = re.search(r"\*{10,}\s*\n(.*?)\n\s*-{10,}", pdf_text, re.DOTALL)
    if name_addr_match:
        full_block = name_addr_match.group(1).strip()
        all_lines = [line.strip() for line in full_block.split('\n') if line.strip()]
        content_lines = [line for line in all_lines if not line.startswith('*')]
        if content_lines:
            data["customer_name"] = content_lines[0]
            if len(content_lines) > 1:
                data["customer_address"] = " ".join(content_lines[1:])

    match = re.search(r"Card Type\s*:\s*(.*?)\s*Card Number", pdf_text, re.DOTALL)
    if match:
        data["card_type"] = match.group(1).strip()

    match = re.search(r"Card Number\s*:\s*.*?(\d{4})", pdf_text, re.DOTALL)
    if match:
        data["card_last_4"] = match.group(1).strip()

    match = re.search(r"Statement Period\s*:\s*([\d/]+\s*-\s*[\d/]+)", pdf_text, re.DOTALL)
    if match:
        data["billing_cycle"] = match.group(1).strip()

    match = re.search(r"Payment Due Date\s*:\s*(\d{2}/\d{2}/\d{4})", pdf_text, re.DOTALL)
    if match:
        data["payment_due_date"] = match.group(1).strip()

    match = re.search(r"Total Amount Due\s*:\s*Rs\.\s*([\d,]+\.\d{2})", pdf_text, re.DOTALL)
    if match:
        data["total_balance_due"] = clean_amount(match.group(1))

    transaction_pattern = re.compile(r"(\d{2}-[A-Z]{3}-\d{2})\s+(.*?)\s+([\d,]+\.\d{2})")
    matches = transaction_pattern.findall(pdf_text)
    
    for match in matches:
        date, description, amount = match
        if description.lower().strip() != "description":
            data["transactions"].append({
                "date": date.strip(),
                "description": description.strip(),
                "amount": clean_amount(amount)
            })

    return data

# Parser mapping
PARSER_MAP = {
    "HDFC": parse_hdfc,
    "ICICI": parse_icici,
    "SBI": parse_sbi,
    "AXIS": parse_axis,
    "KOTAK": parse_kotak,
}

def render_statement_card(data, index):
    """Render individual statement card with expandable details"""
    bank = data.get('bank_name', 'UNKNOWN')
    bank_class = f"bank-{bank.lower()}"
    
    # Create expander for each statement
    with st.expander(f"**{bank}** • {data.get('customer_name', 'N/A')} • Card ending {data.get('card_last_4', 'XXXX')}", expanded=False):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"""
            <div class="statement-info">
                <div class="info-item">
                    <div class="info-label">Customer Name</div>
                    <div class="info-value">{data.get('customer_name', 'N/A')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Address</div>
                    <div class="info-value">{data.get('customer_address', 'N/A')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Card Type</div>
                    <div class="info-value">{data.get('card_type', 'N/A')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Card Number</div>
                    <div class="info-value">XXXX XXXX XXXX {data.get('card_last_4', 'XXXX')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Billing Cycle</div>
                    <div class="info-value">{data.get('billing_cycle', 'N/A')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Payment Due Date</div>
                    <div class="info-value">{data.get('payment_due_date', 'N/A')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; color: white;">
                <div style="font-size: 0.875rem; opacity: 0.9; margin-bottom: 0.5rem;">TOTAL AMOUNT DUE</div>
                <div style="font-size: 2rem; font-weight: 700;">₹{data.get('total_balance_due', '0.00')}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Transactions
        if data.get('transactions'):
            st.markdown("### 📋 Transactions")
            df = pd.DataFrame(data['transactions'])
            df['amount'] = df['amount'].astype(float)
            st.dataframe(
                df.style.format({'amount': '₹{:.2f}'}),
                width='stretch',
                hide_index=True
            )
            
            # Transaction visualization
            if len(df) > 0:
                col1, col2 = st.columns(2)
                with col1:
                    fig = px.bar(df, x='description', y='amount', 
                                title='Transaction Amounts',
                                labels={'amount': 'Amount (₹)', 'description': 'Transaction'})
                    fig.update_layout(xaxis_tickangle=-45, height=300)
                    st.plotly_chart(fig, width='stretch')
                
                with col2:
                    fig = px.pie(df, values='amount', names='description',
                               title='Spending Distribution')
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, width='stretch')
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            json_str = json.dumps(data, indent=2)
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name=f"{bank}_{data.get('card_last_4', 'statement')}.json",
                mime="application/json",
                key=f"download_{index}",
                width='stretch'
            )
        
        with col2:
            if st.button("👁️ Preview JSON", key=f"preview_{index}", width='stretch'):
                st.json(data)

def create_visualizations(all_data):
    """Create summary visualizations"""
    if not all_data:
        return
    
    st.markdown("## 📊 Data Insights")
    
    # Bank distribution
    banks = [d.get('bank_name', 'UNKNOWN') for d in all_data]
    bank_counts = pd.Series(banks).value_counts()
    
    # Total amounts by bank
    bank_amounts = {}
    for d in all_data:
        bank = d.get('bank_name', 'UNKNOWN')
        amount = float(d.get('total_balance_due', 0) or 0)
        bank_amounts[bank] = bank_amounts.get(bank, 0) + amount
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fig = px.pie(values=bank_counts.values, names=bank_counts.index,
                    title='Statements by Bank',
                    color_discrete_sequence=px.colors.qualitative.Set3)
        fig.update_layout(height=300)
        st.plotly_chart(fig, width='stretch')
    
    with col2:
        fig = px.bar(x=list(bank_amounts.keys()), y=list(bank_amounts.values()),
                    title='Total Due by Bank',
                    labels={'x': 'Bank', 'y': 'Amount (₹)'},
                    color=list(bank_amounts.keys()),
                    color_discrete_sequence=px.colors.qualitative.Bold)
        fig.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig, width='stretch')
    
    with col3:
        # Transaction counts
        txn_counts = {d.get('bank_name', 'UNKNOWN'): len(d.get('transactions', [])) for d in all_data}
        fig = px.bar(x=list(txn_counts.keys()), y=list(txn_counts.values()),
                    title='Transaction Count by Bank',
                    labels={'x': 'Bank', 'y': 'Transactions'},
                    color=list(txn_counts.keys()),
                    color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig, width='stretch')
    
    # All transactions timeline
    all_transactions = []
    for d in all_data:
        for txn in d.get('transactions', []):
            all_transactions.append({
                'bank': d.get('bank_name'),
                'date': txn.get('date'),
                'description': txn.get('description'),
                'amount': float(txn.get('amount', 0) or 0)
            })
    
    if all_transactions:
        st.markdown("### 📈 All Transactions Overview")
        df_all = pd.DataFrame(all_transactions)
        
        col1, col2 = st.columns(2)
        with col1:
            top_spending = df_all.nlargest(10, 'amount')
            fig = px.bar(top_spending, x='amount', y='description',
                        title='Top 10 Transactions',
                        labels={'amount': 'Amount (₹)', 'description': 'Transaction'},
                        color='bank',
                        orientation='h')
            fig.update_layout(height=400)
            st.plotly_chart(fig, width='stretch')
        
        with col2:
            bank_spending = df_all.groupby('bank')['amount'].sum().reset_index()
            fig = px.treemap(bank_spending, path=['bank'], values='amount',
                           title='Spending by Bank (Treemap)')
            fig.update_layout(height=400)
            st.plotly_chart(fig, width='stretch')

def main():
    # Header
    st.markdown("""
    <div class="app-header">
        <h1>💳 Credit Card Statement Parser</h1>
        <p>Upload PDF statements • Get structured data • Visualize insights</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'parsed_data' not in st.session_state:
        st.session_state.parsed_data = []
    
    # Upload section
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "📁 Drop your PDF files here or click to browse",
        type="pdf",
        accept_multiple_files=True,
        help="Supports HDFC, ICICI, SBI, Axis, and Kotak Mahindra Bank statements"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Process uploaded files
    if uploaded_files:
        if st.button("🚀 Parse Statements", type="primary", width='stretch'):
            st.session_state.parsed_data = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            successful = 0
            failed = 0
            unknown = 0
            
            for idx, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Processing {uploaded_file.name}...")
                
                # Extract text
                text = extract_text_from_pdf(uploaded_file)
                
                if not text:
                    failed += 1
                    continue
                
                # Identify bank
                bank_id = identify_bank(text)
                
                if bank_id == "UNKNOWN":
                    unknown += 1
                    continue
                
                # Parse data
                parser_function = PARSER_MAP[bank_id]
                extracted_data = parser_function(text)
                st.session_state.parsed_data.append(extracted_data)
                successful += 1
                
                # Update progress
                progress_bar.progress((idx + 1) / len(uploaded_files))
            
            status_text.empty()
            progress_bar.empty()
            
            # Show summary
            if successful > 0:
                st.success(f"✅ Successfully parsed {successful} statement(s)!")
            if failed > 0:
                st.warning(f"⚠️ Failed to process {failed} file(s)")
            if unknown > 0:
                st.warning(f"⚠️ Could not identify bank for {unknown} file(s)")
    
    # Display results if data exists
    if st.session_state.parsed_data:
        # Statistics cards
        total_statements = len(st.session_state.parsed_data)
        total_due = sum(float(d.get('total_balance_due', 0) or 0) for d in st.session_state.parsed_data)
        total_transactions = sum(len(d.get('transactions', [])) for d in st.session_state.parsed_data)
        unique_banks = len(set(d.get('bank_name') for d in st.session_state.parsed_data))
        
        st.markdown("""
        <div class="stats-container">
            <div class="stat-card success">
                <div class="stat-value">{}</div>
                <div class="stat-label">Statements Parsed</div>
            </div>
            <div class="stat-card primary">
                <div class="stat-value">₹{:,.2f}</div>
                <div class="stat-label">Total Amount Due</div>
            </div>
            <div class="stat-card info">
                <div class="stat-value">{}</div>
                <div class="stat-label">Total Transactions</div>
            </div>
            <div class="stat-card warning">
                <div class="stat-value">{}</div>
                <div class="stat-label">Banks</div>
            </div>
        </div>
        """.format(total_statements, total_due, total_transactions, unique_banks), unsafe_allow_html=True)
        
        # Visualizations
        create_visualizations(st.session_state.parsed_data)
        
        # Statement cards
        st.markdown("## 📑 Parsed Statements")
        
        # Download all button
        col1, col2 = st.columns([3, 1])
        with col2:
            all_json = json.dumps(st.session_state.parsed_data, indent=2)
            st.download_button(
                label="📥 Download All as JSON",
                data=all_json,
                file_name="all_statements.json",
                mime="application/json",
                width='stretch',
                type="primary"
            )
        
        # Render each statement card
        for idx, data in enumerate(st.session_state.parsed_data):
            render_statement_card(data, idx)
        
        # Clear button
        st.markdown("---")
        if st.button("🗑️ Clear All Data", width='stretch'):
            st.session_state.parsed_data = []
            st.rerun()
    else:
        # Empty state
        st.markdown("""
        <div style="text-align: center; padding: 4rem 2rem; color: #6b7280;">
            <div style="font-size: 4rem; margin-bottom: 1rem;">📄</div>
            <h3 style="color: #374151;">No statements parsed yet</h3>
            <p>Upload your credit card statement PDFs above to get started</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()