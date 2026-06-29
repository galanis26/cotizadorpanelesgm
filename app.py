import streamlit as st
from pdf_parser import extraer_total_pdf, extraer_items_pdf, extraer_consumo_recibo
from generar_reportes import generar_pdf_interno, generar_pdf_cliente

st.set_page_config(page_title="GM - Cotizador Solar", page_icon="☀️", layout="wide")

st.title("☀️ Cotizador de Paneles Solares")
st.caption("GM Ferretera de Equipos S.A de C.V.")
st.divider()

# --- Inputs ---
col_pdf, col_datos = st.columns([1, 1], gap="large")

with col_pdf:
    st.subheader("📄 Cargar Documentos")
    pdf_paneles = st.file_uploader("Cotización de paneles (proveedor)", type="pdf", key="paneles")
    pdf_materiales = st.file_uploader("Precios de materiales adicionales", type="pdf", key="materiales")
    pdf_recibo = st.file_uploader("Recibo de luz del cliente (CFE)", type="pdf", key="recibo")

with col_datos:
    st.subheader("💰 Costos e Instalación")
    sub1, sub2 = st.columns(2)
    with sub1:
        costo_instalacion = st.number_input(
            "Precio de instalación ($MXN)", min_value=0.0, value=0.0, step=500.0, format="%.2f",
        )
    with sub2:
        tipo_cambio = st.number_input(
            "Tipo de cambio (1 USD → MXN)", min_value=1.0, value=17.50, step=0.10, format="%.2f",
        )

    sub3, sub4 = st.columns(2)
    with sub3:
        porcentaje_ganancia_instalacion = st.number_input(
            "% ganancia sobre instalación", min_value=0.0, max_value=200.0, value=30.0, step=1.0, format="%.1f",
        )
    with sub4:
        porcentaje_ganancia_paneles = st.number_input(
            "% ganancia sobre paneles", min_value=0.0, max_value=200.0, value=15.0, step=1.0, format="%.1f",
        )

    st.markdown("---")
    st.subheader("✏️ Montos manuales (respaldo si el PDF no se lee)")
    man1, man2 = st.columns(2)
    with man1:
        total_paneles_manual = st.number_input(
            "Total paneles manual (USD)", min_value=0.0, value=0.0, step=100.0, format="%.2f",
            help="Monto en DÓLARES. Se convertirá a MXN con el tipo de cambio.",
        )
    with man2:
        total_materiales_manual = st.number_input(
            "Total materiales manual (MXN)", min_value=0.0, value=0.0, step=100.0, format="%.2f",
            help="Monto en PESOS MEXICANOS.",
        )

    st.subheader("📝 Información del Proyecto")
    nombre_cliente = st.text_input("Nombre del cliente (opcional)")
    descripcion = st.text_area(
        "Descripción de lo que se cotiza",
        placeholder="Ej: Instalación de 8 paneles solares en casa habitación...",
        height=100,
    )

st.divider()

# --- Procesar ---
if st.button("⚡ Generar Cotización", type="primary", use_container_width=True):

    with st.spinner("Procesando documentos..."):
        # Extraer totales de PDFs
        total_paneles_pdf = extraer_total_pdf(pdf_paneles) if pdf_paneles else 0.0
        total_materiales_pdf = extraer_total_pdf(pdf_materiales) if pdf_materiales else 0.0
        items_paneles = extraer_items_pdf(pdf_paneles) if pdf_paneles else []

        # Usar manual si PDF da 0
        total_paneles_usd = total_paneles_pdf if total_paneles_pdf > 0 else total_paneles_manual
        total_paneles = total_paneles_usd * tipo_cambio  # Convertir USD → MXN
        total_materiales = total_materiales_pdf if total_materiales_pdf > 0 else total_materiales_manual

        # Recibo CFE
        consumo_datos = extraer_consumo_recibo(pdf_recibo) if pdf_recibo else {
            "consumo_kwh": 0, "total_pagar": 0, "pago_bimestral_promedio": 0,
            "gasto_anual_estimado": 0, "periodo": "N/A", "historico": [],
        }

    # --- REGLAS DE NEGOCIO ---
    # % ganancia paneles se aplica sobre costo de paneles
    paneles_con_ganancia = total_paneles * (1 + porcentaje_ganancia_paneles / 100)
    utilidad_paneles = total_paneles * (porcentaje_ganancia_paneles / 100)
    # % ganancia instalación se aplica sobre mano de obra
    instalacion_con_ganancia = costo_instalacion * (1 + porcentaje_ganancia_instalacion / 100)
    utilidad_instalacion = costo_instalacion * (porcentaje_ganancia_instalacion / 100)
    utilidad_neta = utilidad_paneles + utilidad_instalacion
    precio_final_cliente = paneles_con_ganancia + total_materiales + instalacion_con_ganancia

    # ROI
    ahorro_anual = consumo_datos["gasto_anual_estimado"] * 0.85  # 85% ahorro con paneles
    roi_anios = precio_final_cliente / ahorro_anual if ahorro_anual > 0 else 0

    # --- Mostrar resumen ---
    st.subheader("📊 Resumen de Cotización")

    if total_paneles_pdf > 0:
        st.success(f"✅ PDF de paneles leído: ${total_paneles_pdf:,.2f} USD × {tipo_cambio} = ${total_paneles:,.2f} MXN")
    elif total_paneles_manual > 0:
        st.warning(f"⚠️ Se usó monto manual para paneles: ${total_paneles_manual:,.2f} USD × {tipo_cambio} = ${total_paneles:,.2f} MXN")
    if total_materiales_pdf > 0:
        st.success(f"✅ PDF de materiales leído correctamente: ${total_materiales_pdf:,.2f}")
    elif total_materiales_manual > 0:
        st.warning("⚠️ Se usó el monto manual para materiales.")

    m1, m2, m3 = st.columns(3)
    m1.metric("Costo Paneles (MXN)", f"${total_paneles:,.2f}")
    m2.metric(f"Paneles + {porcentaje_ganancia_paneles}% al cliente", f"${paneles_con_ganancia:,.2f}")
    m3.metric("Costo Materiales", f"${total_materiales:,.2f}")

    m4, m5, m6 = st.columns(3)
    m4.metric("Instalación (base)", f"${costo_instalacion:,.2f}")
    m5.metric(f"Instalación + {porcentaje_ganancia_instalacion}%", f"${instalacion_con_ganancia:,.2f}")
    m6.metric("💰 Utilidad Neta Total", f"${utilidad_neta:,.2f}")

    st.divider()
    p1, p2 = st.columns(2)
    p1.metric("🏷️ PRECIO FINAL AL CLIENTE", f"${precio_final_cliente:,.2f}")
    if ahorro_anual > 0:
        p2.metric("📈 ROI Estimado", f"{roi_anios:.1f} años ({roi_anios*12:.0f} meses)")

    if items_paneles:
        with st.expander("Ver items detectados del PDF de paneles"):
            st.dataframe(items_paneles, use_container_width=True)
    if pdf_recibo:
        with st.expander("Ver datos del recibo de luz"):
            st.json({k: v for k, v in consumo_datos.items() if k != "historico"})
            if consumo_datos["historico"]:
                st.write("Histórico de pagos bimestrales:", consumo_datos["historico"])

    st.divider()

    # --- Generar PDFs ---
    st.subheader("📥 Descargar Reportes")
    col_d1, col_d2 = st.columns(2)

    with col_d1:
        pdf_int_bytes = generar_pdf_interno(
            total_paneles=total_paneles,
            total_materiales=total_materiales,
            costo_instalacion=costo_instalacion,
            porcentaje_ganancia_instalacion=porcentaje_ganancia_instalacion,
            porcentaje_ganancia_paneles=porcentaje_ganancia_paneles,
            paneles_con_ganancia=paneles_con_ganancia,
            instalacion_con_ganancia=instalacion_con_ganancia,
            utilidad_paneles=utilidad_paneles,
            utilidad_instalacion=utilidad_instalacion,
            utilidad_neta=utilidad_neta,
            precio_final=precio_final_cliente,
            descripcion=descripcion,
            items_paneles=items_paneles,
        )
        st.download_button(
            "📋 Descargar Reporte Interno",
            data=pdf_int_bytes,
            file_name="cotizacion_interna.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    with col_d2:
        pdf_cli_bytes = generar_pdf_cliente(
            precio_final=precio_final_cliente,
            paneles_con_ganancia=paneles_con_ganancia,
            total_materiales=total_materiales,
            instalacion_con_ganancia=instalacion_con_ganancia,
            consumo_datos=consumo_datos,
            ahorro_anual=ahorro_anual,
            roi_anios=roi_anios,
            descripcion=descripcion,
            nombre_cliente=nombre_cliente,
        )
        st.download_button(
            "📄 Descargar Cotización para Cliente",
            data=pdf_cli_bytes,
            file_name="cotizacion_cliente.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    st.success("¡Cotización generada exitosamente!")
