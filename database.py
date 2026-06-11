import psycopg2
import psycopg2.extras
import streamlit as st
from datetime import date, datetime
import os


# ─────────────────────────────────────────
#  CONEXIÓN
# ─────────────────────────────────────────

def get_connection():
    """Retorna una conexión a la base de datos Neon (PostgreSQL)."""
    db_url = st.secrets.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        st.error("❌ No se encontró DATABASE_URL en los secrets.")
        st.stop()
    conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn


def run_query(sql, params=None, fetch=True):
    """Ejecuta una query y opcionalmente retorna resultados."""
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                if fetch:
                    return cur.fetchall()
    except Exception as e:
        st.error(f"Error en base de datos: {e}")
        raise
    finally:
        conn.close()


def run_write(sql, params=None):
    """Ejecuta INSERT / UPDATE / DELETE y hace commit."""
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
            conn.commit()
    except Exception as e:
        st.error(f"Error al escribir en base de datos: {e}")
        raise
    finally:
        conn.close()


# ─────────────────────────────────────────
#  USUARIOS / AUTH
# ─────────────────────────────────────────

def get_user_by_username(username: str):
    rows = run_query(
        "SELECT * FROM usuarios WHERE username = %s AND activo = TRUE",
        (username,)
    )
    return rows[0] if rows else None


def get_all_users():
    return run_query("SELECT id, username, nombre, rol, activo FROM usuarios ORDER BY nombre")


def create_user(username, nombre, password_hash, rol):
    run_write(
        "INSERT INTO usuarios (username, nombre, password_hash, rol) VALUES (%s, %s, %s, %s)",
        (username, nombre, password_hash, rol)
    )


def toggle_user_active(user_id: int, activo: bool):
    run_write("UPDATE usuarios SET activo = %s WHERE id = %s", (activo, user_id))


# ─────────────────────────────────────────
#  PRODUCTOS
# ─────────────────────────────────────────

def get_all_products(solo_activos=True):
    if solo_activos:
        return run_query(
            "SELECT * FROM productos WHERE activo = TRUE ORDER BY categoria, nombre"
        )
    return run_query("SELECT * FROM productos ORDER BY categoria, nombre")


def get_product_by_id(product_id: int):
    rows = run_query("SELECT * FROM productos WHERE id = %s", (product_id,))
    return rows[0] if rows else None


def search_products(term: str):
    return run_query(
        "SELECT * FROM productos WHERE activo = TRUE AND (nombre ILIKE %s OR codigo ILIKE %s) ORDER BY nombre",
        (f"%{term}%", f"%{term}%")
    )


def get_categories():
    rows = run_query("SELECT DISTINCT categoria FROM productos WHERE activo = TRUE ORDER BY categoria")
    return [r["categoria"] for r in rows]


def create_product(codigo, nombre, categoria, precio_venta, precio_costo, stock_actual, stock_minimo, unidad):
    run_write(
        """INSERT INTO productos (codigo, nombre, categoria, precio_venta, precio_costo,
           stock_actual, stock_minimo, unidad)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (codigo, nombre, categoria, precio_venta, precio_costo, stock_actual, stock_minimo, unidad)
    )


def update_product(product_id, nombre, categoria, precio_venta, precio_costo, stock_minimo, unidad):
    run_write(
        """UPDATE productos SET nombre=%s, categoria=%s, precio_venta=%s,
           precio_costo=%s, stock_minimo=%s, unidad=%s
           WHERE id=%s""",
        (nombre, categoria, precio_venta, precio_costo, stock_minimo, unidad, product_id)
    )


def update_stock(product_id: int, cantidad_delta: float, motivo: str, usuario_id: int):
    """Modifica el stock y registra el movimiento."""
    run_write(
        "UPDATE productos SET stock_actual = stock_actual + %s WHERE id = %s",
        (cantidad_delta, product_id)
    )
    run_write(
        """INSERT INTO movimientos_stock (producto_id, cantidad, motivo, usuario_id)
           VALUES (%s, %s, %s, %s)""",
        (product_id, cantidad_delta, motivo, usuario_id)
    )


def get_low_stock_products():
    return run_query(
        "SELECT * FROM productos WHERE activo = TRUE AND stock_actual <= stock_minimo ORDER BY stock_actual"
    )


def get_stock_movements(product_id=None, limit=100):
    if product_id:
        return run_query(
            """SELECT ms.*, p.nombre as producto_nombre, u.nombre as usuario_nombre
               FROM movimientos_stock ms
               JOIN productos p ON ms.producto_id = p.id
               JOIN usuarios u ON ms.usuario_id = u.id
               WHERE ms.producto_id = %s
               ORDER BY ms.fecha DESC LIMIT %s""",
            (product_id, limit)
        )
    return run_query(
        """SELECT ms.*, p.nombre as producto_nombre, u.nombre as usuario_nombre
           FROM movimientos_stock ms
           JOIN productos p ON ms.producto_id = p.id
           JOIN usuarios u ON ms.usuario_id = u.id
           ORDER BY ms.fecha DESC LIMIT %s""",
        (limit,)
    )


# ─────────────────────────────────────────
#  VENTAS / POS
# ─────────────────────────────────────────

def create_venta(usuario_id: int, medio_pago: str, items: list, total: float, descuento: float = 0):
    """
    items: lista de dicts con {producto_id, cantidad, precio_unitario, subtotal}
    Retorna el id de la venta creada.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO ventas (usuario_id, medio_pago, total, descuento, fecha)
                       VALUES (%s, %s, %s, %s, NOW()) RETURNING id""",
                    (usuario_id, medio_pago, total, descuento)
                )
                venta_id = cur.fetchone()["id"]

                for item in items:
                    cur.execute(
                        """INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, precio_unitario, subtotal)
                           VALUES (%s, %s, %s, %s, %s)""",
                        (venta_id, item["producto_id"], item["cantidad"],
                         item["precio_unitario"], item["subtotal"])
                    )
                    cur.execute(
                        "UPDATE productos SET stock_actual = stock_actual - %s WHERE id = %s",
                        (item["cantidad"], item["producto_id"])
                    )
                    cur.execute(
                        """INSERT INTO movimientos_stock (producto_id, cantidad, motivo, usuario_id)
                           VALUES (%s, %s, %s, %s)""",
                        (item["producto_id"], -item["cantidad"], "Venta #" + str(venta_id), usuario_id)
                    )
            conn.commit()
        return venta_id
    except Exception as e:
        st.error(f"Error al registrar venta: {e}")
        raise
    finally:
        conn.close()


def get_ventas(fecha_desde=None, fecha_hasta=None, limit=200):
    base = """SELECT v.*, u.nombre as vendedor
              FROM ventas v JOIN usuarios u ON v.usuario_id = u.id"""
    if fecha_desde and fecha_hasta:
        return run_query(
            base + " WHERE v.fecha::date BETWEEN %s AND %s ORDER BY v.fecha DESC LIMIT %s",
            (fecha_desde, fecha_hasta, limit)
        )
    return run_query(base + " ORDER BY v.fecha DESC LIMIT %s", (limit,))


def get_detalle_venta(venta_id: int):
    return run_query(
        """SELECT dv.*, p.nombre as producto_nombre, p.codigo
           FROM detalle_ventas dv JOIN productos p ON dv.producto_id = p.id
           WHERE dv.venta_id = %s""",
        (venta_id,)
    )


def get_ventas_del_dia(fecha=None):
    if fecha is None:
        fecha = date.today()
    return run_query(
        """SELECT v.*, u.nombre as vendedor FROM ventas v
           JOIN usuarios u ON v.usuario_id = u.id
           WHERE v.fecha::date = %s ORDER BY v.fecha DESC""",
        (fecha,)
    )


# ─────────────────────────────────────────
#  CAJA
# ─────────────────────────────────────────

def abrir_caja(usuario_id: int, monto_inicial: float):
    """Abre una nueva caja. Retorna id."""
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO cajas (usuario_id, monto_inicial, estado, fecha_apertura)
                       VALUES (%s, %s, 'abierta', NOW()) RETURNING id""",
                    (usuario_id, monto_inicial)
                )
                caja_id = cur.fetchone()["id"]
            conn.commit()
        return caja_id
    finally:
        conn.close()


def cerrar_caja(caja_id: int, monto_final: float, observaciones: str = ""):
    run_write(
        """UPDATE cajas SET monto_final=%s, observaciones=%s,
           estado='cerrada', fecha_cierre=NOW()
           WHERE id=%s""",
        (monto_final, observaciones, caja_id)
    )


def get_caja_abierta():
    rows = run_query(
        """SELECT c.*, u.nombre as operador FROM cajas c
           JOIN usuarios u ON c.usuario_id = u.id
           WHERE c.estado = 'abierta' ORDER BY c.fecha_apertura DESC LIMIT 1"""
    )
    return rows[0] if rows else None


def get_cajas(limit=50):
    return run_query(
        """SELECT c.*, u.nombre as operador FROM cajas c
           JOIN usuarios u ON c.usuario_id = u.id
           ORDER BY c.fecha_apertura DESC LIMIT %s""",
        (limit,)
    )


def get_resumen_caja(caja_id: int):
    """Total de ventas y desglose por medio de pago durante la caja."""
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT fecha_apertura, fecha_cierre FROM cajas WHERE id = %s", (caja_id,))
                caja = cur.fetchone()
                if not caja:
                    return None

                fecha_desde = caja["fecha_apertura"]
                fecha_hasta = caja["fecha_cierre"] or datetime.now()

                cur.execute(
                    """SELECT medio_pago, COUNT(*) as cantidad, SUM(total) as total
                       FROM ventas WHERE fecha BETWEEN %s AND %s
                       GROUP BY medio_pago ORDER BY total DESC""",
                    (fecha_desde, fecha_hasta)
                )
                desglose = cur.fetchall()

                cur.execute(
                    "SELECT COUNT(*) as cantidad, SUM(total) as total FROM ventas WHERE fecha BETWEEN %s AND %s",
                    (fecha_desde, fecha_hasta)
                )
                totales = cur.fetchone()

                return {"desglose": desglose, "totales": totales, "caja": caja}
    finally:
        conn.close()


# ─────────────────────────────────────────
#  REPORTES
# ─────────────────────────────────────────

def get_ventas_por_dia(fecha_desde, fecha_hasta):
    return run_query(
        """SELECT DATE(fecha) as dia, COUNT(*) as cantidad, SUM(total) as total
           FROM ventas WHERE fecha::date BETWEEN %s AND %s
           GROUP BY DATE(fecha) ORDER BY dia""",
        (fecha_desde, fecha_hasta)
    )


def get_top_productos(fecha_desde, fecha_hasta, limit=10):
    return run_query(
        """SELECT p.nombre, p.categoria, SUM(dv.cantidad) as unidades_vendidas,
                  SUM(dv.subtotal) as total_vendido
           FROM detalle_ventas dv
           JOIN productos p ON dv.producto_id = p.id
           JOIN ventas v ON dv.venta_id = v.id
           WHERE v.fecha::date BETWEEN %s AND %s
           GROUP BY p.id, p.nombre, p.categoria
           ORDER BY total_vendido DESC LIMIT %s""",
        (fecha_desde, fecha_hasta, limit)
    )


def get_ventas_por_medio_pago(fecha_desde, fecha_hasta):
    return run_query(
        """SELECT medio_pago, COUNT(*) as cantidad, SUM(total) as total
           FROM ventas WHERE fecha::date BETWEEN %s AND %s
           GROUP BY medio_pago ORDER BY total DESC""",
        (fecha_desde, fecha_hasta)
    )


def get_margen_por_categoria(fecha_desde, fecha_hasta):
    return run_query(
        """SELECT p.categoria,
                  SUM(dv.subtotal) as ingresos,
                  SUM(dv.cantidad * p.precio_costo) as costo,
                  SUM(dv.subtotal) - SUM(dv.cantidad * p.precio_costo) as margen
           FROM detalle_ventas dv
           JOIN productos p ON dv.producto_id = p.id
           JOIN ventas v ON dv.venta_id = v.id
           WHERE v.fecha::date BETWEEN %s AND %s
           GROUP BY p.categoria ORDER BY margen DESC""",
        (fecha_desde, fecha_hasta)
    )


def get_kpis_periodo(fecha_desde, fecha_hasta):
    rows = run_query(
        """SELECT
             COUNT(*) as total_ventas,
             COALESCE(SUM(total), 0) as total_facturado,
             COALESCE(AVG(total), 0) as ticket_promedio,
             COALESCE(MAX(total), 0) as venta_maxima
           FROM ventas WHERE fecha::date BETWEEN %s AND %s""",
        (fecha_desde, fecha_hasta)
    )
    return rows[0] if rows else {}
