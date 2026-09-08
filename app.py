import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from fpdf import FPDF
import base64
from decimal import Decimal, ROUND_HALF_UP

# --- 0. FUNCIÓN DE REDONDEO FINANCIERO ESTRICTO ---
def redondear(valor):
    return float(Decimal(str(valor)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

# --- 1. LÓGICA DE CÁLCULO ---
def calcular_amortizacion(monto, tasa_anual, plazo, fecha_inicio, tipo_plazo, dias_desfase):
    filas = []
    saldo = redondear(monto)
    fecha_pago = fecha_inicio
    
    tasa_diaria = (tasa_anual / 100) / 360
    
    if tipo_plazo == "Meses":
        tasa_periodo = (tasa_anual / 100) / 12
    else: 
        tasa_periodo = tasa_diaria
        
    # Calculamos la cuota fija base
    valor_cuota_pura = monto * (tasa_periodo * (1 + tasa_periodo)**plazo) / ((1 + tasa_periodo)**plazo - 1)
    cuota_fija = redondear(valor_cuota_pura)
    
    interes_extra = redondear(monto * tasa_diaria * dias_desfase)

    for i in range(1, plazo + 1):
        interes = redondear(saldo * tasa_periodo)
        
        # En los meses normales, el capital es la diferencia
        capital = redondear(cuota_fija - interes)
        
        # Lógica de desfase
        if i == 1:
            interes_a_cobrar = redondear(interes + interes_extra)
            cuota_a_cobrar = redondear(cuota_fija + interes_extra)
        else:
            interes_a_cobrar = interes
            cuota_a_cobrar = cuota_fija
            
        saldo_mostrar = saldo
        
        # EL TRUCO DEL BANCO PARA LA ÚLTIMA CUOTA
        if i == plazo:
            # Obligamos a que la cuota sea la misma
            # Y el capital absorbe la matemática para cuadrar
            capital = redondear(cuota_a_cobrar - interes_a_cobrar)
            # Mostramos el saldo exactamente igual al capital para que visualmente de 0
            saldo_mostrar = capital 
            saldo = 0.00
        else:
            saldo = redondear(saldo - capital)

        filas.append({
            "Div": i,
            "FEC. PAG": fecha_pago.strftime("%Y/%m/%d"),
            "SALDO CAP.": saldo_mostrar,
            "CAPITAL": capital,
            "INTERES": interes_a_cobrar,
            "CUOTA": cuota_a_cobrar
        })
        
        if tipo_plazo == "Meses":
            fecha_pago = fecha_pago + relativedelta(months=1)
        else:
            fecha_pago = fecha_pago + timedelta(days=1)
            
    df = pd.DataFrame(filas)
    return df, cuota_fija

# --- 2. GENERACIÓN DEL PDF ---
def generar_pdf(df, monto, tasa, plazo, fecha_inicio, tipo_plazo, socio, cedula, tipo_operacion, garante, fecha_documento):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    pdf.set_font("Courier", 'B', 12)
    pdf.cell(0, 5, "CAJA DE AHORROS LA UNION HACE LA FUERZA", ln=1, align='C')
    pdf.set_font("Courier", '', 10)
    pdf.cell(0, 5, "TABLA DE AMORTIZACION", ln=1, align='C')
    pdf.ln(5)
    
    pdf.set_font("Courier", '', 9)
    # Fila 1
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
    
    for _, row in df.iterrows():
        pdf.set_x(20)
        pdf.cell(anchos[0], 5, str(row['Div']), 0, align='C')
        pdf.cell(anchos[1], 5, row['FEC. PAG'], 0, align='C')
        pdf.cell(anchos[2], 5, f"{row['SALDO CAP.']:.2f}", 0, align='C')
        pdf.cell(anchos[3], 5, f"{row['CAPITAL']:.2f}", 0, align='C')
        pdf.cell(anchos[4], 5, f"{row['INTERES']:.2f}", 0, align='C')
        pdf.cell(anchos[5], 5, f"{row['CUOTA']:.2f}", 0, align='C')
        pdf.ln()
        
    pdf.line(20, pdf.get_y(), sum(anchos)+20, pdf.get_y())
    pdf.set_font("Courier", 'B', 9)
    pdf.set_x(20)
    
    # EL TRUCO PARA LOS TOTALES: Forzamos la presentación teórica, no sumamos las columnas
    tot_cuota = redondear(df['CUOTA'].sum())
    tot_capital = monto 
    tot_interes = redondear(tot_cuota - tot_capital)
    
    pdf.cell(anchos[0] + anchos[1], 6, "TOTALES", 0, align='L')
    pdf.cell(anchos[2], 6, "0.00", 0, align='C') 
    pdf.cell(anchos[3], 6, f"{tot_capital:.2f}", 0, align='C')
    pdf.cell(anchos[4], 6, f"{tot_interes:.2f}", 0, align='C')
    pdf.cell(anchos[5], 6, f"{tot_cuota:.2f}", 0, align='C')
    
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
    socio = st.text_input("Cliente / Socio", "JHOANA ÁLVAREZ")
    cedula = st.text_input("Cédula", "088318044")
    garante = st.text_input("Nombre del Garante", "HERNRY GONZÁLEZ") 
    
    monto = st.number_input("Monto ($)", min_value=1.0, value=600.0, step=10.0)
    tasa = st.number_input("Tasa Nominal (%)", min_value=0.1, value=10.0, step=0.1, format="%.4f")
    
    tipo_plazo = st.radio("Tipo de Plazo", ["Meses", "Días"])
    plazo = st.number_input(f"Plazo en {tipo_plazo}", min_value=1, value=8, step=1)
    
    dias_desfase = st.number_input("Días de desfase (Ajuste 1ra cuota)", min_value=0, value=0, step=1)
    
    st.markdown("---")
    st.subheader("Fechas")
    fecha_documento = st.date_input("Fecha de Emisión del Documento", datetime(2026, 9, 7))
    fecha_inicio = st.date_input("Fecha de 1er Pago", datetime(2026, 10, 7))

with col2:
    if st.button("Calcular Amortización", type="primary"):
        df_amortizacion, cuota_base = calcular_amortizacion(monto, tasa, plazo, fecha_inicio, tipo_plazo, dias_desfase)
        
        st.subheader("Vista Previa de la Tabla")
        df_display = df_amortizacion.copy()
        for col in ["SALDO CAP.", "CAPITAL", "INTERES", "CUOTA"]:
            df_display[col] = df_display[col].apply(lambda x: f"${x:,.2f}")
            
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        pdf_bytes = generar_pdf(df_amortizacion, monto, tasa, plazo, fecha_inicio, tipo_plazo, socio, cedula, tipo_operacion, garante, fecha_documento)
        b64 = base64.b64encode(pdf_bytes).decode('latin1')
        
        st.markdown(
            f'<br><a href="data:application/pdf;base64,{b64}" download="Amortizacion_{cedula}.pdf" '
            f'style="background-color: #17366b; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">'
            f'📥 Generar Documento PDF</a>',
            unsafe_allow_html=True
        )
