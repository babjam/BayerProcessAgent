import streamlit as st
from fpdf import FPDF
import pandas as pd
import base64
import io
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== CONSTANTS ==========
DEFAULT_VALUES = {
    "stock_amount": 50.0,
    "stock_conc": 1.0,
    "final_amount": 200.0,
    "final_conc": 0.1,
}

SOP_PRESETS = {
    "1% Latex Stock (200 g)": {"amount": 200.0, "conc": 1.0},
    "0.3% Dry Floc Stock (200 g)": {"amount": 200.0, "conc": 0.3},
    "0.1% Working Solution from 1%": {"amount": 200.0, "conc": 0.1}
}

UNIT_CONFIGS = {
    "Weight (g) / % w/w": {"unit": "g", "conc_unit": "% w/w"},
    "Volume (mL) / % v/v": {"unit": "mL", "conc_unit": "% v/v"}
}

# ========== FUNCTIONS ==========
def calculate_solution(amount: float, concentration: float) -> Tuple[float, float]:
    """
    Calculate the required amounts for solution preparation.
    
    Args:
        amount: Total amount of solution needed
        concentration: Target concentration as percentage
        
    Returns:
        Tuple of (solute_amount, solvent_amount)
    """
    try:
        if amount <= 0 or concentration <= 0:
            raise ValueError("Amount and concentration must be positive")
            
        fraction = concentration / 100.0
        solute_amount = amount * fraction
        solvent_amount = amount - solute_amount
        
        logger.info(f"Calculated: {solute_amount:.2f} solute, {solvent_amount:.2f} solvent")
        return solute_amount, solvent_amount
        
    except Exception as e:
        logger.error(f"Calculation error: {str(e)}")
        st.error(f"Calculation error: {str(e)}")
        return 0.0, 0.0

def validate_inputs(amount: float, concentration: float, step_name: str) -> List[str]:
    """
    Validate user inputs for solution preparation.
    
    Args:
        amount: Amount to validate
        concentration: Concentration to validate
        step_name: Name of the step for error messages
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # Basic validation
    if amount <= 0:
        errors.append(f"{step_name}: Amount must be greater than 0")
    if concentration <= 0:
        errors.append(f"{step_name}: Concentration must be greater than 0")
    if concentration >= 100:
        errors.append(f"{step_name}: Concentration must be less than 100%")
    
    # Cross-step validation for final dilution
    if step_name == "Final Dilution" and 'stock_conc' in st.session_state:
        if concentration >= st.session_state.stock_conc:
            errors.append("Final concentration should be lower than stock concentration")
    
    # Reasonable limits validation
    if amount > 10000:  # 10L or 10kg seems reasonable upper limit
        errors.append(f"{step_name}: Amount seems unreasonably large (>{10000})")
    
    return errors

class EnhancedPDF(FPDF):
    """Enhanced PDF class with better formatting and error handling."""
    
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
    
    def header(self):
        """Add header to each page."""
        self.set_font("Arial", 'B', 16)
        self.cell(0, 15, "Flocculant Preparation Report", ln=True, align='C')
        self.set_font("Arial", 'I', 10)
        self.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
        self.ln(5)

    def footer(self):
        """Add footer to each page."""
        self.set_y(-15)
        self.set_font("Arial", 'I', 8)
        self.cell(0, 10, f"Page {self.page_no()}", align='C')
    
    def add_section_title(self, title: str):
        """Add a section title with consistent formatting."""
        self.set_font("Arial", 'B', 14)
        self.cell(0, 10, title, ln=True)
        self.ln(2)
    
    def add_parameter_table(self, data: List[Tuple[str, str]]):
        """Add a parameter table with proper formatting."""
        self.set_font("Arial", 'B', 10)
        self.cell(70, 8, "Parameter", border=1, align='C')
        self.cell(110, 8, "Value", border=1, align='C', ln=True)
        
        self.set_font("Arial", size=10)
        for param, value in data:
            self.cell(70, 6, str(param), border=1)
            self.cell(110, 6, str(value), border=1, ln=True)
        self.ln(4)

def generate_pdf(title: str, stock_info: Dict, dilution_info: Dict, 
                summary_df: pd.DataFrame, mode_used: str) -> str:
    """
    Generate PDF report with enhanced formatting and error handling.
    
    Args:
        title: Report title
        stock_info: Stock solution information
        dilution_info: Dilution information
        summary_df: Summary dataframe
        mode_used: Preparation mode used
        
    Returns:
        HTML link for PDF download or empty string on error
    """
    try:
        pdf = EnhancedPDF()
        pdf.add_page()
        
        # Title and metadata
        pdf.add_section_title(title)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 8, f"Preparation Mode: {mode_used}", ln=True)
        pdf.cell(0, 8, f"Units: {st.session_state.get('unit_type', 'N/A')}", ln=True)
        pdf.ln(4)
        
        # Summary table
        pdf.add_section_title("Summary")
        summary_data = [(row['Parameter'], row['Value']) for _, row in summary_df.iterrows()]
        pdf.add_parameter_table(summary_data)
        
        # Stock solution details
        pdf.add_section_title("Step 1: Stock Solution Preparation")
        pdf.set_font("Arial", size=10)
        stock_data = [
            ("Target Amount", f"{stock_info['stock_amount']:.2f} {stock_info.get('unit', 'g')}"),
            ("Target Concentration", f"{stock_info['stock_conc']:.2f} {stock_info.get('conc_unit', '%')}"),
            ("Emulsion Required", f"{stock_info['emulsion_needed']:.2f} {stock_info.get('unit', 'g')}"),
            ("Water Required", f"{stock_info['water_needed']:.2f} {stock_info.get('unit', 'g')}")
        ]
        pdf.add_parameter_table(stock_data)
        
        # Final dilution details
        pdf.add_section_title("Step 2: Final Dilution")
        dilution_data = [
            ("Final Amount", f"{dilution_info['final_amount']:.2f} {dilution_info.get('unit', 'g')}"),
            ("Final Concentration", f"{dilution_info['final_conc']:.2f} {dilution_info.get('conc_unit', '%')}"),
            ("Stock Solution Used", f"{dilution_info['stock_needed']:.2f} {dilution_info.get('unit', 'g')}"),
            ("Water Added", f"{dilution_info['water_needed']:.2f} {dilution_info.get('unit', 'g')}")
        ]
        pdf.add_parameter_table(dilution_data)
        
        # Safety notes
        pdf.add_section_title("Safety and Quality Notes")
        pdf.set_font("Arial", size=9)
        safety_notes = [
            "• Use DI water with 10-15 g/L NaOH for makeup water",
            "• Mix emulsion thoroughly in alkaline solution",
            "• Always add water first, then stock solution",
            "• Use vessel at least 2x the final volume",
            "• Match plant water conditions where possible"
        ]
        for note in safety_notes:
            pdf.multi_cell(0, 5, note)
        
        # Generate download link
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        b64 = base64.b64encode(pdf_bytes).decode()
        filename = f"flocculant_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return f'<a href="data:application/pdf;base64,{b64}" download="{filename}">📄 Download PDF Report</a>'
        
    except Exception as e:
        logger.error(f"PDF generation failed: {str(e)}")
        st.error(f"PDF generation failed: {str(e)}")
        return ""

def generate_excel(summary_df: pd.DataFrame, stock_info: Dict, dilution_info: Dict) -> str:
    """
    Generate Excel report with multiple sheets and enhanced data.
    
    Args:
        summary_df: Summary dataframe
        stock_info: Stock solution information
        dilution_info: Dilution information
        
    Returns:
        HTML link for Excel download or empty string on error
    """
    try:
        output = io.BytesIO()
        
        # Create detailed dataframes for each sheet
        stock_df = pd.DataFrame({
            'Parameter': ['Target Amount', 'Target Concentration', 'Emulsion Required', 'Water Required'],
            'Value': [
                f"{stock_info['stock_amount']:.2f}",
                f"{stock_info['stock_conc']:.2f}",
                f"{stock_info['emulsion_needed']:.2f}",
                f"{stock_info['water_needed']:.2f}"
            ],
            'Unit': [
                stock_info.get('unit', 'g'),
                stock_info.get('conc_unit', '%'),
                stock_info.get('unit', 'g'),
                stock_info.get('unit', 'g')
            ]
        })
        
        dilution_df = pd.DataFrame({
            'Parameter': ['Final Amount', 'Final Concentration', 'Stock Used', 'Water Added'],
            'Value': [
                f"{dilution_info['final_amount']:.2f}",
                f"{dilution_info['final_conc']:.2f}",
                f"{dilution_info['stock_needed']:.2f}",
                f"{dilution_info['water_needed']:.2f}"
            ],
            'Unit': [
                dilution_info.get('unit', 'g'),
                dilution_info.get('conc_unit', '%'),
                dilution_info.get('unit', 'g'),
                dilution_info.get('unit', 'g')
            ]
        })
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Write multiple sheets
            summary_df.to_excel(writer, index=False, sheet_name='Summary')
            stock_df.to_excel(writer, index=False, sheet_name='Stock Solution')
            dilution_df.to_excel(writer, index=False, sheet_name='Final Dilution')
            
            # Format the worksheets
            workbook = writer.book
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC'})
            
            for sheet_name in ['Summary', 'Stock Solution', 'Final Dilution']:
                worksheet = writer.sheets[sheet_name]
                worksheet.set_row(0, None, header_format)
                worksheet.set_column('A:C', 20)
        
        output.seek(0)
        b64 = base64.b64encode(output.read()).decode()
        filename = f"flocculant_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">📊 Download Excel Summary</a>'
        
    except Exception as e:
        logger.error(f"Excel generation failed: {str(e)}")
        st.error(f"Excel generation failed: {str(e)}")
        return ""

def init_session_state():
    """Initialize session state with default values."""
    defaults = {
        "mode": "Manual Input",
        "unit_type": "Weight (g) / % w/w",
        "step1_completed": False,
        "step2_completed": False,
        "stock_calculations": {},
        "dilution_calculations": {},
        **DEFAULT_VALUES
    }
    
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

def reset_calculations():
    """Reset calculation results when inputs change."""
    st.session_state.step1_completed = False
    st.session_state.step2_completed = False
    st.session_state.stock_calculations = {}
    st.session_state.dilution_calculations = {}

def get_unit_config() -> Dict[str, str]:
    """Get current unit configuration."""
    return UNIT_CONFIGS.get(st.session_state.unit_type, UNIT_CONFIGS["Weight (g) / % w/w"])

# ========== MAIN APPLICATION ==========
def main():
    """Main application function."""
    # Page setup
    st.set_page_config(
        page_title="Flocculant Prep Agent", 
        layout="centered",
        initial_sidebar_state="expanded"
    )
    
    st.markdown("### 🧪 Flocculant Preparation Assistant")
    st.markdown("*Professional solution preparation with step-by-step guidance*")
    
    # Initialize session state
    init_session_state()
    
    # Get current unit configuration
    unit_config = get_unit_config()
    unit = unit_config["unit"]
    conc_unit = unit_config["conc_unit"]
    
    # ========== SIDEBAR (Available from start) ==========
    with st.sidebar:
        st.markdown("#### 📖 Help & Guidelines")
        
        st.markdown("##### 💧 Makeup Water")
        st.info("Use DI or Plant water with 10–15 g/L NaOH. Match plant water conditions when possible.")
        
        st.markdown("##### 📘 Stock Solution Tips")
        st.markdown("""
        - Mix emulsion in alkaline solution (10 g/L NaOH)
        - Target concentration: 0.5–1.0% w/w
        - Ensure complete dissolution
        - Store in appropriate containers
        """)
        
        st.markdown("##### 📙 Final Dilution Tips")
        st.markdown("""
        - Always prepare working solutions fresh
        - Typical working concentration: 
                    from emulsion : 0.1%
                    from dy       : 0.03%
        - **Always add water first, then stock**
        - Use vessel capacity  twice final volume
        - Mix thoroughly ensure proper mixing, no lumps ( fish eyes)
        """)
        
        st.markdown("##### ⚠️ Safety Reminders")
        st.warning("""
        - Wear appropriate PPE.
        - Follow local safety protocols
        """)
        
        # Reset button
        st.markdown("---")
        if st.button("🔄 Reset All Calculations"):
            reset_calculations()
            st.success("All calculations reset!")
            st.rerun()
    
    # ========== MODE & UNITS SELECTION ==========
    st.markdown("#### 🧭 Preparation Mode")
    new_mode = st.radio("Select preparation mode:", ["Manual Input", "SOP-Driven"], horizontal=True)
    
    if new_mode != st.session_state.mode:
        st.session_state.mode = new_mode
        reset_calculations()
    
    st.markdown("#### ⚖️ Select Units")
    new_unit_type = st.radio("Choose unit system:", list(UNIT_CONFIGS.keys()), horizontal=True)
    
    if new_unit_type != st.session_state.unit_type:
        st.session_state.unit_type = new_unit_type
        reset_calculations()
        unit_config = get_unit_config()
        unit = unit_config["unit"]
        conc_unit = unit_config["conc_unit"]
    
    # SOP preset selection
    if st.session_state.mode == "SOP-Driven":
        st.markdown("#### 📘 SOP Recipe Selection")
        selected_preset = st.selectbox("Choose a standard recipe:", list(SOP_PRESETS.keys()))
        preset = SOP_PRESETS[selected_preset]
        
        # Update session state with preset values
        if (st.session_state.stock_amount != preset["amount"] or 
            st.session_state.stock_conc != preset["conc"]):
            st.session_state.stock_amount = preset["amount"]
            st.session_state.stock_conc = preset["conc"]
            reset_calculations()
    
    # ========== TABS ==========
    tab1, tab2, tab3 = st.tabs(["1️⃣ Stock Solution", "2️⃣ Final Dilution", "3️⃣ Export & Reports"])
    
    # --- Tab 1: Stock Solution ---
    with tab1:
        st.markdown("#### 📘 Stock Solution Preparation")
        
        if st.session_state.mode == "Manual Input":
            col1, col2 = st.columns(2)
            with col1:
                new_amount = st.number_input(
                    f"Target amount ({unit})", 
                    min_value=0.0, 
                    value=st.session_state.stock_amount, 
                    step=10.0, 
                    format="%.2f",
                    help=f"Total amount of stock solution to prepare"
                )
            with col2:
                new_conc = st.number_input(
                    f"Target concentration ({conc_unit})", 
                    min_value=0.0, 
                    value=st.session_state.stock_conc, 
                    step=0.1, 
                    format="%.2f",
                    help="Concentration of the stock solution"
                )
            
            # Check if values changed
            if (new_amount != st.session_state.stock_amount or 
                new_conc != st.session_state.stock_conc):
                st.session_state.stock_amount = new_amount
                st.session_state.stock_conc = new_conc
                reset_calculations()
        else:
            st.info(f"**Using SOP Preset:** {selected_preset}")
            st.markdown(f"""
            **Amount**: {st.session_state.stock_amount} {unit}  
            **Concentration**: {st.session_state.stock_conc} {conc_unit}
            """)
        
        if st.button("🔬 Calculate Stock Solution", type="primary"):
            errors = validate_inputs(st.session_state.stock_amount, st.session_state.stock_conc, "Stock Solution")
            
            if errors:
                for err in errors:
                    st.error(err)
                st.session_state.step1_completed = False
            else:
                emulsion, water = calculate_solution(st.session_state.stock_amount, st.session_state.stock_conc)
                st.session_state.stock_calculations = {
                    'emulsion_needed': emulsion,
                    'water_needed': water,
                    'stock_amount': st.session_state.stock_amount,
                    'stock_conc': st.session_state.stock_conc,
                    'unit': unit,
                    'conc_unit': conc_unit
                }
                st.session_state.step1_completed = True
        
        # Display results
        if st.session_state.step1_completed:
            calc = st.session_state.stock_calculations
            st.success("✅ Stock solution calculated successfully!")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Emulsion Required", f"{calc['emulsion_needed']:.2f} {unit}")
            with col2:
                st.metric("Water Required", f"{calc['water_needed']:.2f} {unit}")
            with col3:
                st.metric("Total Volume", f"{calc['stock_amount']:.2f} {unit}")
            
            # Instructions
            st.markdown("##### 📋 Preparation Instructions")
            beaker_volume = calc['stock_amount'] * 2

            st.markdown(f"""
            1. **Prepare alkaline water**: Add 10–15 g/L NaOH to DI or plant water.  
            2. **Set up beaker**: Use a **{beaker_volume:.0f}** ml beaker and add **{calc['water_needed']:.2f} {unit}** of alkaline water.  
            3. **Start vortex mixing**: on a plate, overhead or hand mixer use 700–900 RPM.  
            4. **Add emulsion**: Slowly inject **{calc['emulsion_needed']:.2f} {unit}** of flocculant into the vortex shoulder.  
            5. **Mix thoroughly**: Continue mixing for **30 min** to ensure complete dissolution.  
            6. **Aging**: let the stock solution rest 2 hours under agitation **200 -300** rpm. 
            7. **Strorage** : transfer into a **{calc['stock_amount']:.0f}** ml bottle place the lid, label and use not later than 24 hours.
            """)
    
    # --- Tab 2: Final Dilution ---
    with tab2:
        if not st.session_state.step1_completed:
            st.warning("⚠️ Please complete the Stock Solution calculation first.")
            st.stop()
        
        st.markdown("#### 📙 Final Dilution Preparation")
        
        if st.session_state.mode == "Manual Input":
            col1, col2 = st.columns(2)
            with col1:
                new_final_amount = st.number_input(
                    f"Final amount ({unit})", 
                    min_value=0.0, 
                    value=st.session_state.final_amount, 
                    step=10.0, 
                    format="%.2f",
                    help="Total amount of final diluted solution"
                )
            with col2:
                new_final_conc = st.number_input(
                    f"Final concentration ({conc_unit})", 
                    min_value=0.0, 
                    value=st.session_state.final_conc, 
                    step=0.01, 
                    format="%.3f",
                    help="Target concentration for final solution"
                )
            
            # Check if values changed
            if (new_final_amount != st.session_state.final_amount or 
                new_final_conc != st.session_state.final_conc):
                st.session_state.final_amount = new_final_amount
                st.session_state.final_conc = new_final_conc
                st.session_state.step2_completed = False
        else:
            st.info("Using SOP Final Dilution Settings")
            st.markdown(f"""
            **Amount**: {st.session_state.final_amount} {unit}  
            **Concentration**: {st.session_state.final_conc} {conc_unit}
            """)
        
        if st.button("🔬 Calculate Final Dilution", type="primary"):
            errors = validate_inputs(st.session_state.final_amount, st.session_state.final_conc, "Final Dilution")
            
            if errors:
                for err in errors:
                    st.error(err)
                st.session_state.step2_completed = False
            else:
                # Calculate based on dilution from stock
                stock_conc = st.session_state.stock_calculations['stock_conc']
                final_conc = st.session_state.final_conc
                final_amount = st.session_state.final_amount
                
                # C1V1 = C2V2, so V1 = C2V2/C1
                stock_needed = (final_conc * final_amount) / stock_conc
                water_needed = final_amount - stock_needed
                
                available_stock = st.session_state.stock_calculations['stock_amount']
                
                if stock_needed > available_stock:
                    st.error(f"❌ Insufficient stock solution! Need {stock_needed:.2f} {unit}, but only {available_stock:.2f} {unit} available.")
                    st.session_state.step2_completed = False
                else:
                    st.session_state.dilution_calculations = {
                        'stock_needed': stock_needed,
                        'water_needed': water_needed,
                        'final_amount': final_amount,
                        'final_conc': final_conc,
                        'unit': unit,
                        'conc_unit': conc_unit
                    }
                    st.session_state.step2_completed = True
        
        # Display results
        if st.session_state.step2_completed:
            calc = st.session_state.dilution_calculations
            st.success("✅ Final dilution calculated successfully!")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Stock Solution Needed", f"{calc['stock_needed']:.2f} {unit}")
            with col2:
                st.metric("Water to Add", f"{calc['water_needed']:.2f} {unit}")
            with col3:
                st.metric("Final Volume", f"{calc['final_amount']:.2f} {unit}")
            
            # Instructions
            st.markdown("##### 📋 Dilution Instructions")

            # Ensure bottle is at least twice the final volume
            bottle_volume = calc['final_amount'] * 2

            st.markdown(f"""
            1. **Select bottle**: Use a Nalgene bottle with at least **{bottle_volume:.0f}** ml capacity.  
            2. **Add water first**: Pour **{calc['water_needed']:.2f} {unit}** of alkaline water into the bottle.  
            3. **Stock solution**:add **{calc['stock_needed']:.2f} {unit}** of stock solution into the bottle. 
            4. **Seal & mix**: Tighten the lid securely and shake **vigorously** until fully homogeneous.  
            5. **Use immediately**: Once mixed, transfer into a **{calc['stock_needed']:.0f}** ml bottle place the lid, label and use in this session (do not store overnight).
            """)

    
    # --- Tab 3: Export & Reports ---
    with tab3:
        if not st.session_state.step2_completed:
            st.warning("⚠️ Please complete both calculation steps before generating reports.")
            st.stop()
        
        st.markdown("#### 📊 Summary & Reports")
        
        # Prepare summary data
        stock = st.session_state.stock_calculations
        final = st.session_state.dilution_calculations
        
        summary_df = pd.DataFrame({
            "Parameter": [
                "Stock Amount", "Stock Concentration", "Emulsion Required", "Water for Stock",
                "Final Amount", "Final Concentration", "Stock Solution Used", "Water for Dilution"
            ],
            "Value": [
                f"{stock['stock_amount']:.2f} {unit}", f"{stock['stock_conc']:.2f} {conc_unit}",
                f"{stock['emulsion_needed']:.2f} {unit}", f"{stock['water_needed']:.2f} {unit}",
                f"{final['final_amount']:.2f} {unit}", f"{final['final_conc']:.2f} {conc_unit}",
                f"{final['stock_needed']:.2f} {unit}", f"{final['water_needed']:.2f} {unit}"
            ]
        })
        
        st.dataframe(summary_df, use_container_width=True)
        
        # Material balance check
        st.markdown("##### ⚖️ Material Balance Check")
        stock_used = final['stock_needed']
        stock_available = stock['stock_amount']
        stock_remaining = stock_available - stock_used
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Stock Available", f"{stock_available:.2f} {unit}")
        with col2:
            st.metric("Stock Used", f"{stock_used:.2f} {unit}")
        with col3:
            st.metric("Stock Remaining", f"{stock_remaining:.2f} {unit}")
        
        # Download section
        st.markdown("#### 📥 Download Reports")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Generate PDF Report", type="secondary"):
                with st.spinner("Generating PDF..."):
                    pdf_link = generate_pdf(
                        "Flocculant Preparation Report", 
                        stock, 
                        final, 
                        summary_df, 
                        st.session_state.mode
                    )
                    if pdf_link:
                        st.markdown(pdf_link, unsafe_allow_html=True)
        
        with col2:
            if st.button("Generate Excel Report", type="secondary"):
                with st.spinner("Generating Excel..."):
                    excel_link = generate_excel(summary_df, stock, final)
                    if excel_link:
                        st.markdown(excel_link, unsafe_allow_html=True)

if __name__ == "__main__":
    main()