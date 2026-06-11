"""
pages/caja.py — Gestión de Caja
"""

import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
from fpdf import FPDF
from db import get_ventas, get_resumen_caja, cerrar_caja, get_cierres, get_venta_detalle
from utils import fmt_precio, MEDIOS_PAGO, get_usuario

# ── FUNCIONES LOCALES DE EXPORTACIÓN (CORREGIDAS) ────────────────────────────
def _exportar_excel_local(df, nombre_hoja="Datos"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=nombre_hoja)
    return output.getvalue()

def _exportar_pdf_local(titulo, columnas, filas):
    pdf = FPDF()
    pdf.add_page()
    
    # Usamos Arial estándar que es segura en FPDF
    pdf.set_font("Arial", style="B", size=14)
    # Limpiamos el título de caracteres especiales
    titulo_limpio = str(titulo).encode('latin-1', 'ignore').decode('latin-1')
    pdf.cell(0, 10, txt=titulo_limpio, ln=True, align="C")
    pdf.ln(8)
    
    pdf.set_font("Arial", style="B", size=10)
    ancho_col = pdf.epw / len(columnas) if columnas else 30
    
    for col in columnas:
        # Reemplazamos símbolos conflictivos en los encabezados
        col_limpio = str(col).replace("$", "ARS").replace("Nº", "No.").replace("📋", "").replace("📊", "")
        col_limpio = col_limpio.encode('latin-1', 'ignore').decode('latin-1')
        pdf.cell(ancho_col, 8, txt=col_limpio, border=1, align="C")
    pdf.ln()
    
    pdf.set_font("Arial", size=9)
    for fila in filas:
        for celda in fila:
            # Reemplazamos el símbolo '$' por 'ARS' o vacío y filtramos emojis
            celda_limpia = str(celda).replace("$", "").replace("Nº", "No.")
            # Quitamos cualquier carácter con código alto (como emojis de medios de pago)
            celda_limpia = "".join(c for c in celda_limpia if ord(c) < 128)
            celda_limpia = celda_limpia.encode('latin-1', 'ignore').decode('latin-1')
            pdf.cell(ancho_col, 8, txt=celda_limpia, border=1)
        pdf.ln()
        
    return pdf.output()


def render():
    st.title("💰 Caja")
    usuario = get_usuario()

    tab1, tab2, tab3 = st.tabs(["📊 Estado del día", "🔒 Cierre de caja", "📋 Historial"])

    # ── TAB 1: Estado del día ─────────────────────────────────────────────────
    with tab1:
        ahora = datetime.now()
        inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)

        resumen = get_resumen_caja(inicio_dia, ahora)
        ventas_hoy = get_ventas(fecha_desde=inicio_dia, fecha_hasta=ahora, limit=100)

        st.subheader(f"Resumen del {ahora.strftime('%d/%m/%Y')}")

        # Métricas principales
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total del día", fmt_precio(resumen["total_general"]))
        with c2:
            st.metric("Ventas realizadas", int(resumen["cantidad_ventas"]))
        with c3:
            ticket_prom = (float(resumen["total_general"]) / int(resumen["cantidad_ventas"])
                           if resumen["cantidad_ventas"] else 0)
            st.metric("Ticket promedio", fmt_precio(ticket_prom))
        with c4:
            st.metric("Efectivo en caja", fmt_precio(resumen["efectivo"]))

        st.markdown("---")

        # Desglose por medio de pago
        col_med, col_ventas = st.columns([1, 2])

        with col_med:
            st.subheader("Por medio de pago")
            medios_data = {
                "💵 Efectivo":       resumen["efectivo"],
                "💳 Débito":         resumen["debito"],
                "💳 Crédito":        resumen["credito"],
                "📲 Transferencia":  resumen["transferencia"],
            }
            for label, valor in medios_data.items():
                if float(valor) > 0:
                    st.markdown(f"""
                    <div style="display:flex;justify-content:space-between;align-items:center;
                                padding:10px 14px;border-radius:8px;background:#F7F3EE;
                                margin-bottom:6px;border-left:4px solid #F05A28;">
                        <span style="font-size:14px;">{label}</span>
                        <span style="font-weight:700;color:#1D3557;font-size:15px;">{fmt_precio(valor)}</span>
                    </div>
                    """, unsafe_allow_html=True)

        with col_ventas:
            st.subheader("Últimas ventas")
            if not ventas_hoy:
                st.info("No hay ventas registradas hoy.")
            else:
                df = pd.DataFrame([{
                    "Nº":       f"#{v['id']}",
                    "Hora":     v["fecha"].strftime("%H:%M") if v["fecha"] else "",
                    "Total":    fmt_precio(v["total"]),
                    "Pago":     MEDIOS_PAGO.get(v["medio_pago"], v["medio_pago"]),
                    "Cajero":   v["cajero"],
                } for v in ventas_hoy])
                st.dataframe(df, use_container_width=True, hide_index=True)

                # Exportar Ventas de Hoy
                st.markdown("###### 📥 Exportar listado de ventas actuales")
                cx1, cx2 = st.columns(2)
                with cx1:
                    columnas_v = ["No.", "Hora", "Total", "Medio Pago", "Cajero"]
                    # Pasamos los datos limpios de símbolos problemáticos al generador del PDF
                    filas_v = [[str(v["id"]), v["fecha"].strftime("%H:%M"), f"{float(v['total']):.2f}", str(MEDIOS_PAGO.get(v["medio_pago"], v["medio_pago"])), str(v["cajero"])] for v in ventas_hoy]
                    
                    try:
                        pdf_v = _exportar_pdf_local(f"Ventas del Dia {ahora.strftime('%d-%m-%Y')}", columnas_v, filas_v)
                        st.download_button("📄 PDF Ventas", data=pdf_v, file_name=f"ventas_{ahora.strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True)
                    except Exception as e:
                        st.error(f"Error PDF: {e}")
                with cx2:
                    excel_v = _exportar_excel_local(df, "Ventas de Hoy")
                    st.download_button("📊 Excel Ventas", data=excel_v, file_name=f"ventas_{ahora.strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

                # Ver detalle de venta
                with st.expander("🔍 Ver detalle de una venta"):
                    ids = [v["id"] for v in ventas_hoy]
                    venta_id = st.selectbox("Seleccioná la venta", ids,
                                            format_func=lambda x: f"Venta #{x}")
                    detalles = get_venta_detalle(venta_id)
                    if detalles:
                        df_det = pd.DataFrame([{
                            "Producto":  d["producto"],
                            "Cantidad":  d["cantidad"],
                            "P. Unit.":  fmt_precio(d["precio_unit"]),
                            "Subtotal":  fmt_precio(d["subtotal"]),
                        } for d in detalles])
                        st.dataframe(df_det, use_container_width=True, hide_index=True)
                        total_v = sum(d["subtotal"] for d in detalles)
                        st.markdown(f"**Total: {fmt_precio(total_v)}**")

    # ── TAB 2: Cierre de caja ─────────────────────────────────────────────────
    with tab2:
        st.subheader("Realizar cierre de caja")
        ahora = datetime.now()

        col1, col2 = st.columns(2)
        with col1:
            fecha_apertura = st.date_input("Fecha de apertura", value=ahora.date())
            hora_apertura  = st.time_input("Hora de apertura",  value=ahora.replace(hour=8, minute=0).time())
        with col2:
            fecha_cierre   = st.date_input("Fecha de cierre",   value=ahora.date())
            hora_cierre    = st.time_input("Hora de cierre",    value=ahora.time())

        dt_apertura = datetime.combine(fecha_apertura, hora_apertura)
        dt_cierre   = datetime.combine(fecha_cierre, hora_cierre)

        monto_apertura = st.number_input("Monto de apertura (efectivo inicial)",
                                         min_value=0.0, step=100.0, value=0.0)

        # Previsualizar resumen del período
        if st.button("📊 Previsualizar período"):
            st.session_state["preview_cierre"] = get_resumen_caja(dt_apertura, dt_cierre)

        if "preview_cierre" in st.session_state:
            r = st.session_state["preview_cierre"]
            st.markdown("---")
            st.subheader("Resumen del período")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total ventas",  fmt_precio(r["total_general"]))
                st.metric("Efectivo",       fmt_precio(r["efectivo"]))
            with c2:
                st.metric("Cant. ventas",   int(r["cantidad_ventas"]))
                st.metric("Débito",         fmt_precio(r["debito"]))
            with c3:
                total_digital = float(r["debito"]) + float(r["credito"]) + float(r["transferencia"])
                st.metric("Total digital",  fmt_precio(total_digital))
                st.metric("Transferencia",  fmt_precio(r["transferencia"]))

            st.markdown("---")
            observaciones = st.text_area("Observaciones del cierre", placeholder="Opcional...")

            if st.button("🔒 Confirmar y cerrar caja", type="primary"):
                cierre_id = cerrar_caja(
                    usuario["id"], dt_apertura, dt_cierre,
                    monto_apertura, r, observaciones
                )
                st.success(f"✅ Cierre registrado (ID: {cierre_id})")
                st.session_state.pop("preview_cierre", None)
                st.balloons()
                st.rerun()

    # ── TAB 3: Historial ──────────────────────────────────────────────────────
    with tab3:
        st.subheader("Historial de cierres")
        cierres = get_cierres(limit=30)
        if not cierres:
            st.info("No hay cierres registrados.")
        else:
            df = pd.DataFrame([{
                "Apertura":    c["fecha_apertura"].strftime("%d/%m %H:%M") if c["fecha_apertura"] else "",
                "Cierre":      c["fecha_cierre"].strftime("%d/%m %H:%M")   if c["fecha_cierre"] else "",
                "Cajero":      c["cajero"],
                "Ventas":      int(c["cantidad_ventas"]),
                "Efectivo":    fmt_precio(c["total_efectivo"]),
                "Digital":     fmt_precio(float(c["total_debito"]) + float(c["total_credito"]) + float(c["total_transferencia"])),
                "Total":       fmt_precio(c["total_ventas"]),
            } for c in cierres])
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Exportar Historial
            st.markdown("###### 📥 Exportar historial de cierres")
            ch1, ch2 = st.columns(2)
            with ch1:
                cols_h = ["Apertura", "Cierre", "Cajero", "Ventas", "Efectivo", "Digital", "Total"]
                filas_h = [[
                    c["fecha_apertura"].strftime("%d/%m %H:%M") if c["fecha_apertura"] else "",
                    c["fecha_cierre"].strftime("%d/%m %H:%M") if c["fecha_cierre"] else "",
                    str(c["cajero"]),
                    str(c["cantidad_ventas"]),
                    f"{float(c['total_efectivo']):.2f}",
                    f"{(float(c['total_debito']) + float(c['total_credito']) + float(c['total_transferencia'])):.2f}",
                    f"{float(c['total_ventas']):.2f}"
                ] for c in cierres]
                
                try:
                    pdf_h = _exportar_pdf_local("Historial de Cierres de Caja", cols_h, filas_h)
                    st.download_button("📄 PDF Historial", data=pdf_h, file_name="historial_cierres.pdf", mime="application/pdf", use_container_width=True)
                except Exception as e:
                    st.error(f"Error PDF: {e}")
            with ch2:
                excel_h = _exportar_excel_local(df, "Historial Cierres")
                st.download_button("📊 Excel Historial", data=excel_h, file_name="historial_cierres.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                    
