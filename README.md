# Credit Card Statement Parser: Solution Documentation

## 1. Project Overview

**Objective:** The goal of this assignment was to build a PDF parser to extract 5 key data points from the credit card statements of 5 different major issuers.

**Solution:** I have successfully built a complete Python-based parsing pipeline that meets and exceeds this requirement. The solution identifies and parses 5 different bank statement formats (HDFC, ICICI, SBI, Axis, and Kotak) and extracts 8+ key data points into a single, standardized JSON schema.

This backend pipeline is demonstrated through a live Streamlit web application where any of the supported PDF statements can be uploaded. The app presents the extracted, structured data and provides a direct download of the resulting JSON.

## 2. Core Solution Architecture: The "Identifier/Router" Model

The central challenge is that each bank's statement is fundamentally different. A pattern that finds the "Total Due" in an HDFC statement will fail on an SBI statement.

To solve this, I designed a modular, two-stage pipeline. This approach avoids the fragility of a single, complex parser and instead relies on a "separation of concerns."

**Stage 1: The Identifier (Router)**
This is a single, lightweight function. Its only job is to perform a rapid "fingerprint" check on the PDF's raw text to determine its source. It looks for unique, high-confidence keywords (e.g., "HDFC Bank", "SBI Card", "Kotak Mahindra Bank").

**Stage 2: The Specialist Parsers (Workers)**
This is a collection of bank-specific parsing functions (e.g., `parse_hdfc()`, `parse_icici()`). Each parser is a "specialist," built only to understand the layout of its specific bank.

When a PDF is processed, the Identifier routes the task to the correct Specialist Parser. This makes the entire system predictable, maintainable, and easy to debug.

## 3. The Data Pipeline (Step-by-Step)

The full process, from upload to JSON, is as follows:

1. **PDF Upload:** The user provides a PDF file via the Streamlit frontend.
2. **Text Extraction:** The system uses the PyMuPDF (fitz) library to extract raw text from all pages of the PDF. This library was chosen for its high speed and accuracy in handling PDF text layouts.
3. **Bank Identification (Routing):** The raw text is passed to the `identify_bank()` function. This function quickly returns an ID, such as "HDFC" or "SBI".
4. **Specialized Parsing:** The system uses a "parser map" (a Python dictionary) to call the corresponding function (e.g., `PARSER_MAP["HDFC"]`).
5. **Regex Extraction:** This specialist function executes a set of fine-tuned Regular Expressions (Regex) designed specifically for its layout. It extracts each data point (name, address, transactions, etc.).
6. **Standardization:** All extracted data is formatted and poured into a single, standard Python dictionary. This ensures the final output is always clean and predictable, regardless of the PDF source.
7. **Output:** The standardized dictionary is converted to a JSON object and presented to the user.

## 4. Design Rationale: Why Regex over an LLM?

While a modern LLM could theoretically extract data from a PDF, it is a sub-optimal tool for this task. The regex-based pipeline I built is superior for several key reasons:

- **Speed:** The entire process is blazing fast. Regex matching is computationally trivial and runs instantly, whereas an LLM requires a slow and heavy API call for each PDF.
- **Cost:** This solution is zero-cost. It runs locally with no API fees. An LLM-based solution would be expensive to run at any scale.
- **Reliability:** The regex parser is 100% deterministic. It will either find the data or fail predictably. An LLM is non-deterministic and can "hallucinate" or miss data, making it a reliability risk for financial information.
- **Maintainability:** When a bank (e.g., HDFC) inevitably changes its statement format, this architecture is trivial to update. I only need to debug and update the `parse_hdfc()` function. With an LLM, the entire "black box" model would fail, with no clear path to a fix.

This lightweight, specialist-based approach is far more robust, efficient, and professional for a production environment.

## 5. Standardized Data Schema

To prove the system's effectiveness, I defined a standard schema for 8+ data points. All parsers are required to return this exact structure, filling fields with `None` if they aren't found.

```json
{
  "bank_name": "HDFC",
  "customer_name": "Mr. Rohan Sharma",
  "customer_address": "123, Marine Drive Mumbai, MH 400020",
  "card_last_4": "1234",
  "card_type": "HDFC Regalia Gold",
  "billing_cycle": "Oct 05, 2025 - Nov 04, 2025",
  "payment_due_date": "Nov 24, 2025",
  "total_balance_due": "45678.90",
  "transactions": [
    {
      "date": "Oct 08, 2025",
      "description": "ZOMATO ONLINE",
      "amount": "780.00"
    },
    {
      "date": "Oct 10, 2025",
      "description": "AMAZON INDIA PVT LTD",
      "amount": "12500.00"
    }
  ]
}
```
## 6. Scalability & Future Work

The system's modular architecture is its greatest strength. To add support for a 6th bank (e.g., American Express):

- Add `elif "american express" in text_lower: return "AMEX"` to the Identifier.
- Write a new specialist function, `parse_amex(text)`, containing the regex for Amex cards.
- Add the new function to the main parser map: `"AMEX": parse_amex`.

The core logic remains untouched. This design demonstrates a scalable, maintainable, and highly functional solution to the problem.