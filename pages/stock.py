"""
pages/stock.py — Gestión de Stock
"""

import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from db import (get_productos, get_categorias, ajustar_stock,
                upsert_producto, get_productos_stock_bajo)
from utils import fmt_precio, fmt_stock, get_usuario, is_admin, require_admin


# ── FUNCIONES LOCALES DE EXPORTACIÓN (CORREGIDAS) ────────────────────────────
def _exportar_excel_local(df, nombre_hoja="Datos"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=nombre_hoja)
    return output.getvalue()

def _exportar_pdf_local(titulo, columnas, filas):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", style="B", size=14)
    titulo_limpio = str(titulo).encode('latin-1', 'ignore').decode('latin-1')
    pdf.cell(0, 10, txt=titulo_limpio, ln=True, align="C")
    pdf.ln(8)
    
    pdf.set_font("Arial", style="B", size=9)
    ancho_col = pdf.epw / len(columnas) if columnas else 30
    for col in columnas:
        col_limpio = str(col).replace("$", "ARS").replace("📋", "").replace("⚠️", "")
        col_limpio = col_limpio.encode('latin-1', 'ignore').decode('latin-1')
        pdf.cell(ancho_col, 8, txt=col_limpio, border=1, align="C")
    pdf.ln()
    
    pdf.set_font("Arial", size=8)
    for fila in filas:
        for celda in fila:
            celda_limpia = str(celda).replace("$", "")
            celda_limpia = "".join(c for c in celda_limpia if ord(c) < 128)
            celda_limpia = celda_limpia.encode('latin-1', 'ignore').decode('latin-1')
            pdf.cell(ancho_col, 8, txt=celda_limpia, border=1)
        pdf.ln()
    return pdf.output()


def render():
    st.title("📦 Gestión de Stock")
    usuario = get_usuario()

    tab1, tab2, tab3 = st.tabs(["📋 Inventario", "🔄 Ajustar Stock", "⚠️ Alertas"])

    # ── TAB 1: Inventario ─────────────────────────────────────────────────────
    with tab1:
        col_left, col_right = st.columns([3, 1])
        with col_left:
            busqueda = st.text_input("🔍 Buscar", placeholder="Nombre de producto...", label_visibility="collapsed")
        with col_right:
            if is_admin():
                if st.button("➕ Nuevo producto", use_container_width=True, type="primary"):
                    st.session_state["form_producto"] = {}
                    st.session_state["mostrar_form_prod"] = True

        productos = get_productos(solo_activos=False)
        if busqueda:
            productos = [p for p in productos if busqueda.lower() in p["nombre"].lower()]

        if not productos:
            st.info("No hay productos cargados.")
        else:
            # Tabla
            df = pd.DataFrame([{
                "ID":          p["id"],
                "Producto":    p["nombre"],
                "Categoría":   p.get("categoria") or "—",
                "Stock":       f"{float(p['stock_actual']):g} {p['unidad']}",
                "Mínimo":      f"{float(p['stock_minimo']):g}",
                "P. Venta":    fmt_precio(p["precio_venta"]),
                "P. Costo":    fmt_precio(p["precio_costo"]),
                "Margen":      _margen(p),
                "Estado":      "OK" if float(p["stock_actual"]) > float(p["stock_minimo"]) else "Bajo",
                "Activo":      "✓" if p["activo"] else "✗",
            } for p in productos])

            st.dataframe(
                df, use_container_width=True, hide_index=True,
                column_config={
                    "ID":      st.column_config.NumberColumn(width="small"),
                    "Stock":   st.column_config.TextColumn(width="medium"),
                    "Estado":  st.column_config.TextColumn(width="small"),
                    "Activo":  st.column_config.TextColumn(width="small"),
                }
            )

            # Exportar Inventario Completo
            st.markdown("###### 📥 Exportar Maestro de Inventario")
            ce1, ce2 = st.columns(2)
            with ce1:
                cols_i = ["ID", "Producto", "Categoria", "Stock", "P.Venta", "Estado"]
                filas_i = [[str(p["id"]), str(p["nombre"]), str(p.get("categoria") or "—"), f"{float(p['stock_actual']):g} {p['unidad']}", f"{float(p['precio_venta']):.2f}", "OK" if float(p["stock_actual"]) > float(p["stock_minimo"]) else "Bajo"] for p in productos]
                try:
                    pdf_i = _exportar_pdf_local("Maestro de Inventario Completo", cols_i, filas_i)
                    st.download_button("📄 PDF Inventario", data=pdf_i, file_name="inventario_completo.pdf", mime="application/pdf", use_container_width=True)
                except Exception as e:
                    st.error(f"Error PDF: {e}")
            with ce2:
                excel_i = _exportar_excel_local(df, "Inventario")
                st.download_button("📊 Excel Inventario", data=excel_i, file_name="inventario_completo.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

            if is_admin():
                st.caption("Para editar un producto, ingresá su ID abajo:")
                edit_id = st.number_input("ID a editar", min_value=1, step=1, key="edit_prod_id", label_visibility="collapsed", placeholder="ID del producto")
                if st.button("✏️ Editar producto"):
                    prod = next((p for p in productos if p["id"] == edit_id), None)
                    if prod:
                        st.session_state["form_producto"] = prod
                        st.session_state["mostrar_form_prod"] = True
                    else:
                        st.error("ID no encontrado.")

        if is_admin() and st.session_state.get("mostrar_form_prod"):
            _form_producto()

    # ── TAB 2: Ajustar Stock ──────────────────────────────────────────────────
    with tab2:
        st.subheader("Registrar movimiento de stock")
        productos_activos = get_productos(solo_activos=True)
        nombres_prod = {p["nombre"]: p for p in productos_activos}

        c1, c2 = st.columns(2)
        with c1:
            prod_sel_nombre = st.selectbox("Producto", list(nombres_prod.keys()))
        with c2:
            tipo = st.selectbox("Tipo de movimiento", ["entrada", "salida", "ajuste"], format_func=lambda x: {"entrada": "📥 Entrada (recepción/compra)", "salida": "📤 Salida (pérdida/retiro)", "ajuste": "🔧 Ajuste de inventario"}[x])

        prod_sel = nombres_prod.get(prod_sel_nombre)
        if prod_sel:
            st.info(f"Stock actual: **{fmt_stock(prod_sel['stock_actual'], prod_sel['unidad'])}** |  Mínimo: {fmt_stock(prod_sel['stock_minimo'], prod_sel['unidad'])}")

        c1, c2 = st.columns(2)
        with c1:
            cantidad = st.number_input("Cantidad", min_value=0.01, step=1.0, value=1.0)
        with c2:
            motivo = st.text_input("Motivo / Observación", placeholder="Ej: Compra proveedor, Merma, etc.")

        if st.button("💾 Registrar movimiento", type="primary"):
            if not motivo.strip():
                st.error("Ingresá un motivo para el movimiento.")
            else:
                ajustar_stock(prod_sel["id"], cantidad, tipo, motivo.strip(), usuario["id"])
                st.success(f"✅ Movimiento registrado: {tipo} de {cantidad:g} {prod_sel['unidad']} en **{prod_sel_nombre}**")
                st.rerun()

    # ── TAB 3: Alertas ────────────────────────────────────────────────────────
    with tab3:
        st.subheader("Productos con stock bajo o agotado")
        bajos = get_productos_stock_bajo()
        if not bajos:
            st.success("✅ Todos los productos tienen stock suficiente.")
        else:
            st.error(f"⚠️ {len(bajos)} producto(s) requieren reposición")
            df_bajo = pd.DataFrame([{
                "Producto":   p["nombre"],
                "Categoría":  p.get("categoria") or "—",
                "Stock":      f"{float(p['stock_actual']):g} {p['unidad']}",
                "Mínimo":     f"{float(p['stock_minimo']):g} {p['unidad']}",
                "Diferencia": f"{float(p['stock_actual']) - float(p['stock_minimo']):+g}",
            } for p in bajos])
            st.dataframe(df_bajo, use_container_width=True, hide_index=True)

            # Exportar Alertas
            st.markdown("###### 📥 Exportar lista de reposición / faltantes")
            ca1, ca2 = st.columns(2)
            with ca1:
                cols_a = ["Producto", "Categoria", "Stock Actual", "Minimo", "Diferencia"]
                filas_a = [[str(p["nombre"]), str(p.get("categoria") or "—"), f"{float(p['stock_actual']):g} {p['unidad']}", f"{float(p['stock_minimo']):g} {p['unidad']}", f"{float(p['stock_actual']) - float(p['stock_minimo']):+g}"] for p in bajos]
                try:
                    pdf_a = _exportar_pdf_local("Lista de Productos para Reposicion", cols_a, filas_a)
                    st.download_button("📄 PDF Faltantes", data=pdf_a, file_name="lista_reposicion.pdf", mime="application/pdf", use_container_width=True)
                except Exception as e:
                    st.error(f"Error PDF: {e}")
            with ca2:
                excel_a = _exportar_excel_local(df_bajo, "Reposicion")
                st.download_button("📊 Excel Faltantes", data=excel_a, file_name="lista_reposicion.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)


def _margen(p) -> str:
    try:
        venta = float(p["precio_venta"])
        costo = float(p["precio_costo"])
        if costo > 0:
            return f"{((venta - costo) / costo * 100):.0f}%"
    except Exception:
        pass
    return "—"


def _form_producto():
    prod = st.session_state.get("form_producto", {})
    es_nuevo = not prod.get("id")
    categorias = get_categorias()
    cat_nombres = [c["nombre"] for c in categorias]
    cat_ids = {c["nombre"]: c["id"] for c in categorias}

    st.markdown("---")
    st.subheader("✏️ " + ("Nuevo producto" if es_nuevo else f"Editar: {prod.get('nombre','')}"))

    with st.form("form_prod"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre *", value=prod.get("nombre", ""))
            cat_default = next((c["nombre"] for c in categorias if c["id"] == prod.get("categoria_id")), cat_nombres[0] if cat_nombres else "")
            categoria = st.selectbox("Categoría", cat_nombres, index=cat_nombres.index(cat_default) if cat_default in cat_nombres else 0)
            unidad = st.selectbox("Unidad", ["unidad", "kg", "litro", "docena", "cajón", "bolsa"], index=["unidad","kg","litro","docena","cajón","bolsa"].index(prod.get("unidad","unidad")) if prod.get("unidad","unidad") in ["unidad","kg","litro","docena","cajón","bolsa"] else 0)
        with c2:
            precio_venta = st.number_input("Precio de venta *", min_value=0.0, value=float(prod.get("precio_venta", 0)), step=100.0)
            precio_costo = st.number_input("Precio de costo", min_value=0.0, value=float(prod.get("precio_costo", 0)), step=100.0)
            stock_minimo = st.number_input("Stock mínimo (alerta)", min_value=0.0, value=float(prod.get("stock_minimo", 0)), step=1.0)

        if es_nuevo:
            stock_inicial = st.number_input("Stock inicial", min_value=0.0, value=0.0, step=1.0)
        activo = st.checkbox("Producto activo", value=prod.get("activo", True))

        c1, c2 = st.columns(2)
        with c1:
            submitted = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")
        with c2:
            cancelar = st.form_submit_button("Cancelar", use_container_width=True)

    if submitted:
        if not nombre.strip():
            st.error("El nombre es obligatorio.")
        else:
            data = {
                "id":           prod.get("id"),
                "nombre":       nombre.strip(),
                "categoria_id": cat_ids.get(categoria),
                "precio_venta": precio_venta,
                "precio_costo": precio_costo,
                "stock_minimo": stock_minimo,
                "unidad":       unidad,
                "activo":       activo,
            }
            if es_nuevo:
                data["stock_actual"] = stock_inicial
            upsert_producto(data)
            st.success("✅ Producto guardado correctamente.")
            st.session_state.pop("mostrar_form_prod", None)
            st.session_state.pop("form_producto", None)
            st.rerun()

    if cancelar:
        st.session_state.pop("mostrar_form_prod", None)
        st.session_state.pop("form_producto", None)
        st.rerun()
                                                       
