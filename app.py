import streamlit as st
import fitz  # PyMuPDF
import json
import re
from io import BytesIO
import pandas as pd

# Set page config
st.set_page_config(
    page_title="Credit Card Statement Parser",
    page_icon="💳",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Helper Functions
def extract_text_from_pdf(pdf_file):
    """Opens a PDF and returns all text from all pages."""
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()
        return full_text
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return None

def identify_bank(pdf_text):
    """Analyzes the text to identify which bank parser to use."""
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
    """Removes commas, '₹', and 'Rs.' from a string to get a clean number."""
    if not amount_str:
        return None
    return re.sub(r"[₹,]|Rs\.", "", amount_str).strip()

# Parser Functions
def parse_hdfc(pdf_text):
    """Extracts data specifically from an HDFC statement."""
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
    """Extracts data specifically from an ICICI statement."""
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
    """Extracts data specifically from an SBI statement."""
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
    """Extracts data specifically from an Axis statement."""
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
    """Extracts data specifically from a Kotak statement."""
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

# Streamlit App
def main():
    st.markdown('<div class="main-header">💳 Credit Card Statement Parser</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
    <b>Supported Banks:</b> HDFC, ICICI, SBI, Axis, Kotak Mahindra<br>
    <b>Upload your credit card statement PDF</b> and get structured data with transactions.
    </div>
    """, unsafe_allow_html=True)
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose PDF file(s)",
        type="pdf",
        accept_multiple_files=True,
        help="Upload one or more credit card statement PDFs"
    )
    
    if uploaded_files:
        all_extracted_data = []
        
        for uploaded_file in uploaded_files:
            st.markdown(f"### 📄 Processing: {uploaded_file.name}")
            
            with st.spinner(f"Extracting data from {uploaded_file.name}..."):
                # Extract text
                text = extract_text_from_pdf(uploaded_file)
                
                if not text:
                    st.error(f"❌ Could not extract text from {uploaded_file.name}")
                    continue
                
                # Identify bank
                bank_id = identify_bank(text)
                
                if bank_id == "UNKNOWN":
                    st.warning(f"⚠️ Could not identify bank for {uploaded_file.name}")
                    continue
                
                # Parse data
                parser_function = PARSER_MAP[bank_id]
                extracted_data = parser_function(text)
                all_extracted_data.append(extracted_data)
                
                # Display success
                st.markdown(f'<div class="success-box">✅ Successfully parsed {bank_id} statement</div>', unsafe_allow_html=True)
                
                # Display extracted data
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 📋 Account Details")
                    st.write(f"**Bank:** {extracted_data.get('bank_name', 'N/A')}")
                    st.write(f"**Customer:** {extracted_data.get('customer_name', 'N/A')}")
                    st.write(f"**Address:** {extracted_data.get('customer_address', 'N/A')}")
                    st.write(f"**Card (Last 4):** {extracted_data.get('card_last_4', 'N/A')}")
                
                with col2:
                    st.markdown("#### 💰 Statement Summary")
                    st.write(f"**Card Type:** {extracted_data.get('card_type', 'N/A')}")
                    st.write(f"**Billing Cycle:** {extracted_data.get('billing_cycle', 'N/A')}")
                    st.write(f"**Payment Due:** {extracted_data.get('payment_due_date', 'N/A')}")
                    st.write(f"**Total Due:** ₹{extracted_data.get('total_balance_due', 'N/A')}")
                
                # Display transactions
                if extracted_data.get('transactions'):
                    st.markdown("#### 🧾 Transactions")
                    df = pd.DataFrame(extracted_data['transactions'])
                    st.dataframe(df, width='stretch')
                    st.write(f"**Total Transactions:** {len(extracted_data['transactions'])}")
                else:
                    st.info("No transactions found in this statement")
                
                st.markdown("---")
        
        # Download button for all extracted data
        if all_extracted_data:
            st.markdown("### 📥 Download Results")
            
            json_str = json.dumps(all_extracted_data, indent=2)
            
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                st.download_button(
                    label="📥 Download JSON",
                    data=json_str,
                    file_name="credit_card_statements.json",
                    mime="application/json",
                    width='stretch'
                )
            
            with col2:
                if st.button("👁️ Preview JSON", width='stretch'):
                    st.session_state.show_json = not st.session_state.get('show_json', False)
            
            if st.session_state.get('show_json', False):
                st.markdown("#### JSON Preview")
                st.json(all_extracted_data)

if __name__ == "__main__":
    if 'show_json' not in st.session_state:
        st.session_state.show_json = False
    main()