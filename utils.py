"""
utils.py — Helpers compartidos de UI y formato
"""

import streamlit as st


# ── Formato ───────────────────────────────────────────────────────────────────

def fmt_precio(valor) -> str:
    try:
        return f"$ {float(valor):,.0f}".replace(",", ".")
    except Exception:
        return "$ 0"


def fmt_stock(valor, unidad="unidad") -> str:
    try:
        v = float(valor)
        return f"{v:g} {unidad}"
    except Exception:
        return f"0 {unidad}"


MEDIOS_PAGO = {
    "efectivo":      "💵 Efectivo",
    "debito":        "💳 Débito",
    "credito":       "💳 Crédito",
    "transferencia": "📲 Transferencia",
}

MEDIOS_PAGO_ICONOS = {v: k for k, v in MEDIOS_PAGO.items()}


# ── Tarjetas métricas ─────────────────────────────────────────────────────────

def metric_card(label: str, value: str, delta: str = "", color: str = "#1D3557"):
    st.markdown(f"""
    <div style="
        background:{color};
        border-radius:10px;
        padding:18px 20px 14px;
        text-align:center;
        box-shadow:0 2px 8px rgba(0,0,0,0.12);
    ">
        <div style="font-size:12px;color:rgba(255,255,255,0.7);
                    letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px;">
            {label}
        </div>
        <div style="font-size:26px;font-weight:700;color:#fff;line-height:1.1;">
            {value}
        </div>
        {"<div style='font-size:11px;color:rgba(255,255,255,0.55);margin-top:4px;'>" + delta + "</div>" if delta else ""}
    </div>
    """, unsafe_allow_html=True)


def badge(texto: str, color: str = "#F05A28"):
    st.markdown(f"""
    <span style="
        background:{color};color:#fff;
        border-radius:20px;padding:3px 12px;
        font-size:12px;font-weight:600;
    ">{texto}</span>
    """, unsafe_allow_html=True)


# ── Alerta de stock bajo ──────────────────────────────────────────────────────

def alerta_stock_bajo(productos_bajos: list):
    if productos_bajos:
        nombres = ", ".join(p["nombre"] for p in productos_bajos[:4])
        extra = f" (+{len(productos_bajos)-4} más)" if len(productos_bajos) > 4 else ""
        st.warning(
            f"⚠️ **{len(productos_bajos)} producto(s) con stock bajo:** {nombres}{extra}",
            icon=None
        )


# ── Sesión ────────────────────────────────────────────────────────────────────

def check_login():
    """Retorna True si hay sesión activa, sino muestra pantalla de login."""
    return st.session_state.get("usuario") is not None


def get_usuario():
    return st.session_state.get("usuario", {})


def is_admin():
    return get_usuario().get("rol") == "admin"


def require_admin():
    if not is_admin():
        st.error("🔒 Acceso restringido. Se requiere rol administrador.")
        st.stop()


# ── Config de página ──────────────────────────────────────────────────────────

def page_config(title="Demo Gestión"):
    st.set_page_config(
        page_title=title,
        page_icon="🛒",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def apply_styles():
    st.markdown("""
    <style>
        /* Sidebar */
        [data-testid="stSidebar"] {
            background: #1D3557;
        }
        [data-testid="stSidebar"] * {
            color: rgba(255,255,255,0.85) !important;
        }
        [data-testid="stSidebar"] .stRadio label {
            font-size: 15px;
        }
        /* Botón primario */
        .stButton > button[kind="primary"] {
            background: #F05A28;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            padding: 0.5rem 1.5rem;
        }
        .stButton > button[kind="primary"]:hover {
            background: #C4421A;
        }
        /* Cards */
        [data-testid="stMetricValue"] {
            font-size: 1.6rem !important;
            font-weight: 700 !important;
        }
        /* Tabla */
        [data-testid="stDataFrame"] { border-radius: 8px; }
        /* Headers */
        h1 { color: #1D3557 !important; }
        h2, h3 { color: #2B4E7A !important; }
        /* Divider */
        hr { border-color: #E0D9D0; }
    </style>
    """, unsafe_allow_html=True)
