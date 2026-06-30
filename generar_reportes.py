import os
import io
import tempfile
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fpdf import FPDF

LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo.jpg")
EMPRESA = "GM Ferretera de Equipos S.A de C.V."


MESES_ES = {
    "January": "enero", "February": "febrero", "March": "marzo", "April": "abril",
    "May": "mayo", "June": "junio", "July": "julio", "August": "agosto",
    "September": "septiembre", "October": "octubre", "November": "noviembre", "December": "diciembre",
}


def _fecha_es(dt: datetime) -> str:
    return f"{dt.day} de {MESES_ES[dt.strftime('%B')]} de {dt.year}"


def _fmt(n: float) -> str:
    return f"${n:,.2f}"


def _safe(text: str) -> str:
    """Remove non-latin1 characters that Helvetica can't render."""
    return text.encode("latin-1", errors="replace").decode("latin-1")


# ─── PDF INTERNO ──────────────────────────────────────────

class PDFInterno(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, f"{EMPRESA} - Reporte Interno", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Confidencial - {EMPRESA} | Pag {self.page_no()}/{{nb}}", align="C")


def generar_pdf_interno(
    total_paneles: float,
    total_materiales: float,
    costo_instalacion: float,
    porcentaje_ganancia_instalacion: float,
    porcentaje_ganancia_paneles: float,
    paneles_con_ganancia: float,
    instalacion_con_ganancia: float,
    utilidad_paneles: float,
    utilidad_instalacion: float,
    utilidad_neta: float,
    precio_final: float,
    descripcion: str,
    items_paneles: list[dict],
) -> bytes:
    pdf = PDFInterno()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "DESGLOSE DE COSTOS INTERNOS", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    if descripcion:
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, f"Descripcion: {descripcion}")
        pdf.ln(3)

    # Tabla de items si hay
    if items_paneles:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(41, 65, 122)
        pdf.set_text_color(255)
        pdf.cell(0, 7, "  Items Detectados del Proveedor", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0)
        pdf.set_font("Helvetica", "", 8)
        for item in items_paneles:
            if item["descripcion"].lower() in ("total",):
                continue
            pdf.cell(130, 6, f"  {_safe(item['descripcion'][:70])}", border=1)
            pdf.cell(55, 6, _fmt(item["total"]), border=1, align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # Resumen financiero
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "RESUMEN FINANCIERO", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    filas = [
        ("Costo Paneles (proveedor)", total_paneles, False),
        (f"Ganancia paneles ({porcentaje_ganancia_paneles}%)", utilidad_paneles, False),
        ("Paneles al cliente", paneles_con_ganancia, False),
        ("", 0, False),
        ("Costo Materiales (proveedor)", total_materiales, False),
        ("", 0, False),
        ("Costo Instalacion (mano de obra base)", costo_instalacion, False),
        (f"Ganancia instalacion ({porcentaje_ganancia_instalacion}%)", utilidad_instalacion, False),
        ("Instalacion al cliente", instalacion_con_ganancia, False),
        ("", 0, False),
        ("PRECIO FINAL AL CLIENTE", precio_final, True),
        ("UTILIDAD NETA DE LA TIENDA", utilidad_neta, True),
    ]

    for label, val, bold in filas:
        if not label:
            pdf.ln(2)
            continue
        pdf.set_font("Helvetica", "B" if bold else "", 10)
        if bold and "UTILIDAD" in label:
            pdf.set_fill_color(39, 174, 96)
            pdf.set_text_color(255)
        elif bold:
            pdf.set_fill_color(41, 65, 122)
            pdf.set_text_color(255)
        else:
            pdf.set_fill_color(245, 245, 245)
            pdf.set_text_color(0)
        pdf.cell(120, 8, f"  {label}", border=1, fill=bold)
        pdf.cell(65, 8, _fmt(val), border=1, align="R", fill=bold, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0)

    return bytes(pdf.output())


# ─── PDF CLIENTE ──────────────────────────────────────────

class PDFCliente(FPDF):
    def header(self):
        if os.path.exists(LOGO_PATH):
            self.image(LOGO_PATH, x=10, y=8, w=40)
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, EMPRESA, align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 5, "Soluciones en Energia Solar", align="C", new_x="LMARGIN", new_y="NEXT")
        self.line(10, 28, 200, 28)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"{EMPRESA} | Pag {self.page_no()}/{{nb}}", align="C")


def _crear_grafica_roi(inversion: float, ahorro_anual: float, roi_anios: float) -> bytes:
    meses_max = int(roi_anios * 12) + 24
    meses = list(range(0, meses_max + 1))
    ahorro_mensual = ahorro_anual / 12
    ahorro_acum = [m * ahorro_mensual for m in meses]
    mes_roi = int(roi_anios * 12)

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.plot(meses, ahorro_acum, color="#2E86C1", linewidth=2, label="Ahorro acumulado")
    ax.axhline(y=inversion, color="#E74C3C", linestyle="--", linewidth=1.5, label=f"Inversion ({_fmt(inversion)})")

    if mes_roi <= max(meses):
        ax.axvline(x=mes_roi, color="#27AE60", linestyle=":", linewidth=1)
        ax.annotate(
            f"ROI: {mes_roi} meses\n({roi_anios:.1f} anios)",
            xy=(mes_roi, inversion), xytext=(mes_roi + 6, inversion * 0.65),
            arrowprops=dict(arrowstyle="->", color="#27AE60"),
            fontsize=9, color="#27AE60", fontweight="bold",
        )

    ax.fill_between(meses, ahorro_acum, alpha=0.1, color="#2E86C1")
    ax.set_xlabel("Meses")
    ax.set_ylabel("Pesos ($)")
    ax.set_title("Tiempo de Recuperacion de Inversion")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _crear_grafica_ahorro(ahorro_anual: float) -> bytes:
    categorias = ["Mensual", "Anual", "5 Anios", "10 Anios", "25 Anios"]
    valores = [ahorro_anual / 12, ahorro_anual, ahorro_anual * 5, ahorro_anual * 10, ahorro_anual * 25]

    fig, ax = plt.subplots(figsize=(7, 3))
    bars = ax.bar(categorias, valores, color=["#3498DB", "#2E86C1", "#1F618D", "#154360", "#0B2F4A"])
    for bar, val in zip(bars, valores):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(valores) * 0.02,
                _fmt(val), ha="center", va="bottom", fontsize=7, fontweight="bold")
    ax.set_ylabel("Pesos ($)")
    ax.set_title("Ahorro Estimado con Energia Solar")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generar_pdf_cliente(
    precio_final: float,
    paneles_con_ganancia: float,
    total_materiales: float,
    instalacion_con_ganancia: float,
    consumo_datos: dict,
    ahorro_anual: float,
    roi_anios: float,
    descripcion: str,
    nombre_cliente: str = "",
) -> bytes:
    pdf = PDFCliente()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # --- Página 1: Descripción y desglose ---
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Fecha: {_safe(_fecha_es(datetime.now()))}", align="R", new_x="LMARGIN", new_y="NEXT")
    if nombre_cliente:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, f"Cliente: {nombre_cliente}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(41, 65, 122)
    pdf.cell(0, 10, "COTIZACION DE PROYECTO SOLAR", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0)
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Descripcion del Proyecto", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    if descripcion:
        pdf.multi_cell(0, 5, descripcion)
    else:
        pdf.multi_cell(0, 5, "Instalacion de sistema de paneles solares para generacion de energia limpia y reduccion en el costo del servicio electrico.")
    pdf.ln(3)

    pdf.multi_cell(0, 5, (
        "En GM Ferretera de Equipos le ofrecemos soluciones integrales en energia solar. "
        "Nuestro servicio incluye el suministro de paneles de alta eficiencia, materiales de instalacion "
        "certificados y mano de obra especializada con garantia."
    ))
    pdf.ln(5)

    # Desglose (sin mostrar márgenes)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Desglose de Inversion", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(41, 65, 122)
    pdf.set_text_color(255)
    pdf.cell(95, 7, "  Concepto", border=1, fill=True)
    pdf.cell(90, 7, "Monto", border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0)

    pdf.set_font("Helvetica", "", 9)
    conceptos = [
        ("Sistema de paneles solares", paneles_con_ganancia),
        ("Materiales de instalacion", total_materiales),
        ("Instalacion profesional", instalacion_con_ganancia),
    ]
    for label, val in conceptos:
        pdf.cell(95, 7, f"  {label}", border=1)
        pdf.cell(90, 7, _fmt(val), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(41, 65, 122)
    pdf.set_text_color(255)
    pdf.cell(95, 8, "  INVERSION TOTAL", border=1, fill=True)
    pdf.cell(90, 8, _fmt(precio_final), border=1, align="R", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0)

    # --- Página 2: ROI ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(41, 65, 122)
    pdf.cell(0, 10, "ANALISIS DE AHORRO Y RETORNO DE INVERSION", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0)
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 10)
    consumo_kwh = consumo_datos.get("consumo_kwh", 0)
    pago_bim = consumo_datos.get("pago_bimestral_promedio", 0)
    gasto_anual = consumo_datos.get("gasto_anual_estimado", 0)
    ahorro_mensual = ahorro_anual / 12 if ahorro_anual > 0 else 0

    info = [
        ("Consumo detectado", f"{consumo_kwh:,.0f} kWh"),
        ("Pago bimestral promedio", _fmt(pago_bim)),
        ("Gasto anual estimado", _fmt(gasto_anual)),
        ("Ahorro mensual estimado (85%)", _fmt(ahorro_mensual)),
        ("Ahorro anual estimado", _fmt(ahorro_anual)),
    ]
    for label, val in info:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(90, 7, f"  {label}:")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(90, 7, val, new_x="LMARGIN", new_y="NEXT")

    if roi_anios > 0:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(39, 174, 96)
        pdf.cell(0, 8, f"Tiempo estimado de recuperacion: {roi_anios:.1f} anios ({roi_anios*12:.0f} meses)", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0)
    pdf.ln(5)

    if ahorro_anual > 0:
        roi_img = _crear_grafica_roi(precio_final, ahorro_anual, roi_anios)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(roi_img)
            tmp_path = tmp.name
        pdf.image(tmp_path, x=15, w=180)
        os.unlink(tmp_path)

    # --- Página 3: Ahorro proyectado ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(41, 65, 122)
    pdf.cell(0, 10, "PROYECCION DE AHORRO A LARGO PLAZO", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0)
    pdf.ln(5)

    if ahorro_anual > 0:
        ahorro_img = _crear_grafica_ahorro(ahorro_anual)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(ahorro_img)
            tmp_path = tmp.name
        pdf.image(tmp_path, x=15, w=180)
        os.unlink(tmp_path)
        pdf.ln(10)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Beneficios de la Energia Solar", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    beneficios = [
        "Reduccion de hasta 85% en su recibo de luz.",
        "Vida util de los paneles de 25+ anios con garantia.",
        "Incremento en el valor de su propiedad.",
        "Contribucion al medio ambiente con energia limpia.",
        "Proteccion contra aumentos futuros en tarifas electricas.",
    ]
    for b in beneficios:
        pdf.cell(5, 6, "")
        pdf.cell(0, 6, f"  {b}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "Tiene preguntas? Contactenos:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, EMPRESA, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, "Esta cotizacion tiene una vigencia de 15 dias naturales.", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
