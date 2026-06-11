# 🛒 Sistema de Gestión Comercial — Demo

Sistema de gestión para comercios de barrio (almacenes, kioscos, panaderías, verdulerías) desarrollado en **Python + Streamlit** con base de datos **PostgreSQL**.

---

## 📦 Módulos

| Módulo | Descripción |
|--------|-------------|
| 🛒 **Punto de Venta** | Grilla de productos, carrito, cobro con múltiples medios de pago |
| 📦 **Stock** | Inventario completo, ajustes de entrada/salida, alertas de stock bajo |
| 💰 **Caja** | Resumen del día, cierre de caja por período, historial |
| 📊 **Reportes** | Ventas por día, ranking de productos, análisis por categoría |
| ⚙️ **Administración** | Gestión de usuarios y roles (solo admin) |

---

## 🚀 Deploy en Streamlit Community Cloud

### 1. Cloná el repositorio

```bash
git clone https://github.com/TU_USUARIO/demo-gestion.git
cd demo-gestion
```

### 2. Creá la base de datos en Neon.tech

1. Entrá a [neon.tech](https://neon.tech) y creá una cuenta gratuita
2. Creá un nuevo proyecto
3. Copiá la **Connection string** (formato: `postgresql://user:pass@host/dbname?sslmode=require`)

### 3. Subí a GitHub

```bash
git add .
git commit -m "Initial commit"
git push origin main
```

### 4. Deploy en Streamlit Cloud

1. Entrá a [share.streamlit.io](https://share.streamlit.io)
2. Conectá tu repositorio de GitHub
3. En **Advanced settings → Secrets**, agregá:

```toml
DATABASE_URL = "postgresql://user:password@host/dbname?sslmode=require"
```

4. Hacé clic en **Deploy**

¡Listo! La app crea las tablas y carga los datos de demo automáticamente en el primer inicio.

---

## 🔑 Credenciales de demo

| Usuario | Contraseña | Rol |
|---------|------------|-----|
| `admin` | `admin123` | Administrador |
| `operador` | `op123` | Operador |

> ⚠️ **Importante:** Cambiá las contraseñas antes de usar en producción desde el módulo de Administración.

---

## 💻 Desarrollo local

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variable de entorno
cp .env.example .env
# Editar .env con tu DATABASE_URL

# Correr la app
streamlit run app.py
```

---

## 🗂️ Estructura del proyecto

```
demo-gestion/
├── app.py              # Entry point + login + navegación
├── db.py               # Base de datos: schema, queries, helpers
├── utils.py            # Formato, estilos, helpers de UI
├── requirements.txt    # Dependencias Python
├── .env.example        # Ejemplo de variables de entorno
├── pages/
│   ├── pos.py          # Punto de Venta
│   ├── stock.py        # Gestión de Stock
│   ├── caja.py         # Caja y cierres
│   ├── reportes.py     # Reportes y gráficos
│   └── admin.py        # Administración (solo admin)
└── README.md
```

---

## ⚙️ Personalización para cada cliente

Para adaptar la demo a un cliente específico:

1. **Nombre del comercio**: cambiar `"Sistema de Gestión"` en `app.py` y `utils.py`
2. **Productos iniciales**: editar la función `_seed_demo()` en `db.py`
3. **Categorías**: modificar el seed o agregar desde el módulo Administración
4. **Logo**: agregar `st.image("assets/logo.png")` en el sidebar de `app.py`

---

## 📄 Licencia

Demo comercial — Desarrollado para presentación a clientes. Todos los derechos reservados.
