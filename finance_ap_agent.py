import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import streamlit as st
import pandas as pd

from invoice_email_parsing_agent import InvoiceEmailParsingAgent
from invoice_parsing_module import InvoiceFieldGenerator, InvoiceDatabase
from grn_parsing_module import GRNFieldGenerator
from dc_parsing_module import DCFieldGenerator
from ewaybill_parsing_module import EWayBillFieldGenerator

# Optional additional parsers can be swapped in later if needed


class FinanceAPDatabase:
    def __init__(self, db_path: str = "finance_ap_database.json"):
        self.db_path = db_path
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        self._init()

    def _init(self):
        if not os.path.exists(self.db_path):
            data = {
                "ap_documents": {},
                "metadata": {
                    "created_date": datetime.now().isoformat(),
                    "version": "1.0",
                    "total_records": 0,
                },
            }
            self._save(data)

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "ap_documents": {},
                "metadata": {"created_date": datetime.now().isoformat(), "version": "1.0", "total_records": 0},
            }

    def _save(self, data: Dict[str, Any]):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def save_record(self, po_number: str, doc_type: str, filename: str, payload: Dict[str, Any]) -> bool:
        data = self._load()
        key = f"{po_number}_{doc_type}_{filename}"
        payload.update({
            "po_number": po_number,
            "doc_type": doc_type,
            "filename": filename,
            "processed_date": datetime.now().isoformat(),
            "record_key": key,
        })
        data["ap_documents"][key] = payload
        data["metadata"]["total_records"] = len(data["ap_documents"])
        data["metadata"]["last_updated"] = datetime.now().isoformat()
        self._save(data)
        return True

    def get_by_po(self, po_number: str) -> List[Dict[str, Any]]:
        data = self._load()
        return [r for r in data["ap_documents"].values() if r.get("po_number") == po_number]

    def get_all(self) -> List[Dict[str, Any]]:
        data = self._load()
        return list(data["ap_documents"].values())


def _three_way_match(invoice: Dict[str, Any], po_lines: List[Dict[str, Any]], grn_lines: Optional[List[Dict[str, Any]]] = None,
                     qty_tol: float = 0.02, price_tol: float = 0.01) -> Dict[str, Any]:
    """Perform a simplified 3-way match using invoice vs PO (and GRN if provided)."""
    # NOTE: In this generalized agent, PO/GRN structured data would come from ERP integrations.
    # For now, we match invoice lines internally (self-consistency) and surface placeholders.
    results = {
        "po_number": invoice.get("po_number"),
        "invoice_number": invoice.get("invoice_number"),
        "summary": {
            "lines_evaluated": 0,
            "qty_variance_count": 0,
            "price_variance_count": 0,
            "missing_grn_count": 0,
            "flags": []
        },
        "lines": []
    }

    invoice_lines = invoice.get("line_items", []) or []
    # Placeholder PO lines: if not provided, assume invoice is reference baseline
    if not po_lines:
        po_lines = []
        for l in invoice_lines:
            po_lines.append({
                "item_code": l.get("item_code") or l.get("item_number") or l.get("description"),
                "description": l.get("description"),
                "quantity": l.get("quantity"),
                "unit_price": l.get("unit_price"),
                "uom": l.get("uom"),
            })

    for inv in invoice_lines:
        code = inv.get("item_code") or inv.get("item_number") or inv.get("description")
        qty = (inv.get("quantity") or 0) * 1.0
        price = (inv.get("unit_price") or 0) * 1.0

        # naive find in po_lines by code/description
        po_match = next((p for p in po_lines if (p.get("item_code") == code or p.get("description") == inv.get("description"))), None)

        grn_qty = None
        if grn_lines:
            grn_match = next((g for g in grn_lines if (g.get("item_code") == code or g.get("description") == inv.get("description"))), None)
            if grn_match:
                grn_qty = grn_match.get("quantity")

        qty_ok = True
        price_ok = True
        flags: List[str] = []

        if po_match:
            po_qty = (po_match.get("quantity") or 0) * 1.0
            po_price = (po_match.get("unit_price") or 0) * 1.0
            if po_qty:
                qty_var = abs(qty - po_qty) / max(po_qty, 1e-6)
                if qty_var > qty_tol:
                    qty_ok = False
                    flags.append("Quantity variance")
            if po_price:
                price_var = abs(price - po_price) / max(po_price, 1e-6)
                if price_var > price_tol:
                    price_ok = False
                    flags.append("Price variance")
        else:
            flags.append("Line not found in PO")

        if grn_lines is not None:
            if grn_qty is None:
                flags.append("Missing GRN line")
            else:
                # Optional: quantity vs GRN check
                pass

        results["summary"]["lines_evaluated"] += 1
        if not qty_ok:
            results["summary"]["qty_variance_count"] += 1
        if not price_ok:
            results["summary"]["price_variance_count"] += 1
        if grn_lines is not None and grn_qty is None:
            results["summary"]["missing_grn_count"] += 1
        results["lines"].append({
            "item": code,
            "description": inv.get("description"),
            "invoice_qty": qty,
            "invoice_price": price,
            "flags": ", ".join(flags)
        })

    # Aggregate flags
    if results["summary"]["qty_variance_count"] > 0:
        results["summary"]["flags"].append("Quantity variances detected")
    if results["summary"]["price_variance_count"] > 0:
        results["summary"]["flags"].append("Price variances detected")
    if results["summary"]["missing_grn_count"] > 0:
        results["summary"]["flags"].append("Missing GRN lines")

    return results


def show_ap_automation_agent():
    st.markdown("""
    <div class="main-header">
        <h1 class="header-title">🏦 Accounts Payable Automation Agent</h1>
        <p class="header-subtitle">Finance - Parse finance documents from email and perform 3-way match</p>
    </div>
    """, unsafe_allow_html=True)

    # Back button
    if st.button("← Back to Finance Department", key="back_to_finance_dept"):
        st.session_state.show_finance_ap_agent = False
        st.session_state.show_finance_dept = True
        st.rerun()

    # Config section mirrors other agents
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
        if st.button("⚙️ Configure Email", key="config_email_fin", type="primary"):
            st.session_state.show_email_config = True
            st.session_state.show_finance_ap_agent = False
            st.rerun()

    # Step 1: Select PO Number
    st.markdown("### 📋 Step 1: Select PO Number")
    po_number = st.text_input("PO Number", placeholder="e.g., PO-2024-001")
    if not po_number:
        st.info("Enter a PO number to continue.")
        return

    # Step 2: Scan Email by PO
    st.markdown("### 📧 Step 2: Scan Email for Finance Documents (Invoices/GRN/DC/E-Way Bill)")
    if st.button("🔍 Scan Email by PO", key="scan_fin_docs", type="primary"):
        agent = InvoiceEmailParsingAgent()
        with st.spinner("Scanning mailbox..."):
            result = asyncio.run(agent.process_emails_by_po(po_number))
        if result and not result.get('error'):
            st.success(f"Found {result.get('total_invoices', 0)} attachments tagged to PO {po_number}")
            st.session_state.fin_scan_result = result
        else:
            st.error(f"Scan error: {result.get('error','Unknown error') if result else 'Unknown'}")

    # Display results
    scan = st.session_state.get('fin_scan_result')
    if scan and scan.get('invoices'):
        rows = []
        for inv in scan['invoices']:
            rows.append({
                "Email Subject": inv.get('email_subject','')[:60] + '...',
                "Sender": inv.get('sender',''),
                "Date": inv.get('date',''),
                "Filename": inv.get('filename',''),
                "Path": inv.get('saved_path',''),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # Step 3: Parse Selected Documents
        st.markdown("### 🧾 Step 3: Parse Documents")
        options = [f"{i+1}. {r['filename']}" for i, r in enumerate(scan['invoices'])]
        to_parse = st.multiselect("Select documents to parse:", options=options, default=options)
        if st.button("▶️ Parse Selected", key="parse_selected_fin", type="primary"):
            inv_db = InvoiceDatabase()
            ap_db = FinanceAPDatabase()
            generator = InvoiceFieldGenerator()
            grn_gen = GRNFieldGenerator()
            dc_gen = DCFieldGenerator()
            ewb_gen = EWayBillFieldGenerator()
            from fileparser import FileParser
            parser = FileParser()
            parsed_invoices: List[Dict[str, Any]] = []
            for opt in to_parse:
                idx = int(opt.split('.')[0]) - 1
                rec = scan['invoices'][idx]
                path = rec.get('saved_path','')
                if not os.path.exists(path):
                    st.warning(f"Missing file: {path}")
                    continue
                parsed = asyncio.run(parser.parse_file_async(path))
                if not parsed.get('success'):
                    st.warning(f"Parse error: {parsed.get('error','Unknown error')}")
                    continue
                raw_text = parsed.get('raw_text','')
                filename = rec.get('filename','unknown').lower()
                # Route by filename keywords (basic heuristic)
                if any(k in filename for k in ["invoice", "inv", ".pdf", ".docx", ".xlsx"]):
                    inv = asyncio.run(generator.generate_async(raw_text, rec.get('filename','unknown')))
                    if inv.get('success'):
                        inv['email_subject'] = rec.get('email_subject','')
                        inv['sender'] = rec.get('sender','')
                        inv['email_date'] = rec.get('date','')
                        inv_db.save_invoice(po_number, rec.get('filename',''), inv)
                        ap_db.save_record(po_number, 'invoice', rec.get('filename',''), inv)
                        parsed_invoices.append(inv)
                if any(k in filename for k in ["grn", "goodsreceipt", "goods_receipt"]):
                    grn = asyncio.run(grn_gen.generate_async(raw_text, rec.get('filename','unknown')))
                    if grn.get('success'):
                        grn['email_subject'] = rec.get('email_subject','')
                        grn['sender'] = rec.get('sender','')
                        grn['email_date'] = rec.get('date','')
                        ap_db.save_record(po_number, 'grn', rec.get('filename',''), grn)
                if any(k in filename for k in ["challan", "dc_"]):
                    dc = asyncio.run(dc_gen.generate_async(raw_text, rec.get('filename','unknown')))
                    if dc.get('success'):
                        dc['email_subject'] = rec.get('email_subject','')
                        dc['sender'] = rec.get('sender','')
                        dc['email_date'] = rec.get('date','')
                        ap_db.save_record(po_number, 'delivery_challan', rec.get('filename',''), dc)
                if any(k in filename for k in ["eway", "e-way", "ewaybill"]):
                    ewb = asyncio.run(ewb_gen.generate_async(raw_text, rec.get('filename','unknown')))
                    if ewb.get('success'):
                        ewb['email_subject'] = rec.get('email_subject','')
                        ewb['sender'] = rec.get('sender','')
                        ewb['email_date'] = rec.get('date','')
                        ap_db.save_record(po_number, 'eway_bill', rec.get('filename',''), ewb)
            if parsed_invoices:
                st.success(f"Parsed {len(parsed_invoices)} invoices")

                # Step 4: 3-way Match (simplified)
                st.markdown("### ✅ Step 4: 3-way Match")
                # Placeholder PO/GRN lines (none). In production, load from ERP/DB.
                for inv in parsed_invoices:
                    # In a full system, fetch PO and GRN lines by PO from ERP/DB and pass below
                    match = _three_way_match(inv, po_lines=[], grn_lines=None)
                    # Save match summary in AP DB
                    FinanceAPDatabase().save_record(po_number, 'match', inv.get('invoice_number') or inv.get('filename','unknown'), match)
                    st.info(f"Invoice {inv.get('invoice_number') or inv.get('filename','')} - Flags: {', '.join(match['summary']['flags']) or 'None'}")
                    # Show lines table
                    line_df = pd.DataFrame(match['lines'])
                    st.dataframe(line_df, use_container_width=True, hide_index=True)

    # View AP Records
    st.markdown("### 📊 View AP Records")
    ap_db = FinanceAPDatabase()
    ap_rows = ap_db.get_by_po(po_number)
    if ap_rows:
        table = []
        for r in ap_rows:
            table.append({
                "Type": r.get('doc_type',''),
                "Invoice #": r.get('invoice_number',''),
                "Supplier": r.get('supplier_name',''),
                "Total": r.get('total_amount',''),
                "Currency": r.get('currency',''),
                "Processed": r.get('processed_date',''),
                "Filename": r.get('filename',''),
            })
        st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)


