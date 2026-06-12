"""
pdf_exports.py — Exportacion a PDF para el Sistema de Gestion Comercial
Genera PDFs en memoria (BytesIO) listos para st.download_button()
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)

AZUL       = colors.HexColor("#1D3557")
AZUL_MED   = colors.HexColor("#2B4E7A")
NARANJA    = colors.HexColor("#F05A28")
VERDE      = colors.HexColor("#1B7A4A")
ROJO       = colors.HexColor("#DC2626")
GRIS_CLARO = colors.HexColor("#F7F3EE")
GRIS_MED   = colors.HexColor("#6B7280")
LINEA      = colors.HexColor("#E0D9D0")
BLANCO     = colors.white

W, H = A4

def _fmt(valor) -> str:
    try:
        return "$ {:,.0f}".format(float(valor)).replace(",", ".")
    except Exception:
        return "$ 0"

def _fecha(dt=None) -> str:
    dt = dt or datetime.now()
    return dt.strftime("%d/%m/%Y %H:%M")

def _solo_fecha(dt) -> str:
    if hasattr(dt, "strftime"):
        return dt.strftime("%d/%m/%Y")
    return str(dt)

def _hora(dt) -> str:
    if hasattr(dt, "strftime"):
        return dt.strftime("%H:%M")
    return str(dt)

_h2 = ParagraphStyle("h2",
    fontName="Helvetica-Bold", fontSize=11, textColor=AZUL,
    spaceBefore=10, spaceAfter=5, leading=14)

_body = ParagraphStyle("body",
    fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#1A1C22"),
    leading=13, spaceAfter=4)

_small = ParagraphStyle("small",
    fontName="Helvetica", fontSize=8, textColor=GRIS_MED, leading=11)


def _make_page_handler(titulo: str, subtitulo: str = ""):
    def handler(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(AZUL)
        canvas.rect(0, H - 1.6*cm, W, 1.6*cm, fill=1, stroke=0)
        canvas.setFillColor(NARANJA)
        canvas.rect(0, H - 0.25*cm, W, 0.25*cm, fill=1, stroke=0)
        canvas.setFillColor(BLANCO)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(1.5*cm, H - 1.0*cm, titulo)
        if subtitulo:
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#C8D9E8"))
            canvas.drawString(1.5*cm, H - 1.35*cm, subtitulo)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#8FB3CC"))
        canvas.drawRightString(W - 1.5*cm, H - 1.0*cm, "Generado: " + _fecha())
        canvas.drawRightString(W - 1.5*cm, H - 1.35*cm, "Pagina " + str(doc.page))
        canvas.setStrokeColor(LINEA)
        canvas.setLineWidth(0.5)
        canvas.line(1.5*cm, 1.2*cm, W - 1.5*cm, 1.2*cm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(GRIS_MED)
        canvas.drawString(1.5*cm, 0.75*cm, "Sistema de Gestion Comercial  |  Soporte: WhatsApp 299 689-4360  |  Neuquen Capital")
        canvas.drawRightString(W - 1.5*cm, 0.75*cm, "Documento generado automaticamente")
        canvas.restoreState()
    return handler


def _tabla(data, col_widths, header_bg=AZUL, align_cols=None):
    style = [
        ("BACKGROUND",    (0,0),  (-1,0),  header_bg),
        ("TEXTCOLOR",     (0,0),  (-1,0),  BLANCO),
        ("FONTNAME",      (0,0),  (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),  (-1,0),  8.5),
        ("TOPPADDING",    (0,0),  (-1,0),  7),
        ("BOTTOMPADDING", (0,0),  (-1,0),  7),
        ("LEFTPADDING",   (0,0),  (-1,-1), 7),
        ("RIGHTPADDING",  (0,0),  (-1,-1), 7),
        ("FONTNAME",      (0,1),  (-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,1),  (-1,-1), 8.5),
        ("TOPPADDING",    (0,1),  (-1,-1), 5),
        ("BOTTOMPADDING", (0,1),  (-1,-1), 5),
        ("VALIGN",        (0,0),  (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0,1),  (-1,-1), [BLANCO, GRIS_CLARO]),
        ("GRID",          (0,0),  (-1,-1), 0.3, LINEA),
        ("LINEBELOW",     (0,0),  (-1,0),  1.5, NARANJA),
    ]
    if align_cols:
        for col, aln in align_cols.items():
            style.append(("ALIGN", (col,0), (col,-1), aln))
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle(style))
    return t


def _kpi_row(items: list) -> Table:
    n = len(items)
    ancho = (W - 3.0*cm) / n
    celdas = []
    for label, valor, bg in items:
        celda = Table([
            [Paragraph(label, ParagraphStyle("kl", fontName="Helvetica", fontSize=7.5,
                       textColor=colors.HexColor("#C8D9E8"), alignment=TA_CENTER))],
            [Paragraph(valor, ParagraphStyle("kv", fontName="Helvetica-Bold", fontSize=13,
                       textColor=BLANCO, alignment=TA_CENTER, leading=16))],
        ], colWidths=[ancho - 0.4*cm])
        celda.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), bg),
            ("TOPPADDING",    (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
            ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ]))
        celdas.append(celda)
    row = Table([celdas], colWidths=[ancho]*n)
    row.setStyle(TableStyle([
        ("LEFTPADDING",  (0,0), (-1,-1), 3),
        ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING",   (0,0), (-1,-1), 0),
        ("BOTTOMPADDING",(0,0), (-1,-1), 0),
    ]))
    return row


# ══════════════════════════════════════════════════════════════════════════════
def exportar_stock(productos: list, nombre_comercio: str = "Mi Comercio") -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=2.2*cm, bottomMargin=2.0*cm)
    handler = _make_page_handler("Reporte de Stock Actual",
        nombre_comercio + "  |  " + _fecha())
    story = []

    activos  = [p for p in productos if p.get("activo", True)]
    bajos    = [p for p in activos if float(p.get("stock_actual",0)) <= float(p.get("stock_minimo",0))]
    agotados = [p for p in activos if float(p.get("stock_actual",0)) <= 0]
    valor_inv= sum(float(p.get("stock_actual",0))*float(p.get("precio_costo",0)) for p in activos)

    story.append(_kpi_row([
        ("Total productos",  str(len(activos)),   AZUL),
        ("Stock bajo",       str(len(bajos)),      NARANJA if bajos else VERDE),
        ("Agotados",         str(len(agotados)),   ROJO if agotados else VERDE),
        ("Valor inventario", _fmt(valor_inv),      AZUL_MED),
    ]))
    story.append(Spacer(1, 14))

    if bajos:
        story.append(Paragraph("Productos con stock bajo o agotado", _h2))
        story.append(HRFlowable(width="100%", thickness=1, color=NARANJA, spaceAfter=6))
        data_b = [["Producto","Categoria","Stock actual","Minimo","Diferencia","Unidad"]]
        for p in sorted(bajos, key=lambda x: float(x.get("stock_actual",0))):
            diff = float(p.get("stock_actual",0)) - float(p.get("stock_minimo",0))
            data_b.append([
                p.get("nombre",""), p.get("categoria","") or "—",
                "{:g}".format(float(p.get("stock_actual",0))),
                "{:g}".format(float(p.get("stock_minimo",0))),
                "{:+g}".format(diff), p.get("unidad",""),
            ])
        t_b = _tabla(data_b, [5.5*cm,3*cm,2.2*cm,2.2*cm,2.2*cm,2.2*cm],
                     header_bg=NARANJA,
                     align_cols={2:"CENTER",3:"CENTER",4:"CENTER"})
        for i, p in enumerate(bajos, 1):
            if float(p.get("stock_actual",0)) <= 0:
                t_b.setStyle(TableStyle([("TEXTCOLOR",(0,i),(-1,i),ROJO),
                                         ("FONTNAME",(0,i),(-1,i),"Helvetica-Bold")]))
        story.append(t_b)
        story.append(Spacer(1, 14))

    story.append(Paragraph("Inventario completo", _h2))
    story.append(HRFlowable(width="100%", thickness=1, color=AZUL, spaceAfter=6))

    cats = {}
    for p in activos:
        cat = p.get("categoria") or "Sin categoria"
        cats.setdefault(cat, []).append(p)

    for cat, prods in sorted(cats.items()):
        story.append(Paragraph(cat, ParagraphStyle("cat_lbl",
            fontName="Helvetica-Bold", fontSize=9, textColor=AZUL_MED,
            spaceBefore=8, spaceAfter=4, backColor=GRIS_CLARO,
            leftIndent=4, borderPad=4)))

        data = [["Producto","P. Venta","P. Costo","Margen","Stock","Min.","Unidad","Estado"]]
        for p in sorted(prods, key=lambda x: x.get("nombre","")):
            try:
                v = float(p.get("precio_venta",0)); c2 = float(p.get("precio_costo",0))
                margen = "{:.0f}%".format((v-c2)/c2*100) if c2 > 0 else "—"
            except Exception:
                margen = "—"
            sa = float(p.get("stock_actual",0)); sm = float(p.get("stock_minimo",0))
            estado = "OK" if sa > sm else ("AGOTADO" if sa <= 0 else "BAJO")
            data.append([p.get("nombre",""), _fmt(p.get("precio_venta",0)),
                         _fmt(p.get("precio_costo",0)), margen,
                         "{:g}".format(sa), "{:g}".format(sm),
                         p.get("unidad",""), estado])

        t = _tabla(data, [4.8*cm,2.2*cm,2.2*cm,1.5*cm,1.5*cm,1.2*cm,1.5*cm,1.8*cm],
                   align_cols={1:"RIGHT",2:"RIGHT",3:"CENTER",
                               4:"CENTER",5:"CENTER",7:"CENTER"})
        for i, p in enumerate(prods, 1):
            sa = float(p.get("stock_actual",0)); sm = float(p.get("stock_minimo",0))
            if sa <= 0:
                t.setStyle(TableStyle([("TEXTCOLOR",(7,i),(7,i),ROJO),
                                       ("FONTNAME",(7,i),(7,i),"Helvetica-Bold")]))
            elif sa <= sm:
                t.setStyle(TableStyle([("TEXTCOLOR",(7,i),(7,i),NARANJA),
                                       ("FONTNAME",(7,i),(7,i),"Helvetica-Bold")]))
            else:
                t.setStyle(TableStyle([("TEXTCOLOR",(7,i),(7,i),VERDE)]))
        story.append(t)
        story.append(Spacer(1, 4))

    doc.build(story, onFirstPage=handler, onLaterPages=handler)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
def exportar_cierres(cierres: list, nombre_comercio: str = "Mi Comercio") -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=2.2*cm, bottomMargin=2.0*cm)
    handler = _make_page_handler("Historial de Cierres de Caja",
        nombre_comercio + "  |  " + _fecha())
    story = []

    if not cierres:
        story.append(Paragraph("No hay cierres registrados.", _body))
        doc.build(story, onFirstPage=handler, onLaterPages=handler)
        return buf.getvalue()

    total_global    = sum(float(c.get("total_ventas",0))    for c in cierres)
    ventas_global   = sum(int(c.get("cantidad_ventas",0))   for c in cierres)
    efectivo_global = sum(float(c.get("total_efectivo",0))  for c in cierres)
    digital_global  = sum(float(c.get("total_debito",0)) +
                         float(c.get("total_credito",0)) +
                         float(c.get("total_transferencia",0)) for c in cierres)

    story.append(_kpi_row([
        ("Cierres incluidos", str(len(cierres)),     AZUL),
        ("Total facturado",   _fmt(total_global),    VERDE),
        ("Total ventas",      str(ventas_global),    AZUL_MED),
        ("Total efectivo",    _fmt(efectivo_global), AZUL),
    ]))
    story.append(Spacer(1, 14))

    story.append(Paragraph("Resumen de cierres", _h2))
    story.append(HRFlowable(width="100%", thickness=1, color=AZUL, spaceAfter=6))

    data_r = [["Apertura","Cierre","Cajero","Ventas","Efectivo","Digital","Total"]]
    for c in cierres:
        digital = (float(c.get("total_debito",0)) + float(c.get("total_credito",0)) +
                   float(c.get("total_transferencia",0)))
        data_r.append([
            _solo_fecha(c.get("fecha_apertura","")) + " " + _hora(c.get("fecha_apertura","")),
            _solo_fecha(c.get("fecha_cierre",""))   + " " + _hora(c.get("fecha_cierre","")),
            c.get("cajero",""), str(int(c.get("cantidad_ventas",0))),
            _fmt(c.get("total_efectivo",0)), _fmt(digital), _fmt(c.get("total_ventas",0)),
        ])
    data_r.append(["TOTAL","","", str(ventas_global),
                   _fmt(efectivo_global), _fmt(digital_global), _fmt(total_global)])

    t_r = _tabla(data_r, [3*cm,3*cm,2.5*cm,1.6*cm,2.5*cm,2.3*cm,2.4*cm],
                 align_cols={3:"CENTER",4:"RIGHT",5:"RIGHT",6:"RIGHT"})
    n = len(data_r)
    t_r.setStyle(TableStyle([
        ("BACKGROUND",(0,n-1),(-1,n-1),AZUL),
        ("TEXTCOLOR", (0,n-1),(-1,n-1),BLANCO),
        ("FONTNAME",  (0,n-1),(-1,n-1),"Helvetica-Bold"),
        ("LINEABOVE", (0,n-1),(-1,n-1),1.5,NARANJA),
    ]))
    story.append(t_r)
    story.append(Spacer(1, 16))

    story.append(Paragraph("Detalle por cierre", _h2))
    story.append(HRFlowable(width="100%", thickness=1, color=AZUL, spaceAfter=8))

    for i, c in enumerate(cierres):
        digital = (float(c.get("total_debito",0)) + float(c.get("total_credito",0)) +
                   float(c.get("total_transferencia",0)))

        header_t = Table([[
            Paragraph(
                "Cierre #{} — {} {} a {} {}".format(
                    i+1,
                    _solo_fecha(c.get("fecha_apertura","")), _hora(c.get("fecha_apertura","")),
                    _solo_fecha(c.get("fecha_cierre","")),   _hora(c.get("fecha_cierre",""))),
                ParagraphStyle("ct", fontName="Helvetica-Bold", fontSize=9, textColor=BLANCO)),
            Paragraph("Cajero: " + c.get("cajero",""),
                ParagraphStyle("cs", fontName="Helvetica", fontSize=8,
                               textColor=colors.HexColor("#C8D9E8"), alignment=TA_RIGHT)),
        ]], colWidths=[12*cm, 5.3*cm])
        header_t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),AZUL_MED),
            ("TOPPADDING",(0,0),(-1,-1),7), ("BOTTOMPADDING",(0,0),(-1,-1),7),
            ("LEFTPADDING",(0,0),(-1,-1),8), ("RIGHTPADDING",(0,0),(-1,-1),8),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ]))

        det = Table([
            ["Monto apertura:", _fmt(c.get("monto_apertura",0)), "Ventas:", str(int(c.get("cantidad_ventas",0)))],
            ["Efectivo:",       _fmt(c.get("total_efectivo",0)), "Debito:", _fmt(c.get("total_debito",0))],
            ["Credito:",        _fmt(c.get("total_credito",0)),  "Transferencia:", _fmt(c.get("total_transferencia",0))],
            ["Total digital:",  _fmt(digital),                   "TOTAL CIERRE:", _fmt(c.get("total_ventas",0))],
        ], colWidths=[3.2*cm, 3.8*cm, 3.2*cm, 3.8*cm])
        det.setStyle(TableStyle([
            ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
            ("FONTNAME",(2,0),(2,-1),"Helvetica-Bold"),
            ("TEXTCOLOR",(0,0),(0,-1),GRIS_MED),
            ("TEXTCOLOR",(2,0),(2,-1),GRIS_MED),
            ("FONTSIZE",(0,0),(-1,-1),8.5),
            ("TOPPADDING",(0,0),(-1,-1),5), ("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),8),
            ("BACKGROUND",(0,0),(-1,-1),GRIS_CLARO),
            ("BACKGROUND",(0,3),(-1,3),colors.HexColor("#E8F0FA")),
            ("FONTNAME",(1,3),(1,3),"Helvetica-Bold"),
            ("FONTNAME",(3,3),(3,3),"Helvetica-Bold"),
            ("TEXTCOLOR",(3,3),(3,3),VERDE),
            ("FONTSIZE",(3,3),(3,3),10),
            ("GRID",(0,0),(-1,-1),0.3,LINEA),
        ]))

        obs = c.get("observaciones") or ""
        extras = [Paragraph("Obs: " + obs, _small)] if obs else []
        story.append(KeepTogether([header_t, det] + extras + [Spacer(1, 10)]))

    doc.build(story, onFirstPage=handler, onLaterPages=handler)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
def exportar_ventas_dia(ventas: list, resumen: dict,
                        fecha=None, nombre_comercio: str = "Mi Comercio") -> bytes:
    buf = io.BytesIO()
    fecha_str = fecha.strftime("%d/%m/%Y") if fecha else datetime.now().strftime("%d/%m/%Y")
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=2.2*cm, bottomMargin=2.0*cm)
    handler = _make_page_handler("Ventas del dia  " + fecha_str,
        nombre_comercio + "  |  Generado: " + _fecha())
    story = []

    cant  = int(resumen.get("cantidad_ventas", 0))
    total = float(resumen.get("total_general", 0))
    prom  = total / cant if cant else 0

    story.append(_kpi_row([
        ("Total del dia",   _fmt(total),  VERDE),
        ("Ventas",          str(cant),    AZUL),
        ("Ticket promedio", _fmt(prom),   AZUL_MED),
        ("Efectivo",        _fmt(resumen.get("efectivo", 0)), AZUL),
    ]))
    story.append(Spacer(1, 14))

    story.append(Paragraph("Desglose por medio de pago", _h2))
    story.append(HRFlowable(width="100%", thickness=1, color=AZUL, spaceAfter=6))

    MEDIOS_LABEL = {"efectivo":"Efectivo","debito":"Debito",
                    "credito":"Credito","transferencia":"Transferencia"}
    medios = [("Efectivo",resumen.get("efectivo",0)),
              ("Debito",  resumen.get("debito",0)),
              ("Credito", resumen.get("credito",0)),
              ("Transferencia", resumen.get("transferencia",0))]
    data_m = [["Medio de pago","Total","% del dia"]]
    for label, valor in medios:
        pct = float(valor)/total*100 if total else 0
        data_m.append([label, _fmt(valor), "{:.1f}%".format(pct)])
    data_m.append(["TOTAL", _fmt(total), "100%"])
    t_m = _tabla(data_m, [6*cm,4*cm,3*cm], align_cols={1:"RIGHT",2:"CENTER"})
    n = len(data_m)
    t_m.setStyle(TableStyle([
        ("BACKGROUND",(0,n-1),(-1,n-1),AZUL),
        ("TEXTCOLOR",(0,n-1),(-1,n-1),BLANCO),
        ("FONTNAME",(0,n-1),(-1,n-1),"Helvetica-Bold"),
    ]))
    story.append(t_m)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Listado de ventas ({})".format(len(ventas)), _h2))
    story.append(HRFlowable(width="100%", thickness=1, color=AZUL, spaceAfter=6))

    if not ventas:
        story.append(Paragraph("No hay ventas registradas.", _body))
    else:
        data_v = [["N Venta","Hora","Cajero","Medio de pago","Total"]]
        for v in ventas:
            hora = v["fecha"].strftime("%H:%M") if hasattr(v.get("fecha"), "strftime") else ""
            data_v.append([
                "#" + str(v.get("id","")), hora, v.get("cajero",""),
                MEDIOS_LABEL.get(v.get("medio_pago",""), v.get("medio_pago","")),
                _fmt(v.get("total",0)),
            ])
        t_v = _tabla(data_v, [2*cm,2*cm,4*cm,4*cm,3*cm],
                     align_cols={0:"CENTER",1:"CENTER",4:"RIGHT"})
        story.append(t_v)

    doc.build(story, onFirstPage=handler, onLaterPages=handler)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
def exportar_mas_vendidos(productos: list, ventas_dia: list,
                          fecha_desde=None, fecha_hasta=None,
                          nombre_comercio: str = "Mi Comercio") -> bytes:
    buf = io.BytesIO()
    desde_str = fecha_desde.strftime("%d/%m/%Y") if fecha_desde else "—"
    hasta_str = fecha_hasta.strftime("%d/%m/%Y") if fecha_hasta else "—"
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=2.2*cm, bottomMargin=2.0*cm)
    handler = _make_page_handler("Reporte de Ventas y Productos mas Vendidos",
        nombre_comercio + "  |  Periodo: " + desde_str + " al " + hasta_str)
    story = []

    total_fact  = sum(float(p.get("total_facturado",0))   for p in productos)
    total_unids = sum(float(p.get("unidades_vendidas",0)) for p in productos)
    dias_act    = len(ventas_dia)
    prom_dia    = total_fact / dias_act if dias_act else 0

    story.append(_kpi_row([
        ("Facturacion total", _fmt(total_fact),    VERDE),
        ("Unidades vendidas", "{:g}".format(total_unids), AZUL),
        ("Dias con ventas",   str(dias_act),        AZUL_MED),
        ("Promedio diario",   _fmt(prom_dia),       AZUL),
    ]))
    story.append(Spacer(1, 14))

    story.append(Paragraph("Ranking de productos por facturacion", _h2))
    story.append(HRFlowable(width="100%", thickness=1, color=AZUL, spaceAfter=6))

    if not productos:
        story.append(Paragraph("No hay datos en el periodo seleccionado.", _body))
    else:
        data_p = [["#","Producto","Categoria","Unidades","Total facturado","% del total"]]
        for i, p in enumerate(productos, 1):
            fact = float(p.get("total_facturado",0))
            pct  = fact/total_fact*100 if total_fact else 0
            data_p.append([str(i), p.get("nombre",""), p.get("categoria","") or "—",
                           "{:g}".format(float(p.get("unidades_vendidas",0))),
                           _fmt(fact), "{:.1f}%".format(pct)])
        data_p.append(["","TOTAL","","{:g}".format(total_unids),_fmt(total_fact),"100%"])

        t_p = _tabla(data_p, [0.8*cm,5.5*cm,3*cm,2.5*cm,3*cm,2*cm],
                     align_cols={0:"CENTER",3:"CENTER",4:"RIGHT",5:"CENTER"})
        n = len(data_p)
        t_p.setStyle(TableStyle([
            ("BACKGROUND",(0,n-1),(-1,n-1),AZUL),
            ("TEXTCOLOR",(0,n-1),(-1,n-1),BLANCO),
            ("FONTNAME",(0,n-1),(-1,n-1),"Helvetica-Bold"),
        ]))
        for i in range(1, min(4, n-1)):
            t_p.setStyle(TableStyle([
                ("FONTNAME",(1,i),(1,i),"Helvetica-Bold"),
                ("TEXTCOLOR",(0,i),(0,i),NARANJA),
                ("FONTNAME",(0,i),(0,i),"Helvetica-Bold"),
            ]))
        story.append(t_p)
        story.append(Spacer(1, 14))

    if ventas_dia:
        story.append(Paragraph("Ventas por dia en el periodo", _h2))
        story.append(HRFlowable(width="100%", thickness=1, color=AZUL, spaceAfter=6))
        data_vd = [["Fecha","Cantidad de ventas","Total del dia","Ticket promedio"]]
        for d in ventas_dia:
            cant2 = int(d.get("cantidad",0)); tot2 = float(d.get("total",0))
            prom2 = tot2/cant2 if cant2 else 0
            dia = d.get("dia")
            dia_s = dia.strftime("%d/%m/%Y") if hasattr(dia,"strftime") else str(dia)
            data_vd.append([dia_s, str(cant2), _fmt(tot2), _fmt(prom2)])
        tc = sum(int(d.get("cantidad",0)) for d in ventas_dia)
        tt = sum(float(d.get("total",0)) for d in ventas_dia)
        data_vd.append(["TOTAL", str(tc), _fmt(tt), _fmt(tt/tc if tc else 0)])
        t_vd = _tabla(data_vd, [3.5*cm,4*cm,4*cm,4*cm],
                      align_cols={1:"CENTER",2:"RIGHT",3:"RIGHT"})
        n = len(data_vd)
        t_vd.setStyle(TableStyle([
            ("BACKGROUND",(0,n-1),(-1,n-1),AZUL),
            ("TEXTCOLOR",(0,n-1),(-1,n-1),BLANCO),
            ("FONTNAME",(0,n-1),(-1,n-1),"Helvetica-Bold"),
        ]))
        story.append(t_vd)

    doc.build(story, onFirstPage=handler, onLaterPages=handler)
    return buf.getvalue()
