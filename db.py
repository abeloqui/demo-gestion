"""
db.py — Conexión y esquema PostgreSQL para Demo Gestión Comercial
"""

import os
import psycopg2
import psycopg2.extras
import bcrypt
from dotenv import load_dotenv

load_dotenv()


def get_conn():
    """Retorna una conexión a la base de datos."""
    return psycopg2.connect(os.environ["DATABASE_URL"])


def init_db():
    """Crea todas las tablas si no existen e inserta datos de demo."""
    conn = get_conn()
    cur = conn.cursor()

    # ── Usuarios ──────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id          SERIAL PRIMARY KEY,
            nombre      TEXT NOT NULL,
            usuario     TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            rol         TEXT NOT NULL CHECK (rol IN ('admin','operador')),
            activo      BOOLEAN DEFAULT TRUE,
            creado_en   TIMESTAMP DEFAULT NOW()
        )
    """)

    # ── Categorías ────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id      SERIAL PRIMARY KEY,
            nombre  TEXT UNIQUE NOT NULL
        )
    """)

    # ── Productos ─────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id              SERIAL PRIMARY KEY,
            nombre          TEXT NOT NULL,
            categoria_id    INTEGER REFERENCES categorias(id),
            precio_venta    NUMERIC(10,2) NOT NULL DEFAULT 0,
            precio_costo    NUMERIC(10,2) NOT NULL DEFAULT 0,
            stock_actual    NUMERIC(10,2) NOT NULL DEFAULT 0,
            stock_minimo    NUMERIC(10,2) NOT NULL DEFAULT 0,
            unidad          TEXT NOT NULL DEFAULT 'unidad',
            activo          BOOLEAN DEFAULT TRUE,
            creado_en       TIMESTAMP DEFAULT NOW()
        )
    """)

    # ── Ventas (cabecera) ─────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id              SERIAL PRIMARY KEY,
            usuario_id      INTEGER REFERENCES usuarios(id),
            total           NUMERIC(10,2) NOT NULL DEFAULT 0,
            medio_pago      TEXT NOT NULL DEFAULT 'efectivo',
            fecha           TIMESTAMP DEFAULT NOW()
        )
    """)

    # ── Detalle de ventas ─────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS venta_items (
            id              SERIAL PRIMARY KEY,
            venta_id        INTEGER REFERENCES ventas(id) ON DELETE CASCADE,
            producto_id     INTEGER REFERENCES productos(id),
            cantidad        NUMERIC(10,2) NOT NULL,
            precio_unit     NUMERIC(10,2) NOT NULL,
            subtotal        NUMERIC(10,2) NOT NULL
        )
    """)

    # ── Movimientos de stock ──────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_movimientos (
            id              SERIAL PRIMARY KEY,
            producto_id     INTEGER REFERENCES productos(id),
            usuario_id      INTEGER REFERENCES usuarios(id),
            tipo            TEXT NOT NULL CHECK (tipo IN ('entrada','salida','ajuste')),
            cantidad        NUMERIC(10,2) NOT NULL,
            motivo          TEXT,
            fecha           TIMESTAMP DEFAULT NOW()
        )
    """)

    # ── Cierres de caja ───────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cierres_caja (
            id              SERIAL PRIMARY KEY,
            usuario_id      INTEGER REFERENCES usuarios(id),
            fecha_apertura  TIMESTAMP NOT NULL,
            fecha_cierre    TIMESTAMP DEFAULT NOW(),
            monto_apertura  NUMERIC(10,2) DEFAULT 0,
            total_efectivo  NUMERIC(10,2) DEFAULT 0,
            total_debito    NUMERIC(10,2) DEFAULT 0,
            total_credito   NUMERIC(10,2) DEFAULT 0,
            total_transferencia NUMERIC(10,2) DEFAULT 0,
            total_ventas    NUMERIC(10,2) DEFAULT 0,
            cantidad_ventas INTEGER DEFAULT 0,
            observaciones   TEXT
        )
    """)

    conn.commit()

    # ── Seed: admin por defecto ───────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM usuarios")
    if cur.fetchone()[0] == 0:
        _seed_demo(cur)
        conn.commit()

    cur.close()
    conn.close()


def _seed_demo(cur):
    """Inserta datos de ejemplo para la demo."""
    # Usuarios
    pw_admin = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
    pw_op    = bcrypt.hashpw("op123".encode(), bcrypt.gensalt()).decode()
    cur.execute("""
        INSERT INTO usuarios (nombre, usuario, password, rol) VALUES
        ('Administrador', 'admin', %s, 'admin'),
        ('Operador Demo',  'operador', %s, 'operador')
    """, (pw_admin, pw_op))

    # Categorías
    cur.execute("""
        INSERT INTO categorias (nombre) VALUES
        ('Almacén'), ('Bebidas'), ('Lácteos'), ('Limpieza'), ('Panificados')
        ON CONFLICT DO NOTHING
    """)

    # Productos de ejemplo
    cur.execute("""
        INSERT INTO productos
            (nombre, categoria_id, precio_venta, precio_costo, stock_actual, stock_minimo, unidad)
        VALUES
        ('Arroz 1kg',        1, 1200, 800, 30, 5,  'unidad'),
        ('Aceite 900ml',     1, 2100, 1500, 18, 4, 'unidad'),
        ('Harina 1kg',       1, 900,  600, 25, 5,  'unidad'),
        ('Azúcar 1kg',       1, 800,  550, 22, 5,  'unidad'),
        ('Fideos 500g',      1, 600,  400, 40, 8,  'unidad'),
        ('Coca-Cola 1.5L',   2, 1800, 1200, 24, 6, 'unidad'),
        ('Agua 500ml',       2, 500,  300, 36, 10, 'unidad'),
        ('Cerveza 1L',       2, 1500, 1000, 20, 4, 'unidad'),
        ('Jugo Cepita 1L',   2, 900,  600, 15, 4,  'unidad'),
        ('Leche 1L',         3, 1100, 750, 20, 6,  'unidad'),
        ('Yogur x4',         3, 1400, 950, 12, 3,  'unidad'),
        ('Queso en barra',   3, 5500, 4000, 5, 2,  'kg'),
        ('Detergente 500ml', 4, 1200, 800, 10, 3,  'unidad'),
        ('Lavandina 1L',     4, 700,  450, 8,  3,  'unidad'),
        ('Medialunas x6',    5, 1000, 600, 15, 4,  'unidad'),
        ('Pan Lactal',       5, 900,  600, 10, 3,  'unidad')
        ON CONFLICT DO NOTHING
    """)


# ── Helpers de usuario ────────────────────────────────────────────────────────

def login(usuario: str, password: str):
    """Retorna dict del usuario si credenciales válidas, sino None."""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT * FROM usuarios WHERE usuario=%s AND activo=TRUE", (usuario,)
    )
    row = cur.fetchone()
    cur.close(); conn.close()
    if row and bcrypt.checkpw(password.encode(), row["password"].encode()):
        return dict(row)
    return None


# ── Helpers de productos ──────────────────────────────────────────────────────

def get_productos(solo_activos=True):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    q = """
        SELECT p.*, c.nombre AS categoria
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        {}
        ORDER BY c.nombre, p.nombre
    """.format("WHERE p.activo=TRUE" if solo_activos else "")
    cur.execute(q)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in rows]


def get_producto(pid: int):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM productos WHERE id=%s", (pid,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return dict(row) if row else None


def upsert_producto(data: dict):
    conn = get_conn()
    cur = conn.cursor()
    if data.get("id"):
        cur.execute("""
            UPDATE productos SET nombre=%s, categoria_id=%s, precio_venta=%s,
            precio_costo=%s, stock_minimo=%s, unidad=%s, activo=%s
            WHERE id=%s
        """, (data["nombre"], data["categoria_id"], data["precio_venta"],
              data["precio_costo"], data["stock_minimo"], data["unidad"],
              data["activo"], data["id"]))
    else:
        cur.execute("""
            INSERT INTO productos
                (nombre, categoria_id, precio_venta, precio_costo, stock_actual, stock_minimo, unidad)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (data["nombre"], data["categoria_id"], data["precio_venta"],
              data["precio_costo"], data.get("stock_actual", 0),
              data["stock_minimo"], data["unidad"]))
    conn.commit(); cur.close(); conn.close()


def ajustar_stock(producto_id: int, cantidad: float, tipo: str,
                  motivo: str, usuario_id: int):
    """Ajusta el stock y registra el movimiento."""
    conn = get_conn()
    cur = conn.cursor()
    delta = cantidad if tipo == "entrada" else -cantidad
    cur.execute(
        "UPDATE productos SET stock_actual = stock_actual + %s WHERE id=%s",
        (delta, producto_id)
    )
    cur.execute("""
        INSERT INTO stock_movimientos (producto_id, usuario_id, tipo, cantidad, motivo)
        VALUES (%s,%s,%s,%s,%s)
    """, (producto_id, usuario_id, tipo, cantidad, motivo))
    conn.commit(); cur.close(); conn.close()


def get_categorias():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM categorias ORDER BY nombre")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in rows]


# ── Helpers de ventas ─────────────────────────────────────────────────────────

def registrar_venta(usuario_id: int, items: list, medio_pago: str) -> int:
    """
    items: [{"producto_id": x, "cantidad": y, "precio_unit": z}, ...]
    Retorna el id de la venta creada.
    """
    total = sum(i["cantidad"] * i["precio_unit"] for i in items)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ventas (usuario_id, total, medio_pago) VALUES (%s,%s,%s) RETURNING id",
        (usuario_id, total, medio_pago)
    )
    venta_id = cur.fetchone()[0]
    for item in items:
        subtotal = item["cantidad"] * item["precio_unit"]
        cur.execute("""
            INSERT INTO venta_items (venta_id, producto_id, cantidad, precio_unit, subtotal)
            VALUES (%s,%s,%s,%s,%s)
        """, (venta_id, item["producto_id"], item["cantidad"],
              item["precio_unit"], subtotal))
        cur.execute(
            "UPDATE productos SET stock_actual = stock_actual - %s WHERE id=%s",
            (item["cantidad"], item["producto_id"])
        )
        cur.execute("""
            INSERT INTO stock_movimientos (producto_id, usuario_id, tipo, cantidad, motivo)
            VALUES (%s,%s,'salida',%s,'Venta #'||%s)
        """, (item["producto_id"], usuario_id, item["cantidad"], venta_id))
    conn.commit(); cur.close(); conn.close()
    return venta_id


def get_ventas(fecha_desde=None, fecha_hasta=None, limit=200):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    q = """
        SELECT v.id, v.fecha, v.total, v.medio_pago, u.nombre AS cajero
        FROM ventas v
        JOIN usuarios u ON v.usuario_id = u.id
        WHERE 1=1
    """
    params = []
    if fecha_desde:
        q += " AND v.fecha >= %s"; params.append(fecha_desde)
    if fecha_hasta:
        q += " AND v.fecha <= %s"; params.append(fecha_hasta)
    q += " ORDER BY v.fecha DESC LIMIT %s"; params.append(limit)
    cur.execute(q, params)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in rows]


def get_venta_detalle(venta_id: int):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT vi.*, p.nombre AS producto
        FROM venta_items vi
        JOIN productos p ON vi.producto_id = p.id
        WHERE vi.venta_id=%s
    """, (venta_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in rows]


# ── Helpers de caja ───────────────────────────────────────────────────────────

def get_resumen_caja(fecha_desde, fecha_hasta):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT
            COUNT(*) AS cantidad_ventas,
            COALESCE(SUM(total),0) AS total_general,
            COALESCE(SUM(CASE WHEN medio_pago='efectivo'      THEN total ELSE 0 END),0) AS efectivo,
            COALESCE(SUM(CASE WHEN medio_pago='debito'        THEN total ELSE 0 END),0) AS debito,
            COALESCE(SUM(CASE WHEN medio_pago='credito'       THEN total ELSE 0 END),0) AS credito,
            COALESCE(SUM(CASE WHEN medio_pago='transferencia' THEN total ELSE 0 END),0) AS transferencia
        FROM ventas
        WHERE fecha >= %s AND fecha <= %s
    """, (fecha_desde, fecha_hasta))
    row = cur.fetchone()
    cur.close(); conn.close()
    return dict(row)


def cerrar_caja(usuario_id, fecha_apertura, fecha_cierre,
                monto_apertura, resumen, observaciones=""):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO cierres_caja
            (usuario_id, fecha_apertura, fecha_cierre, monto_apertura,
             total_efectivo, total_debito, total_credito, total_transferencia,
             total_ventas, cantidad_ventas, observaciones)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
    """, (usuario_id, fecha_apertura, fecha_cierre, monto_apertura,
          resumen["efectivo"], resumen["debito"], resumen["credito"],
          resumen["transferencia"], resumen["total_general"],
          resumen["cantidad_ventas"], observaciones))
    cierre_id = cur.fetchone()[0]
    conn.commit(); cur.close(); conn.close()
    return cierre_id


def get_cierres(limit=30):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT cc.*, u.nombre AS cajero
        FROM cierres_caja cc
        JOIN usuarios u ON cc.usuario_id = u.id
        ORDER BY cc.fecha_cierre DESC LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in rows]


# ── Helpers de reportes ───────────────────────────────────────────────────────

def get_reporte_productos_mas_vendidos(fecha_desde, fecha_hasta, limit=10):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT p.nombre, c.nombre AS categoria,
               SUM(vi.cantidad) AS unidades_vendidas,
               SUM(vi.subtotal) AS total_facturado
        FROM venta_items vi
        JOIN ventas v ON vi.venta_id = v.id
        JOIN productos p ON vi.producto_id = p.id
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE v.fecha >= %s AND v.fecha <= %s
        GROUP BY p.id, p.nombre, c.nombre
        ORDER BY total_facturado DESC
        LIMIT %s
    """, (fecha_desde, fecha_hasta, limit))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in rows]


def get_reporte_ventas_por_dia(fecha_desde, fecha_hasta):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT DATE(fecha) AS dia,
               COUNT(*) AS cantidad,
               SUM(total) AS total
        FROM ventas
        WHERE fecha >= %s AND fecha <= %s
        GROUP BY DATE(fecha)
        ORDER BY dia
    """, (fecha_desde, fecha_hasta))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in rows]


def get_productos_stock_bajo():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT p.nombre, c.nombre AS categoria,
               p.stock_actual, p.stock_minimo, p.unidad
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE p.activo=TRUE AND p.stock_actual <= p.stock_minimo
        ORDER BY (p.stock_actual - p.stock_minimo) ASC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in rows]


def get_usuarios():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, nombre, usuario, rol, activo, creado_en FROM usuarios ORDER BY nombre")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in rows]


def crear_usuario(nombre, usuario, password, rol):
    pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO usuarios (nombre, usuario, password, rol) VALUES (%s,%s,%s,%s)",
        (nombre, usuario, pw, rol)
    )
    conn.commit(); cur.close(); conn.close()


def toggle_usuario(uid: int, activo: bool):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET activo=%s WHERE id=%s", (activo, uid))
    conn.commit(); cur.close(); conn.close()
