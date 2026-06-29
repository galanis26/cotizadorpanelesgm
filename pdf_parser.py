import re
import pdfplumber


def _limpiar_numero(texto: str) -> float | None:
    texto = texto.replace(",", "").replace(" ", "").strip()
    try:
        return float(texto)
    except ValueError:
        return None


def extraer_total_pdf(archivo) -> float:
    """Extrae el monto total de un PDF de cotización.
    Busca patrones como 'Total $2,479.18' con regex flexible.
    """
    full_text = ""
    with pdfplumber.open(archivo) as pdf:
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + "\n"

    total_patterns = [
        re.compile(r'(?:Grand\s*)?Total\s*\$?\s*([\d,]+(?:\.\d{1,2})?)', re.IGNORECASE),
        re.compile(r'Total\s*(?:USD|MXN|MN)?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)', re.IGNORECASE),
        re.compile(r'Importe\s*Total\s*\$?\s*([\d,]+(?:\.\d{1,2})?)', re.IGNORECASE),
        re.compile(r'Monto\s*Total\s*\$?\s*([\d,]+(?:\.\d{1,2})?)', re.IGNORECASE),
    ]

    candidatos = []
    for pat in total_patterns:
        for m in pat.finditer(full_text):
            val = _limpiar_numero(m.group(1))
            if val and val > 1:
                candidatos.append(val)

    if candidatos:
        return max(candidatos)

    # Fallback: buscar el número más grande precedido de $
    precio_pat = re.compile(r'\$\s*([\d,]+(?:\.\d{1,2})?)')
    todos = []
    for m in precio_pat.finditer(full_text):
        val = _limpiar_numero(m.group(1))
        if val and val > 10:
            todos.append(val)
    return max(todos) if todos else 0.0


def extraer_items_pdf(archivo) -> list[dict]:
    """Extrae items individuales de un PDF de cotización."""
    items = []
    with pdfplumber.open(archivo) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split("\n"):
                # Buscar líneas con precio al final como $826.32 o s 45.60
                match = re.search(r'[\$s]\s*([\d,]+\.\d{2})\s*$', line)
                if match:
                    total = _limpiar_numero(match.group(1))
                    if total and total > 0.5:
                        desc = line[:match.start()].strip()
                        desc = re.sub(r'[\d.]+\s*$', '', desc).strip()
                        desc = re.sub(r'^[\d\s]+', '', desc).strip()
                        if len(desc) > 3:
                            items.append({
                                "descripcion": desc[:80],
                                "cantidad": 1,
                                "precio_unitario": total,
                                "total": total,
                            })
    return items


def extraer_consumo_recibo(archivo) -> dict:
    """Extrae datos de consumo del recibo de luz CFE."""
    resultado = {
        "consumo_kwh": 0.0,
        "total_pagar": 0.0,
        "pago_bimestral_promedio": 0.0,
        "gasto_anual_estimado": 0.0,
        "periodo": "No detectado",
        "historico": [],
    }

    full_text = ""
    with pdfplumber.open(archivo) as pdf:
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + "\n"

    # Total a pagar
    total_patterns = [
        re.compile(r'TOTAL\s*A\s*PAGAR\s*:?\s*\$?\s*([\d,]+(?:\.\d{0,2})?)', re.IGNORECASE),
        re.compile(r'Total\s*\$?\s*([\d,]+\.\d{2})', re.IGNORECASE),
        re.compile(r'Fac\.\s*del\s*Periodo\s*([\d,]+\.\d{2})', re.IGNORECASE),
    ]
    for pat in total_patterns:
        m = pat.search(full_text)
        if m:
            val = _limpiar_numero(m.group(1))
            if val and val > 50:
                resultado["total_pagar"] = val
                break

    # Consumo kWh
    kwh_pat = re.compile(r'Energ[ií]a\s*\(kWh\)\s*[\d,]+\s*[\d,]+\s*([\d,]+)', re.IGNORECASE)
    m = kwh_pat.search(full_text)
    if m:
        resultado["consumo_kwh"] = _limpiar_numero(m.group(1)) or 0

    # Periodo
    periodo_pat = re.compile(r'PERIODO\s*FACTURADO\s*:?\s*(.+?)(?:\n|$)', re.IGNORECASE)
    m = periodo_pat.search(full_text)
    if m:
        resultado["periodo"] = m.group(1).strip()

    # Histórico de pagos - extraer todos los importes
    hist_pat = re.compile(r'del\s+(.+?)\s+al\s+(.+?)\s+(\d+)\s+\$([\d,]+(?:\.\d{2})?)', re.IGNORECASE)
    pagos = []
    for m in hist_pat.finditer(full_text):
        monto = _limpiar_numero(m.group(4))
        if monto:
            pagos.append({
                "periodo": f"del {m.group(1)} al {m.group(2)}",
                "consumo_kwh": int(m.group(3)),
                "importe": monto,
            })
            resultado["historico"].append(monto)

    # Calcular promedio bimestral y gasto anual con el histórico
    if resultado["historico"]:
        resultado["pago_bimestral_promedio"] = sum(resultado["historico"]) / len(resultado["historico"])
        resultado["gasto_anual_estimado"] = resultado["pago_bimestral_promedio"] * 6  # 6 bimestres al año
    elif resultado["total_pagar"] > 0:
        resultado["pago_bimestral_promedio"] = resultado["total_pagar"]
        resultado["gasto_anual_estimado"] = resultado["total_pagar"] * 6

    return resultado
