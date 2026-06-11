"""
pages/caja.py — Gestión de Caja
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from db import get_ventas, get_resumen_caja, cerrar_caja, get_cierres, get_venta_detalle
from utils import fmt_precio, MEDIOS_PAGO, get_usuario


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
