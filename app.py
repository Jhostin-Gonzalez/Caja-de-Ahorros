import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from fpdf import FPDF
import base64

# --- 1. LÓGICA DE CÁLCULO ---
def calcular_amortizacion(monto, tasa_anual, plazo, fecha_inicio, tipo_plazo):
    filas = []
    saldo = monto
    fecha_pago = fecha_inicio
    
    if tipo_plazo == "Meses":
        tasa_periodo = (tasa_anual / 100) / 12
    else: # Días
        tasa_periodo = (tasa_anual / 100) / 360
        
    cuota = monto * (tasa_periodo * (1 + tasa_periodo)**plazo) / ((1 + tasa_periodo)**plazo - 1)

    for i in range(1, plazo + 1):
        interes = saldo * tasa_periodo
        capital = cuota - interes
        saldo_final = saldo - capital
        
        # Ajuste en la última cuota para cuadrar a 0 exacto
        if i == plazo:
            saldo_final = 0.0
            capital = saldo

        filas.append({
            "Div": i,
            "FEC. PAG": fecha_pago.strftime("%Y/%m/%d"),
            "SALDO CAP.": saldo,
            "CAPITAL": capital,
            "INTERES": interes,
            "CUOTA": cuota
        })
        
        saldo = saldo_final
        if tipo_plazo == "Meses":
            fecha_pago = fecha_pago + relativedelta(months=1)
        else:
            fecha_pago = fecha_pago + timedelta(days=1)
            
    df = pd.DataFrame(filas)
    return df, cuota

# --- 2. GENERACIÓN DEL PDF ---
# (Añadimos fecha_documento como parámetro)
def generar_pdf(df, monto, tasa, plazo, fecha_inicio, tipo_plazo, socio, cedula, tipo_operacion, garante, fecha_documento):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    pdf.set_font("Courier", 'B', 12)
    pdf.cell(0, 5, "CAJA DE AHORROS LA UNION HACE LA FUERZA", ln=1, align='C')
    pdf.set_font("Courier", '', 10)
    pdf.cell(0, 5, "TABLA DE AMORTIZACION", ln=1, align='C')
    pdf.ln(5)
    
    pdf.set_font("Courier", '', 9)
    # Fila 1 (Aquí aplicamos la fecha_documento que elijas en la interfaz)
    pdf.cell(40, 5, "TIPO OPERACION:", 0, 0)
    pdf.cell(100, 5, tipo_operacion, 0, 0)
    pdf.cell(40, 5, "FECHA:", 0, 0)
    pdf.cell(50, 5, fecha_documento.strftime("%Y/%m/%d"), 0, 1)
    
    # Fila 2
    pdf.cell(40, 5, "CLIENTE:", 0, 0)
    pdf.cell(100, 5, socio.upper(), 0, 0)
    pdf.cell(40, 5, "MONEDA:", 0, 0)
    pdf.cell(50, 5, "DOLAR", 0, 1)
    
    # Fila 3
    pdf.cell(40, 5, "CEDULA:", 0, 0)
    pdf.cell(100, 5, cedula, 0, 0)
    pdf.cell(40, 5, "TASA INT.NOMINAL:", 0, 0)
    pdf.cell(50, 5, f"{tasa:.4f}%", 0, 1)
    
    # Fila 4
    pdf.cell(40, 5, "MONTO:", 0, 0)
    pdf.cell(100, 5, f"{monto:,.2f}", 0, 0)
    pdf.cell(40, 5, "TIPO AMORTIZAC.:", 0, 0)
    pdf.cell(50, 5, "FRANCESA", 0, 1)
    
    # Fila 5
    pdf.cell(40, 5, "PLAZO:", 0, 0)
    pdf.cell(100, 5, f"{plazo} {tipo_plazo.upper()}", 0, 1)
    
    pdf.ln(8)
    
    pdf.set_font("Courier", 'B', 9)
    anchos = [15, 35, 45, 45, 45, 45]
    columnas = ["Div", "FEC. PAG", "SALDO CAP.", "CAPITAL", "INTERES", "CUOTA"]
    
    pdf.line(20, pdf.get_y(), sum(anchos)+20, pdf.get_y())
    pdf.set_y(pdf.get_y() + 1)
    pdf.set_x(20)
    
    for col, ancho in zip(columnas, anchos):
        pdf.cell(ancho, 6, col, 0, align='C')
    pdf.ln()
    
    pdf.line(20, pdf.get_y(), sum(anchos)+20, pdf.get_y())
    pdf.set_y(pdf.get_y() + 1)
    
    pdf.set_font("Courier", '', 9)
    
    tot_capital = 0
    tot_interes = 0
    tot_cuota = 0
    
    for _, row in df.iterrows():
        pdf.set_x(20)
        pdf.cell(anchos[0], 5, str(row['Div']), 0, align='C')
        pdf.cell(anchos[1], 5, row['FEC. PAG'], 0, align='C')
        pdf.cell(anchos[2], 5, f"{row['SALDO CAP.']:,.2f}", 0, align='C')
        pdf.cell(anchos[3], 5, f"{row['CAPITAL']:,.2f}", 0, align='C')
        pdf.cell(anchos[4], 5, f"{row['INTERES']:,.2f}", 0, align='C')
        pdf.cell(anchos[5], 5, f"{row['CUOTA']:,.2f}", 0, align='C')
        pdf.ln()
        
        tot_capital += row['CAPITAL']
        tot_interes += row['INTERES']
        tot_cuota += row['CUOTA']
        
    pdf.line(20, pdf.get_y(), sum(anchos)+20, pdf.get_y())
    pdf.set_font("Courier", 'B', 9)
    pdf.set_x(20)
    pdf.cell(anchos[0] + anchos[1], 6, "TOTALES", 0, align='L')
    pdf.cell(anchos[2], 6, "0.00", 0, align='C') 
    pdf.cell(anchos[3], 6, f"{tot_capital:,.2f}", 0, align='C')
    pdf.cell(anchos[4], 6, f"{tot_interes:,.2f}", 0, align='C')
    pdf.cell(anchos[5], 6, f"{tot_cuota:,.2f}", 0, align='C')
    
    # Firmas
    pdf.ln(25)
    y_actual = pdf.get_y()
    
    pdf.set_xy(40, y_actual)
    pdf.cell(85, 30, border=1)
    pdf.set_xy(40, y_actual)
    pdf.cell(85, 6, "GARANTE", border=1, ln=1, align='C')
    pdf.set_xy(40, y_actual + 25)
    pdf.cell(85, 5, garante, align='C')
    
    pdf.set_xy(160, y_actual)
    pdf.cell(85, 30, border=1)
    pdf.set_xy(160, y_actual)
    pdf.cell(85, 6, "EL DEUDOR / SOCIO", border=1, ln=1, align='C')
    pdf.set_xy(160, y_actual + 25)
    pdf.cell(85, 5, socio, align='C')
    
    return pdf.output(dest='S').encode('latin1')

# --- 3. INTERFAZ VISUAL ---
st.set_page_config(page_title="Sistema de Préstamos", layout="wide")
st.title("🏦 Sistema de Amortización (Formato Caja de Ahorros)")

col1, col2 = st.columns([1, 2])

with col1:
    st.header("Datos del Préstamo")
    tipo_operacion = st.text_input("Tipo Operación", "CREDI TODO")
    socio = st.text_input("Cliente / Socio", "SAMANIEGO PASACA CECIBEL DE LOS ANGELES")
    cedula = st.text_input("Cédula", "1104500168")
    garante = st.text_input("Nombre del Garante", "HERNRY GONZÁLEZ") 
    
    monto = st.number_input("Monto ($)", min_value=1.0, value=250.0, step=10.0)
    tasa = st.number_input("Tasa Nominal (%)", min_value=0.1, value=10.0, step=0.1, format="%.4f")
    
    tipo_plazo = st.radio("Tipo de Plazo", ["Meses", "Días"])
    plazo = st.number_input(f"Plazo en {tipo_plazo}", min_value=1, value=3, step=1)
    
    st.markdown("---")
    st.subheader("Fechas")
    # Nuevo campo para la fecha de emisión del documento
    fecha_documento = st.date_input("Fecha de Emisión del Documento", datetime.now())
    fecha_inicio = st.date_input("Fecha de 1er Pago", datetime(2026, 8, 30))

with col2:
    if st.button("Calcular Amortización", type="primary"):
        df_amortizacion, cuota_base = calcular_amortizacion(monto, tasa, plazo, fecha_inicio, tipo_plazo)
        
        st.subheader("Vista Previa de la Tabla")
        df_display = df_amortizacion.copy()
        for col in ["SALDO CAP.", "CAPITAL", "INTERES", "CUOTA"]:
            df_display[col] = df_display[col].apply(lambda x: f"${x:,.2f}")
            
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Pasamos la nueva variable fecha_documento a la función de generar PDF
        pdf_bytes = generar_pdf(df_amortizacion, monto, tasa, plazo, fecha_inicio, tipo_plazo, socio, cedula, tipo_operacion, garante, fecha_documento)
        b64 = base64.b64encode(pdf_bytes).decode('latin1')
        
        st.markdown(
            f'<br><a href="data:application/pdf;base64,{b64}" download="Amortizacion_{cedula}.pdf" '
            f'style="background-color: #17366b; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">'
            f'📥 Generar Documento PDF</a>',
            unsafe_allow_html=True
        )
