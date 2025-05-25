import streamlit as st
from fpdf import FPDF
import pandas as pd
import base64
import io

def calculate_solution(target_amount, concentration):
    frac = concentration / 100
    emulsion = target_amount * frac
    water = target_amount - emulsion
    return emulsion, water

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", 'B', 12)
        self.cell(0, 10, "Flocculant Preparation Report", ln=True, align='C')
        self.ln(10)

def generate_pdf(title, stock_info, dilution_info, summary_df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, title, ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 10, "Summary Table", ln=True)
    pdf.set_font("Arial", size=12)
    for _, row in summary_df.iterrows():
        pdf.cell(95, 8, f"{row['Parameter']}", border=1)
        pdf.cell(95, 8, f"{row['Value']}", border=1, ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 10, "Step 1: Stock Solution", ln=True)
    pdf.set_font("Arial", size=12)
    for line in stock_info:
        pdf.multi_cell(190, 8, txt=line.replace("≥", ">="), align="L")
    pdf.ln(5)
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 10, "Step 2: Final Dilution", ln=True)
    pdf.set_font("Arial", size=12)
    for line in dilution_info:
        pdf.multi_cell(190, 8, txt=line.replace("≥", ">="), align="L")
    pdf_bytes = pdf.output(dest="S").encode("latin1")
    buffer = io.BytesIO(pdf_bytes)
    b64 = base64.b64encode(buffer.read()).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="flocculant_instructions.pdf">📄 Download PDF Report</a>'
    return href

def generate_excel(summary_df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        summary_df.to_excel(writer, index=False, sheet_name='Summary')
    output.seek(0)
    b64 = base64.b64encode(output.read()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="flocculant_summary.xlsx">📊 Download Excel Summary</a>'
    return href

st.set_page_config(page_title="Flocculant Prep Agent", layout="centered")
st.title("🧪 Water-in-Oil Emulsion Flocculant Preparation")

mode = st.radio("Select mode:", ["Weight (g) / % w/w", "Volume (mL) / % v/v"], horizontal=True)
unit_default = "g" if "Weight" in mode else "mL"
conc_type_default = "% w/w" if "Weight" in mode else "% v/v"

step1_complete = False
step2_complete = False
stock_info_lines = []
dilution_info_lines = []

tabs = st.tabs(["1️⃣ Step 1: Stock Solution", "2️⃣ Step 2: Final Dilution", "3️⃣ 📥 Export"])

# Step 1
stock_amount = 0.0
stock_conc = 0.0
with tabs[0]:
    st.subheader("Enter Stock Solution Parameters")
    s1_col1, s1_col2 = st.columns([4, 1])
    with s1_col1:
        stock_amount = st.number_input("Target amount", min_value=50.0, step=50.0, format="%.2f")
    with s1_col2:
        st.markdown(f"<div style='line-height:3.3'>{unit_default}</div>", unsafe_allow_html=True)

    s1c1, s1c2 = st.columns([4, 1])
    with s1c1:
        stock_conc = st.number_input("Target concentration", min_value=0.1, step=0.1, format="%.2f")
    with s1c2:
        st.markdown(f"<div style='line-height:3.3'>{conc_type_default}</div>", unsafe_allow_html=True)

    emul, wat = calculate_solution(stock_amount, stock_conc)
    step1_complete = stock_amount > 0 and stock_conc > 0
    st.success(f"Emulsion: {emul:.2f} {unit_default} | Water: {wat:.2f} {unit_default}")

    with st.expander("📋 Instructions", expanded=False):
        st.markdown(f"- Use a clean beaker or bottle ≥ **{2 * stock_amount:.0f} mL**.")
        if unit_default == "g":
            st.markdown("- Tare a syringe, sample emulsion, weigh, and adjust.")
            st.markdown("- Tare beaker and add water to exact mass.")
        else:
            st.markdown("- Measure emulsion volume with syringe.")
            st.markdown("- Measure water with graduated cylinder and pour.")
        st.markdown("- Add magnetic stir bar and stir at ~750 rpm.")
        st.markdown("- Inject emulsion steadily into vortex shoulder.")
        st.markdown("- Stir 5 min at high speed, then 2+ hours gently.")
        st.markdown("- If undissolved strands remain, discard and remake.")

    stock_info_lines = [
        f"Target amount: {stock_amount:.2f} {unit_default}",
        f"Target concentration: {stock_conc:.2f} {conc_type_default}",
        f"Emulsion required: {emul:.2f} {unit_default}",
        f"Water required: {wat:.2f} {unit_default}",
        f"Use clean beaker/bottle ≥ {2 * stock_amount:.0f} mL."
    ] + [
        "Tare syringe or measure by volume.",
        "Add water and magnetic stir bar.",
        "Stir ~750 rpm to vortex, inject emulsion.",
        "Stir 5 min high, then 2+ hours gently.",
        "Inspect and discard if undissolved."
    ]

# Step 2
if step1_complete:
    with tabs[1]:
        st.subheader("Enter Final Dilution Parameters")
        s2_col1, s2_col2 = st.columns([4, 1])
        with s2_col1:
            final_amount = st.number_input("Final amount", min_value=100.0, step=10.0, format="%.2f")
        with s2_col2:
            st.markdown(f"<div style='line-height:3.3'>{unit_default}</div>", unsafe_allow_html=True)

        s2c1, s2c2 = st.columns([4, 1])
        with s2c1:
            final_conc = st.number_input("Target concentration", min_value=0.001, step=0.01, value=0.1, format="%.2f")
        with s2c2:
            st.markdown(f"<div style='line-height:3.3'>{conc_type_default}</div>", unsafe_allow_html=True)

        stock_needed, water_needed = calculate_solution(final_amount, final_conc)
        step2_complete = final_amount > 0 and final_conc > 0

        st.success(f"Stock Solution: {stock_needed:.2f} {unit_default} | Water: {water_needed:.2f} {unit_default}")

        with st.expander("📋 Instructions", expanded=False):
            st.markdown(f"- Use a clean bottle ≥ **{2 * final_amount:.0f} mL**.")
            if unit_default == "g":
                st.markdown("- Tare bottle, add exact mass of water.")
                st.markdown("- Tare syringe and adjust stock weight.")
            else:
                st.markdown("- Measure water with graduated cylinder.")
                st.markdown("- Measure stock volume with syringe.")
            st.markdown("- Inject stock solution into bottle.")
            st.markdown("- Seal tightly and shake vigorously.")

        dilution_info_lines = [
            f"Final amount: {final_amount:.2f} {unit_default}",
            f"Target concentration: {final_conc:.2f} {conc_type_default}",
            f"Stock solution required: {stock_needed:.2f} {unit_default}",
            f"Water required: {water_needed:.2f} {unit_default}",
            f"Use clean bottle ≥ {2 * final_amount:.0f} mL."
        ] + [
            "Add water, then inject stock.",
            "Seal and shake until mixed."
        ]

# Export
if step2_complete:
    with tabs[2]:
        st.subheader("Summary & Export")
        summary_df = pd.DataFrame({
            "Parameter": [
                "Stock Target Amount", "Stock Concentration",
                "Emulsion", "Water",
                "Final Solution Amount", "Final Concentration",
                "Stock Used for Dilution", "Water for Dilution"
            ],
            "Value": [
                f"{stock_amount:.2f} {unit_default}", f"{stock_conc:.2f} {conc_type_default}",
                f"{emul:.2f} {unit_default}", f"{wat:.2f} {unit_default}",
                f"{final_amount:.2f} {unit_default}", f"{final_conc:.2f} {conc_type_default}",
                f"{stock_needed:.2f} {unit_default}", f"{water_needed:.2f} {unit_default}"
            ]
        })
        st.dataframe(summary_df, use_container_width=True)
        st.markdown(generate_pdf("Flocculant Preparation Report", stock_info_lines, dilution_info_lines, summary_df), unsafe_allow_html=True)
        st.markdown(generate_excel(summary_df), unsafe_allow_html=True)

