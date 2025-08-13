# comparative_analysis_agent.py
import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import os
from quotation_parsing_agent import QuotationDatabase
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComparativeAnalysisAgent:
    """Agent for creating comparative analysis of quotations"""
    
    def __init__(self):
        self.database = QuotationDatabase()
        
        # Standard comparison parameters
        self.standard_parameters = {
            "Basic Information": [
                "item_name_part_no",
                "quotation_number",
                "quotation_date",
                "supplier_name"
            ],

            "Pricing & Cost Structure": [
                "quantity",
                "unit_price",
                "total_price",
                "currency",
                "uom",
                "taxes",
                "freight_pf_charges",
                "insurance",
                "total_landed_cost",
                "currency_code"
            ],
            "Delivery & Logistics": [
                "delivery_location",
                "lead_time_days",
                "delivery_terms_incoterms",
                "partial_delivery_allowed",
                "minimum_order_quantity"
            ],
            "Payment & Commercial Terms": [
                "payment_terms",
                "advance_payment_percent",
                "discount_structure",
                "price_escalation_clause"
            ],
            "Warranty & Service": [
                "warranty_period",
                "warranty_scope",
                "after_sales_support",
                "service_level_agreement",
                "spare_parts_availability"
            ],
            "Quality & Compliance": [
                "compliance_with_specifications",
                "deviation_remarks",
                "certifications",
                "test_reports_attached"
            ],
            "Vendor Assessment": [
                "vendor_rating",
                "past_performance",
                "financial_stability",
                "references_client_list",
                "remarks_notes"
            ]
        }
    
    def get_all_indent_ids(self) -> List[str]:
        """Get all unique indent IDs from the database"""
        try:
            all_quotations = self.database.get_all_quotations()
            indent_ids = list(set(q.get('indent_id') for q in all_quotations if q.get('indent_id')))
            return sorted(indent_ids)
        except Exception as e:
            logger.error(f"Error getting indent IDs: {str(e)}")
            return []
    
    def get_quotations_by_indent(self, indent_id: str) -> List[Dict[str, Any]]:
        """Get all quotations for a specific indent ID"""
        try:
            return self.database.get_quotations_by_indent(indent_id)
        except Exception as e:
            logger.error(f"Error getting quotations for indent {indent_id}: {str(e)}")
            return []
    
    def get_available_parameters(self, quotations: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Get available parameters from the quotations"""
        available_params = {}
        
        # Collect all unique keys from quotations and line items
        all_keys = set()
        
        for quotation in quotations:
            # Add main quotation keys
            all_keys.update(quotation.keys())
            
            # Also collect keys from line items
            if 'line_items' in quotation and quotation['line_items']:
                for line_item in quotation['line_items']:
                    all_keys.update(line_item.keys())
        
        # Map keys to standard parameter categories
        for category, standard_params in self.standard_parameters.items():
            available_params[category] = []
            for param in standard_params:
                if param in all_keys:
                    available_params[category].append(param)
        
        # Add any additional parameters not in standard list
        additional_params = []
        for key in all_keys:
            if not any(key in params for params in self.standard_parameters.values()):
                additional_params.append(key)
        
        if additional_params:
            available_params["Additional Parameters"] = additional_params
        
        return available_params
    
    def create_comparison_table(self, quotations: List[Dict[str, Any]], selected_parameters: List[str]) -> pd.DataFrame:
        """Create comparison table from selected quotations and parameters"""
        try:
            # Prepare data for comparison in the required format
            comparison_data = []
            
            # Get vendor names for column headers
            vendor_names = [q.get('supplier_name', f'Vendor {i+1}') for i, q in enumerate(quotations)]
            
            # Check if we have line items in any quotation
            has_line_items = any('line_items' in q and q['line_items'] for q in quotations)
            
            if has_line_items:
                # Handle line items comparison
                # Get all unique line items across all quotations
                all_line_items = set()
                for quotation in quotations:
                    if 'line_items' in quotation and quotation['line_items']:
                        for line_item in quotation['line_items']:
                            # Combine item number and description
                            item_number = line_item.get('item_number', '')
                            description = line_item.get('description', '')
                            if item_number and description:
                                item_name = f"{item_number} - {description}"
                            elif item_number:
                                item_name = item_number
                            elif description:
                                item_name = description
                            else:
                                item_name = 'Unknown Item'
                            all_line_items.add(item_name)
                
                # Separate line item specific parameters from common parameters
                line_item_specific_params = ['quantity', 'unit_price', 'total_price', 'currency']
                summary_params = ['tax_amount', 'total_amount']  # Parameters to show after all parts
                common_params = [param for param in selected_parameters if param not in line_item_specific_params and param not in summary_params]
                
                # First, add line item specific parameters for each item
                for i, item_name in enumerate(sorted(all_line_items)):
                    # Add empty separator row between different part numbers (except for first item)
                    if i > 0:
                        comparison_data.append({
                            "Item Name / Part No.": "",
                            "Parameter": "",
                            **{vendor: "" for vendor in vendor_names}
                        })
                    
                    # Add part number header row
                    comparison_data.append({
                        "Item Name / Part No.": f"📋 {item_name}",
                        "Parameter": "PART NUMBER DETAILS",
                        **{vendor: "" for vendor in vendor_names}
                    })
                    
                    # Add pricing & cost structure for this line item
                    pricing_params = [p for p in line_item_specific_params if p in selected_parameters]
                    if pricing_params:
                        comparison_data.append({
                            "Item Name / Part No.": item_name,
                            "Parameter": "--- PRICING & COST STRUCTURE ---",
                            **{vendor: "" for vendor in vendor_names}
                        })
                        
                        for param in pricing_params:
                            display_name = param.replace('_', ' ').title()
                            row_data = {
                                "Item Name / Part No.": item_name,
                                "Parameter": display_name
                            }
                            
                            # Add vendor values for this line item and parameter
                            for i, quotation in enumerate(quotations):
                                vendor_name = vendor_names[i]
                                value = 'N/A'
                                
                                # Find the line item in this quotation
                                if 'line_items' in quotation and quotation['line_items']:
                                    for line_item in quotation['line_items']:
                                        line_item_number = line_item.get('item_number', '')
                                        line_item_desc = line_item.get('description', '')
                                        if line_item_number and line_item_desc:
                                            line_item_name = f"{line_item_number} - {line_item_desc}"
                                        elif line_item_number:
                                            line_item_name = line_item_number
                                        elif line_item_desc:
                                            line_item_name = line_item_desc
                                        else:
                                            line_item_name = ''
                                        
                                        if line_item_name == item_name:
                                            # Get the parameter value from the line item
                                            if param in line_item:
                                                value = line_item.get(param, 'N/A')
                                            break
                                
                                row_data[vendor_name] = value
                            
                            comparison_data.append(row_data)
                
                # Add summary parameters (tax amount and total amount) after all parts
                summary_selected_params = [p for p in summary_params if p in selected_parameters]
                if summary_selected_params:
                    for param in summary_selected_params:
                        display_name = param.replace('_', ' ').title()
                        row_data = {
                            "Item Name / Part No.": "",
                            "Parameter": display_name
                        }
                        
                        # Add vendor values from main quotation
                        for i, quotation in enumerate(quotations):
                            vendor_name = vendor_names[i]
                            value = quotation.get(param, '')
                            row_data[vendor_name] = value
                        
                        comparison_data.append(row_data)
                
                # Add empty separator row between summary and basic information
                if summary_selected_params and common_params:
                    comparison_data.append({
                        "Item Name / Part No.": "",
                        "Parameter": "",
                        **{vendor: "" for vendor in vendor_names}
                    })
                
                # Then, add common parameters once at the bottom
                if common_params:
                    # Group common parameters by category
                    common_parameter_groups = {}
                    for param in common_params:
                        # Find which category this parameter belongs to
                        category_found = False
                        for category, standard_params in self.standard_parameters.items():
                            if param in standard_params:
                                if category not in common_parameter_groups:
                                    common_parameter_groups[category] = []
                                common_parameter_groups[category].append(param)
                                category_found = True
                                break
                        
                        # If not found in standard categories, add to Additional Parameters
                        if not category_found:
                            if "Additional Parameters" not in common_parameter_groups:
                                common_parameter_groups["Additional Parameters"] = []
                            common_parameter_groups["Additional Parameters"].append(param)
                    
                    # Add common parameters
                    for category, params in common_parameter_groups.items():
                        if params:
                            # Add category header row
                            comparison_data.append({
                                "Item Name / Part No.": "",
                                "Parameter": f"--- {category.upper()} ---",
                                **{vendor: "" for vendor in vendor_names}
                            })
                            
                            # Add parameters for this category
                            for param in params:
                                # Format the parameter name for display
                                display_name = param.replace('_', ' ').title()
                                
                                # Create row data
                                row_data = {
                                    "Item Name / Part No.": "",
                                    "Parameter": display_name
                                }
                                
                                # Add vendor values from main quotation
                                for i, quotation in enumerate(quotations):
                                    vendor_name = vendor_names[i]
                                    value = quotation.get(param, '')
                                    row_data[vendor_name] = value
                                
                                comparison_data.append(row_data)
                

            else:
                # No line items, use main quotation data
                # Group parameters by category
                parameter_groups = {}
                for param in selected_parameters:
                    # Find which category this parameter belongs to
                    category_found = False
                    for category, standard_params in self.standard_parameters.items():
                        if param in standard_params:
                            if category not in parameter_groups:
                                parameter_groups[category] = []
                            parameter_groups[category].append(param)
                            category_found = True
                            break
                    
                    # If not found in standard categories, add to Additional Parameters
                    if not category_found:
                        if "Additional Parameters" not in parameter_groups:
                            parameter_groups["Additional Parameters"] = []
                        parameter_groups["Additional Parameters"].append(param)
                
                # Get item name/part no for this parameter
                item_name = quotations[0].get('item_name_part_no', '') if quotations else ''
                
                # Create rows for each parameter group
                for category, params in parameter_groups.items():
                    if params:
                        # Add category header row
                        comparison_data.append({
                            "Item Name / Part No.": "",
                            "Parameter": f"--- {category.upper()} ---",
                            **{vendor: "" for vendor in vendor_names}
                        })
                        
                        # Add parameters for this category
                        for param in params:
                            # Format the parameter name for display
                            display_name = param.replace('_', ' ').title()
                            
                            # Create row data
                            row_data = {
                                "Item Name / Part No.": "",
                                "Parameter": display_name
                            }
                            
                            # Add vendor values
                            for i, quotation in enumerate(quotations):
                                vendor_name = vendor_names[i]
                                value = quotation.get(param, '')
                                row_data[vendor_name] = value
                            
                            comparison_data.append(row_data)
            
            return pd.DataFrame(comparison_data)
            
        except Exception as e:
            logger.error(f"Error creating comparison table: {str(e)}")
            return pd.DataFrame()
    
    def calculate_comparison_metrics(self, quotations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comparison metrics and scores"""
        try:
            metrics = {
                "total_quotations": len(quotations),
                "unique_vendors": len(set(q.get('supplier_name') for q in quotations if q.get('supplier_name'))),
                "price_range": {},
                "average_confidence": 0,
                "requires_review_count": 0,
                "currency": "INR"  # Default currency
            }
            
            # Calculate price metrics if available
            prices = [q.get('total_amount') for q in quotations if q.get('total_amount')]
            if prices:
                # Get currency from quotations (assume all quotations have same currency)
                currency = quotations[0].get('currency', 'INR') if quotations else 'INR'
                metrics["currency"] = currency
                
                metrics["price_range"] = {
                    "min": min(prices),
                    "max": max(prices),
                    "average": sum(prices) / len(prices)
                }
            
            # Calculate confidence metrics
            confidences = [q.get('confidence_score', 0) for q in quotations]
            if confidences:
                metrics["average_confidence"] = sum(confidences) / len(confidences)
            
            # Count quotations requiring review
            metrics["requires_review_count"] = sum(1 for q in quotations if q.get('requires_review', False))
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating comparison metrics: {str(e)}")
            return {}

def show_comparative_analysis_agent():
    """Main function to display the Comparative Analysis Agent interface"""
    
    st.markdown("""
    <div class="main-header">
        <h1 class="header-title">🔍 Comparative Analysis Agent</h1>
        <p class="header-subtitle">Compare quotations and generate comprehensive analysis reports</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Back button
    if st.button("← Back to Procurement Department", key="back_to_dept_comparative"):
        st.session_state.show_comparative_agent = False
        st.session_state.show_procurement_dept = True
        st.rerun()
    
    st.markdown("## 🔍 Comparative Analysis Agent")
    st.markdown("Compare quotations from the database to make informed decisions.")
    
    # Initialize the agent
    agent = ComparativeAnalysisAgent()
    
    # Step 1: Select Indent ID
    st.markdown("### 📋 Step 1: Select Indent ID")
    
    indent_ids = agent.get_all_indent_ids()
    
    if not indent_ids:
        st.warning("⚠️ No indent IDs found in the database. Please parse some quotations first.")
        return
    
    selected_indent_id = st.selectbox(
        "Choose Indent ID to compare:",
        options=indent_ids,
        help="Select the indent ID for which you want to compare quotations",
        key="selected_indent_id"
    )
    
    if selected_indent_id:
        # Step 2: Get quotations for selected indent ID
        quotations = agent.get_quotations_by_indent(selected_indent_id)
        
        if not quotations:
            st.warning(f"⚠️ No quotations found for indent ID: {selected_indent_id}")
            return
        
        st.success(f"✅ Found {len(quotations)} quotations for indent ID: {selected_indent_id}")
        
        # Display quotation summary
        st.markdown("### 📊 Available Quotations")
        
        summary_data = []
        for i, quotation in enumerate(quotations):
            summary_data.append({
                "Index": i + 1,
                "Vendor": quotation.get('supplier_name', 'Unknown'),
                "Quotation Number": quotation.get('quotation_number', 'N/A'),
                "Filename": quotation.get('filename', 'N/A'),
                "Total Amount": quotation.get('total_amount', 'N/A'),
                "Confidence": f"{quotation.get('confidence_score', 0):.2f}",
                "Requires Review": "Yes" if quotation.get('requires_review') else "No"
            })
        
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
        
        # Step 3: Select quotations to compare
        st.markdown("### 🔍 Step 2: Select Quotations to Compare")
        
        quotation_options = [f"{i+1}. {q.get('supplier_name', 'Unknown')} - {q.get('filename', 'N/A')}" 
                           for i, q in enumerate(quotations)]
        
        selected_quotation_indices = st.multiselect(
            "Choose quotations to compare (select 2 or more):",
            options=quotation_options,
            help="Select the quotations you want to compare",
            key="selected_quotation_indices"
        )
        
        if len(selected_quotation_indices) < 2:
            st.warning("⚠️ Please select at least 2 quotations to compare.")
            return
        
        # Get selected quotations
        selected_quotations = []
        for option in selected_quotation_indices:
            index = int(option.split('.')[0]) - 1
            selected_quotations.append(quotations[index])
        
        st.success(f"✅ Selected {len(selected_quotations)} quotations for comparison")
        
        # Step 4: Get available parameters
        available_parameters = agent.get_available_parameters(selected_quotations)
        
        st.markdown("### ⚙️ Step 3: Select Parameters to Compare")
        st.info("💡 **All parameters are selected by default.** You can unselect any parameters you don't want to compare.")
        
        # Display available parameters by category
        selected_parameters = []
        
        for category, params in available_parameters.items():
            if params:
                st.markdown(f"**{category}:**")
                category_params = st.multiselect(
                    f"Select {category.lower()} parameters:",
                    options=params,
                    default=params,  # Select all parameters by default
                    key=f"params_{category}",
                    help=f"All parameters are selected by default. Unselect any parameters you don't want to compare."
                )
                selected_parameters.extend(category_params)
        
        if not selected_parameters:
            st.warning("⚠️ Please select at least one parameter to compare.")
            return
        
        st.success(f"✅ Selected {len(selected_parameters)} parameters for comparison")
        
        # Check if line items are present
        has_line_items = any('line_items' in q and q['line_items'] for q in selected_quotations)
        if has_line_items:
            st.info("📋 **Line Items Detected**: The comparison will show each line item separately with its parameters compared across vendors.")
        
        # Step 5: Generate comparison table
        st.markdown("### 📊 Step 4: Comparative Analysis Results")
        
        # Calculate metrics
        metrics = agent.calculate_comparison_metrics(selected_quotations)
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Quotations", metrics.get('total_quotations', 0))
        
        with col2:
            st.metric("Unique Vendors", metrics.get('unique_vendors', 0))
        
        with col3:
            avg_confidence = metrics.get('average_confidence', 0)
            st.metric("Avg Confidence", f"{avg_confidence:.2f}")
        
        with col4:
            review_count = metrics.get('requires_review_count', 0)
            st.metric("Need Review", review_count)
        
        # Create and display comparison table
        comparison_df = agent.create_comparison_table(selected_quotations, selected_parameters)
        
        if not comparison_df.empty:
            st.markdown("#### 📋 Comparison Table")
            st.dataframe(
                comparison_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Item Name / Part No.": st.column_config.TextColumn("Item Name / Part No.", width="medium"),
                    "Parameter": st.column_config.TextColumn("Parameter", width="medium")
                }
            )
            
            # Add download button
            csv = comparison_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Comparison Table (CSV)",
                data=csv,
                file_name=f"comparison_{selected_indent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            # Display price analysis if available
            if metrics.get('price_range'):
                st.markdown("#### 💰 Price Analysis")
                price_range = metrics['price_range']
                currency = metrics.get('currency', 'INR')
                
                # Format currency symbol
                currency_symbol = "₹" if currency == "INR" else "$"
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Lowest Price", f"{currency_symbol}{price_range['min']:,.2f}")
                with col2:
                    st.metric("Highest Price", f"{currency_symbol}{price_range['max']:,.2f}")
                with col3:
                    st.metric("Average Price", f"{currency_symbol}{price_range['average']:,.2f}")
                
                # Calculate price difference
                price_diff = price_range['max'] - price_range['min']
                price_diff_percent = (price_diff / price_range['min']) * 100 if price_range['min'] > 0 else 0
                
                st.info(f"💰 Price Range: {currency_symbol}{price_diff:,.2f} ({price_diff_percent:.1f}% difference)")
            
            # Recommendations
            st.markdown("#### 🎯 Recommendations")
            
            # Find best options based on different criteria
            best_price = min(selected_quotations, key=lambda x: x.get('total_amount', float('inf')))
            best_confidence = max(selected_quotations, key=lambda x: x.get('confidence_score', 0))
            
            # Get currency for recommendations
            currency = metrics.get('currency', 'INR')
            currency_symbol = "₹" if currency == "INR" else "$"
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**💰 Best Price:**")
                st.info(f"**{best_price.get('supplier_name', 'Unknown')}** - {currency_symbol}{best_price.get('total_amount', 0):,.2f}")
            
            with col2:
                st.markdown("**🎯 Best Confidence:**")
                st.info(f"**{best_confidence.get('supplier_name', 'Unknown')}** - {best_confidence.get('confidence_score', 0):.2f}")
            
            # Overall recommendation
            if best_price == best_confidence:
                st.success(f"🏆 **RECOMMENDED**: {best_price.get('supplier_name', 'Unknown')} - Best price and confidence!")
            else:
                st.warning("⚠️ **CONSIDER**: Different vendors excel in different areas. Review detailed comparison.")
        
        # Clear results button
        st.markdown("---")
        if st.button("🗑️ Clear Comparison Results", key="clear_comparison_results"):
            # Clear all relevant session state variables
            for key in list(st.session_state.keys()):
                if key.startswith('params_'):
                    del st.session_state[key]
            # Clear selected quotations so results disappear on rerun
            if 'selected_quotation_indices' in st.session_state:
                del st.session_state['selected_quotation_indices']
            st.rerun()

def main():
    """Main function to run the comparative analysis agent"""
    show_comparative_analysis_agent()

if __name__ == "__main__":
    main()
