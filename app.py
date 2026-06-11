"""
app.py — Entry point: login y navegación principal
Sistema de Gestión Comercial — Demo
"""

import streamlit as st
from utils import page_config, apply_styles, get_usuario, is_admin
from db import init_db, login, get_productos_stock_bajo

page_config("Sistema de Gestión")
apply_styles()

# Ocultar el menú de navegación nativo superior de Streamlit
st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)


def pantalla_login():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-bottom:32px;">
            <div style="font-size:52px;">🛒</div>
            <h1 style="color:#1D3557;margin:8px 0 4px;">Sistema de Gestión</h1>
            <p style="color:#6B7280;font-size:14px;">Ingresá tus credenciales para continuar</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            usuario = st.text_input("Usuario", placeholder="admin")
            password = st.text_input("Contraseña", type="password", placeholder="••••••")
            submitted = st.form_submit_button("Ingresar", use_container_width=True, type="primary")

        if submitted:
            user = login(usuario.strip(), password)
            if user:
                st.session_state["usuario"] = user
                st.session_state["carrito"] = []
                st.session_state["caja_abierta"] = None
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

        st.markdown("""
        <div style="text-align:center;margin-top:24px;color:#9CA3AF;font-size:12px;">
            Demo: <code>admin / admin123</code> &nbsp;|&nbsp; <code>operador / op123</code>
        </div>
        """, unsafe_allow_html=True)


def sidebar_nav():
    u = get_usuario()
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:16px 0 20px;">
            <div style="font-size:28px;text-align:center;margin-bottom:8px;">🛒</div>
            <div style="text-align:center;font-size:15px;font-weight:600;color:#fff;">
                Sistema de Gestión
            </div>
            <div style="text-align:center;font-size:11px;color:rgba(255,255,255,0.5);margin-top:4px;">
                v1.0 — Demo
            </div>
        </div>
        <hr style="border-color:rgba(255,255,255,0.15);margin:0 0 16px;">
        <div style="font-size:12px;color:rgba(255,255,255,0.5);padding:0 4px 8px;">
            👤 {u.get('nombre','')}<br>
            <span style="font-size:10px;background:rgba(255,255,255,0.1);
                border-radius:10px;padding:1px 8px;">{u.get('rol','').upper()}</span>
        </div>
        """, unsafe_allow_html=True)

        opciones = ["🏠 Inicio", "🛒 Punto de Venta", "📦 Stock", "💰 Caja", "📊 Reportes"]
        if is_admin():
            opciones.append("⚙️ Administración")

        pagina = st.radio("Navegación", opciones, label_visibility="collapsed")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Cerrar sesión", use_container_width=True):
            for key in ["usuario", "carrito", "caja_abierta"]:
                st.session_state.pop(key, None)
            st.rerun()

    return pagina


def pagina_inicio():
    u = get_usuario()
    st.title(f"Bienvenido, {u.get('nombre', '')} 👋")
    st.caption("Panel principal del sistema")

    stock_bajo = get_productos_stock_bajo()
    if stock_bajo:
        st.warning(
            f"⚠️ **{len(stock_bajo)} producto(s) con stock bajo.** "
            "Revisá el módulo de Stock para más detalles."
        )

    st.markdown("---")
    st.subheader("Acceso rápido")

    col1, col2, col3, col4 = st.columns(4)
    modulos = [
        ("🛒", "Punto de Venta", "Registrá ventas y cobrá al cliente", "#F05A28"),
        ("📦", "Stock",          "Controlá inventario y recibí mercadería", "#1D3557"),
        ("💰", "Caja",           "Apertura, cierre y resumen del día", "#1B7A4A"),
        ("📊", "Reportes",       "Estadísticas y rankings de productos", "#2B4E7A"),
    ]
    for col, (icon, titulo, desc, color) in zip([col1, col2, col3, col4], modulos):
        with col:
            st.markdown(f"""
            <div style="background:{color};border-radius:12px;padding:20px 16px;
                        text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.12);">
                <div style="font-size:32px;">{icon}</div>
                <div style="font-size:14px;font-weight:700;color:#fff;margin:8px 0 4px;">{titulo}</div>
                <div style="font-size:11px;color:rgba(255,255,255,0.65);line-height:1.4;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Inicializar DB
    try:
        init_db()
    except Exception as e:
        st.error(f"Error de conexión a la base de datos: {e}")
        st.info("Verificá que la variable `DATABASE_URL` esté configurada en los secrets.")
        st.stop()

    # Login
    if not st.session_state.get("usuario"):
        pantalla_login()
        return

    # Inicializar estado de sesión
    if "carrito" not in st.session_state:
        st.session_state["carrito"] = []
    if "caja_abierta" not in st.session_state:
        st.session_state["caja_abierta"] = None

    # Navegación
    pagina = sidebar_nav()

    if pagina == "🏠 Inicio":
        pagina_inicio()
    elif pagina == "🛒 Punto de Venta":
        from pages.pos import render
        render()
    elif pagina == "📦 Stock":
        from pages.stock import render
        render()
    elif pagina == "💰 Caja":
        from pages.caja import render
        render()
    elif pagina == "📊 Reportes":
        from pages.reportes import render
        render()
    elif pagina == "⚙️ Administración":
        from pages.admin import render
        render()


if __name__ == "__main__":
    main()
    
