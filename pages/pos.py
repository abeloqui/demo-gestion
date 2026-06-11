"""
pages/pos.py — Punto de Venta (POS)
"""

import streamlit as st
from db import get_productos, registrar_venta, get_categorias
from utils import fmt_precio, MEDIOS_PAGO, get_usuario


def render():
    st.title("🛒 Punto de Venta")

    usuario = get_usuario()
    productos = get_productos(solo_activos=True)
    categorias = get_categorias()

    # ── Inicializar carrito ───────────────────────────────────────────────────
    if "carrito" not in st.session_state:
        st.session_state["carrito"] = []

    carrito = st.session_state["carrito"]

    # ── Layout: buscador + carrito ────────────────────────────────────────────
    col_prod, col_carrito = st.columns([1.4, 1])

    # ── Columna izquierda: productos ──────────────────────────────────────────
    with col_prod:
        st.subheader("Productos")

        # Filtros
        c1, c2 = st.columns([2, 1])
        with c1:
            busqueda = st.text_input("🔍 Buscar producto", placeholder="Escribí el nombre...", label_visibility="collapsed")
        with c2:
            cats = ["Todas"] + [c["nombre"] for c in categorias]
            cat_sel = st.selectbox("Categoría", cats, label_visibility="collapsed")

        # Filtrar lista
        filtrados = productos
        if busqueda:
            filtrados = [p for p in filtrados if busqueda.lower() in p["nombre"].lower()]
        if cat_sel != "Todas":
            filtrados = [p for p in filtrados if p.get("categoria") == cat_sel]

        if not filtrados:
            st.info("No se encontraron productos.")
        else:
            # Grilla de productos 3 columnas
            cols = st.columns(3)
            for i, prod in enumerate(filtrados):
                with cols[i % 3]:
                    stock_ok = float(prod["stock_actual"]) > 0
                    color_stock = "#1B7A4A" if stock_ok else "#DC2626"
                    st.markdown(f"""
                    <div style="border:1px solid #E0D9D0;border-radius:10px;
                                padding:12px;margin-bottom:8px;background:#fff;
                                box-shadow:0 1px 3px rgba(0,0,0,0.06);">
                        <div style="font-size:13px;font-weight:600;color:#1A1C22;
                                    line-height:1.3;margin-bottom:6px;min-height:36px;">
                            {prod['nombre']}
                        </div>
                        <div style="font-size:11px;color:#6B7280;margin-bottom:6px;">
                            {prod.get('categoria','') or ''}
                        </div>
                        <div style="font-size:16px;font-weight:700;color:#F05A28;margin-bottom:4px;">
                            {fmt_precio(prod['precio_venta'])}
                        </div>
                        <div style="font-size:10px;color:{color_stock};font-weight:500;">
                            Stock: {prod['stock_actual']:g} {prod['unidad']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if stock_ok:
                        if st.button("+ Agregar", key=f"add_{prod['id']}", use_container_width=True):
                            _agregar_al_carrito(prod)
                            st.rerun()
                    else:
                        st.button("Sin stock", key=f"nostock_{prod['id']}",
                                  disabled=True, use_container_width=True)

    # ── Columna derecha: carrito ──────────────────────────────────────────────
    with col_carrito:
        st.subheader("🧾 Ticket actual")

        if not carrito:
            st.markdown("""
            <div style="border:2px dashed #E0D9D0;border-radius:12px;
                        padding:40px 20px;text-align:center;color:#9CA3AF;">
                <div style="font-size:40px;margin-bottom:8px;">🛒</div>
                <div>El carrito está vacío.<br>Agregá productos desde la grilla.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Items del carrito
            total = 0
            for idx, item in enumerate(carrito):
                subtotal = item["cantidad"] * item["precio_unit"]
                total += subtotal

                with st.container():
                    c1, c2, c3 = st.columns([2.5, 1.5, 0.8])
                    with c1:
                        st.markdown(f"**{item['nombre']}**")
                        st.caption(fmt_precio(item["precio_unit"]) + " c/u")
                    with c2:
                        nueva_cant = st.number_input(
                            "Cant.", min_value=0.0,
                            max_value=float(item["stock_max"]),
                            value=float(item["cantidad"]),
                            step=1.0,
                            key=f"cant_{idx}",
                            label_visibility="collapsed"
                        )
                        if nueva_cant != item["cantidad"]:
                            if nueva_cant == 0:
                                st.session_state["carrito"].pop(idx)
                            else:
                                st.session_state["carrito"][idx]["cantidad"] = nueva_cant
                            st.rerun()
                    with c3:
                        st.markdown(f"**{fmt_precio(subtotal)}**")
                        if st.button("✕", key=f"del_{idx}"):
                            st.session_state["carrito"].pop(idx)
                            st.rerun()

                st.markdown("<hr style='margin:4px 0;border-color:#E0D9D0;'>", unsafe_allow_html=True)

            # Total
            st.markdown(f"""
            <div style="background:#1D3557;border-radius:10px;padding:16px;
                        text-align:center;margin:12px 0;">
                <div style="font-size:12px;color:rgba(255,255,255,0.6);margin-bottom:4px;">TOTAL</div>
                <div style="font-size:30px;font-weight:700;color:#fff;">{fmt_precio(total)}</div>
            </div>
            """, unsafe_allow_html=True)

            # Medio de pago
            medio_label = st.selectbox(
                "Medio de pago",
                list(MEDIOS_PAGO.values()),
                key="medio_pago_sel"
            )
            medio_key = {v: k for k, v in MEDIOS_PAGO.items()}[medio_label]

            c1, c2 = st.columns(2)
            with c1:
                if st.button("🗑️ Vaciar", use_container_width=True):
                    st.session_state["carrito"] = []
                    st.rerun()
            with c2:
                if st.button("✅ Cobrar", use_container_width=True, type="primary"):
                    _confirmar_venta(usuario, carrito, medio_key, total)


def _agregar_al_carrito(prod):
    carrito = st.session_state["carrito"]
    # Si ya está, suma 1
    for item in carrito:
        if item["producto_id"] == prod["id"]:
            if item["cantidad"] < float(prod["stock_actual"]):
                item["cantidad"] += 1
            return
    carrito.append({
        "producto_id": prod["id"],
        "nombre":      prod["nombre"],
        "precio_unit": float(prod["precio_venta"]),
        "cantidad":    1.0,
        "stock_max":   float(prod["stock_actual"]),
    })


def _confirmar_venta(usuario, carrito, medio_pago, total):
    items = [
        {
            "producto_id": i["producto_id"],
            "cantidad":    i["cantidad"],
            "precio_unit": i["precio_unit"],
        }
        for i in carrito
    ]
    venta_id = registrar_venta(usuario["id"], items, medio_pago)
    st.session_state["carrito"] = []
    st.session_state["ultima_venta"] = {
        "id": venta_id, "total": total, "medio": medio_pago
    }
    st.success(f"✅ Venta #{venta_id} registrada — Total: {fmt_precio(total)}")
    st.balloons()
    st.rerun()
