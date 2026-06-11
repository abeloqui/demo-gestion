"""
pages/reportes.py — Reportes y estadísticas
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from db import (get_reporte_productos_mas_vendidos, get_reporte_ventas_por_dia,
                get_productos_stock_bajo, get_ventas)
from utils import fmt_precio


def render():
    st.title("📊 Reportes y Estadísticas")

    # ── Selector de período ───────────────────────────────────────────────────
    col1, col2, col3 = st.columns([1, 1, 2])
    hoy = date.today()
    with col1:
        fecha_desde = st.date_input("Desde", value=hoy - timedelta(days=30))
    with col2:
        fecha_hasta = st.date_input("Hasta", value=hoy)
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        if c1.button("Hoy"):
            st.session_state["f_desde"] = hoy
            st.session_state["f_hasta"] = hoy
            st.rerun()
        if c2.button("Esta semana"):
            st.session_state["f_desde"] = hoy - timedelta(days=hoy.weekday())
            st.session_state["f_hasta"] = hoy
            st.rerun()
        if c3.button("Este mes"):
            st.session_state["f_desde"] = hoy.replace(day=1)
            st.session_state["f_hasta"] = hoy
            st.rerun()

    # Aplicar estado si existe
    if "f_desde" in st.session_state:
        fecha_desde = st.session_state.pop("f_desde")
    if "f_hasta" in st.session_state:
        fecha_hasta = st.session_state.pop("f_hasta")

    dt_desde = datetime.combine(fecha_desde, datetime.min.time())
    dt_hasta = datetime.combine(fecha_hasta, datetime.max.time().replace(microsecond=0))

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["📈 Ventas por día", "🏆 Más vendidos", "⚠️ Stock bajo"])

    # ── TAB 1: Ventas por día ─────────────────────────────────────────────────
    with tab1:
        ventas_dia = get_reporte_ventas_por_dia(dt_desde, dt_hasta)

        if not ventas_dia:
            st.info("No hay ventas en el período seleccionado.")
        else:
            df = pd.DataFrame(ventas_dia)
            df["dia"] = pd.to_datetime(df["dia"])
            df["total"] = df["total"].astype(float)

            # KPIs del período
            total_periodo   = df["total"].sum()
            total_ventas    = df["cantidad"].sum()
            dias_con_ventas = len(df)
            prom_diario     = total_periodo / dias_con_ventas if dias_con_ventas else 0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total del período", fmt_precio(total_periodo))
            c2.metric("Ventas totales",    int(total_ventas))
            c3.metric("Días con ventas",   dias_con_ventas)
            c4.metric("Promedio diario",   fmt_precio(prom_diario))

            st.markdown("---")

            # Gráfico de línea
            fig = px.area(
                df, x="dia", y="total",
                title="Ventas diarias",
                labels={"dia": "Fecha", "total": "Total ($)"},
                color_discrete_sequence=["#F05A28"],
            )
            fig.update_layout(
                plot_bgcolor="white",
                paper_bgcolor="white",
                font_family="sans-serif",
                title_font_size=16,
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="#F0EDE8"),
                hovermode="x unified",
            )
            fig.update_traces(
                line_width=2.5,
                fillcolor="rgba(240,90,40,0.12)",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Gráfico de barras cantidad
            fig2 = px.bar(
                df, x="dia", y="cantidad",
                title="Cantidad de ventas por día",
                labels={"dia": "Fecha", "cantidad": "Ventas"},
                color_discrete_sequence=["#1D3557"],
            )
            fig2.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="#F0EDE8"),
            )
            st.plotly_chart(fig2, use_container_width=True)

    # ── TAB 2: Más vendidos ───────────────────────────────────────────────────
    with tab2:
        mas_vendidos = get_reporte_productos_mas_vendidos(dt_desde, dt_hasta, limit=15)

        if not mas_vendidos:
            st.info("No hay datos de ventas en el período.")
        else:
            df_mv = pd.DataFrame(mas_vendidos)
            df_mv["total_facturado"] = df_mv["total_facturado"].astype(float)
            df_mv["unidades_vendidas"] = df_mv["unidades_vendidas"].astype(float)

            col_graf, col_tabla = st.columns([1.4, 1])

            with col_graf:
                # Top 10 por facturación
                df_top = df_mv.head(10).sort_values("total_facturado")
                fig = px.bar(
                    df_top, x="total_facturado", y="nombre",
                    orientation="h",
                    title="Top 10 por facturación",
                    labels={"total_facturado": "Total ($)", "nombre": ""},
                    color="total_facturado",
                    color_continuous_scale=["#1D3557", "#F05A28"],
                )
                fig.update_layout(
                    plot_bgcolor="white", paper_bgcolor="white",
                    coloraxis_showscale=False,
                    xaxis=dict(gridcolor="#F0EDE8"),
                    yaxis=dict(showgrid=False),
                    height=360,
                )
                st.plotly_chart(fig, use_container_width=True)

            with col_tabla:
                st.subheader("Ranking completo")
                df_show = df_mv[["nombre", "unidades_vendidas", "total_facturado"]].copy()
                df_show.columns = ["Producto", "Unidades", "Facturado"]
                df_show["Facturado"] = df_show["Facturado"].apply(fmt_precio)
                df_show.index = range(1, len(df_show) + 1)
                st.dataframe(df_show, use_container_width=True)

            # Pie por categoría
            if "categoria" in df_mv.columns:
                df_cat = df_mv.groupby("categoria")["total_facturado"].sum().reset_index()
                fig_pie = px.pie(
                    df_cat, values="total_facturado", names="categoria",
                    title="Facturación por categoría",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                fig_pie.update_layout(paper_bgcolor="white")
                st.plotly_chart(fig_pie, use_container_width=True)

    # ── TAB 3: Stock bajo ─────────────────────────────────────────────────────
    with tab3:
        bajos = get_productos_stock_bajo()
        if not bajos:
            st.success("✅ Todos los productos tienen stock suficiente.")
        else:
            st.error(f"⚠️ {len(bajos)} producto(s) necesitan reposición")

            df_b = pd.DataFrame([{
                "Producto":   p["nombre"],
                "Categoría":  p.get("categoria") or "—",
                "Stock actual": float(p["stock_actual"]),
                "Mínimo":     float(p["stock_minimo"]),
                "Diferencia": float(p["stock_actual"]) - float(p["stock_minimo"]),
                "Unidad":     p["unidad"],
            } for p in bajos])

            fig = px.bar(
                df_b, x="Producto", y=["Stock actual", "Mínimo"],
                barmode="group",
                title="Stock actual vs. Mínimo",
                color_discrete_map={"Stock actual": "#F05A28", "Mínimo": "#1D3557"},
            )
            fig.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                xaxis=dict(tickangle=-30, showgrid=False),
                yaxis=dict(gridcolor="#F0EDE8"),
                legend_title="",
            )
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(
                df_b[["Producto", "Categoría", "Stock actual", "Mínimo", "Diferencia", "Unidad"]],
                use_container_width=True,
                hide_index=True,
            )
