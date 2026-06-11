"""
pages/admin.py — Administración (solo rol admin)
"""

import streamlit as st
import pandas as pd
from db import get_usuarios, crear_usuario, toggle_usuario, get_categorias
from utils import require_admin, is_admin
import psycopg2
from db import get_conn


def render():
    require_admin()
    st.title("⚙️ Administración")

    tab1, tab2 = st.tabs(["👥 Usuarios", "🏷️ Categorías"])

    # ── TAB 1: Usuarios ───────────────────────────────────────────────────────
    with tab1:
        st.subheader("Gestión de usuarios")
        usuarios = get_usuarios()

        df = pd.DataFrame([{
            "ID":       u["id"],
            "Nombre":   u["nombre"],
            "Usuario":  u["usuario"],
            "Rol":      u["rol"].capitalize(),
            "Estado":   "✅ Activo" if u["activo"] else "❌ Inactivo",
            "Creado":   u["creado_en"].strftime("%d/%m/%Y") if u["creado_en"] else "",
        } for u in usuarios])
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Toggle activo
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            uid_toggle = st.number_input("ID de usuario", min_value=1, step=1,
                                         key="uid_toggle", placeholder="ID")
        with col2:
            nuevo_estado = st.selectbox("Estado", ["Activar", "Desactivar"])

        if st.button("Aplicar cambio de estado"):
            u_sel = next((u for u in usuarios if u["id"] == uid_toggle), None)
            if not u_sel:
                st.error("ID no encontrado.")
            elif u_sel["usuario"] == "admin":
                st.error("No se puede desactivar el admin principal.")
            else:
                toggle_usuario(uid_toggle, nuevo_estado == "Activar")
                st.success(f"Usuario {uid_toggle} actualizado.")
                st.rerun()

        # Crear usuario
        st.markdown("---")
        st.subheader("Crear nuevo usuario")
        with st.form("form_nuevo_usuario"):
            c1, c2 = st.columns(2)
            with c1:
                nuevo_nombre   = st.text_input("Nombre completo")
                nuevo_usuario  = st.text_input("Nombre de usuario (login)")
            with c2:
                nueva_pw       = st.text_input("Contraseña", type="password")
                nuevo_rol      = st.selectbox("Rol", ["operador", "admin"])
            submitted = st.form_submit_button("Crear usuario", type="primary")

        if submitted:
            if not nuevo_nombre or not nuevo_usuario or not nueva_pw:
                st.error("Completá todos los campos.")
            else:
                try:
                    crear_usuario(nuevo_nombre, nuevo_usuario, nueva_pw, nuevo_rol)
                    st.success(f"✅ Usuario '{nuevo_usuario}' creado correctamente.")
                    st.rerun()
                except Exception as e:
                    if "unique" in str(e).lower():
                        st.error("Ese nombre de usuario ya existe.")
                    else:
                        st.error(f"Error: {e}")

    # ── TAB 2: Categorías ─────────────────────────────────────────────────────
    with tab2:
        st.subheader("Gestión de categorías")
        categorias = get_categorias()

        if categorias:
            df_cat = pd.DataFrame([{"ID": c["id"], "Nombre": c["nombre"]} for c in categorias])
            st.dataframe(df_cat, use_container_width=True, hide_index=True)
        else:
            st.info("No hay categorías creadas.")

        st.markdown("---")
        st.subheader("Agregar categoría")
        with st.form("form_cat"):
            nueva_cat = st.text_input("Nombre de la categoría")
            if st.form_submit_button("Agregar", type="primary"):
                if not nueva_cat.strip():
                    st.error("El nombre no puede estar vacío.")
                else:
                    try:
                        conn = get_conn()
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO categorias (nombre) VALUES (%s)",
                            (nueva_cat.strip(),)
                        )
                        conn.commit(); cur.close(); conn.close()
                        st.success(f"Categoría '{nueva_cat}' creada.")
                        st.rerun()
                    except Exception as e:
                        if "unique" in str(e).lower():
                            st.error("Esa categoría ya existe.")
                        else:
                            st.error(f"Error: {e}")
