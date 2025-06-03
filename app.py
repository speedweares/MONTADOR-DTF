
import streamlit as st
from PIL import Image
import math
from io import BytesIO

st.set_page_config(page_title="Montador DTF Final", layout="wide")
st.title("🖨️ Montador DTF - Packing de múltiples diseños")

ROLL_WIDTH_CM = 55
PPI = 300
PX_PER_CM = PPI / 2.54

# Espaciado para corte 1.5 cm
SPACING_CM = 1.5
SPACING_PX = int(SPACING_CM * PX_PER_CM)

uploaded_files = st.file_uploader(
    "Sube varios diseños (PNG, JPG)", 
    type=["png", "jpg", "jpeg"], 
    accept_multiple_files=True
)

if uploaded_files:
    # Configuración para cada diseño
    config = []
    st.markdown("### 📋 Configura cada diseño")
    for i, file in enumerate(uploaded_files):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            tipo = st.selectbox(
                f"Tipo diseño {i+1}", 
                ["Espalda (22.5 cm)", "Frontal (5 cm)", "Frontal (7 cm)"], 
                key=f"tipo_{i}"
            )
        with col2:
            copias = st.number_input(
                f"Copias para diseño {i+1}", 
                min_value=1, value=5, key=f"copias_{i}"
            )
        with col3:
            st.image(file, width=80)
        config.append((file, tipo, copias))

    if st.button("🧩 Generar montaje"):
        # Preparar lista de items (imagen, width_cm, height_px)
        items = []
        for file, tipo_diseño, copias in config:
            image = Image.open(file).convert("RGBA")
            # Determinar ancho en cm según tipo
            if "Espalda" in tipo_diseño:
                width_cm = 22.5
            elif "5" in tipo_diseño:
                width_cm = 5
            else:
                width_cm = 7

            # Calcular valores en px
            width_px = int(width_cm * PX_PER_CM)
            aspect_ratio = image.height / image.width
            height_px = int(width_px * aspect_ratio)
            resized_img = image.resize((width_px, height_px))

            # Agregar copias a la lista
            for _ in range(copias):
                items.append((resized_img, width_cm, width_px, height_px))

        # Packing: ubicar cada item en filas de ancho fijo ROLL_WIDTH_CM
        roll_width_px = int(ROLL_WIDTH_CM * PX_PER_CM)
        placements = []  # lista de tuplas (image, x, y)
        current_x = 0
        current_row_height = 0
        y_offset = 0

        for img, width_cm, w_px, h_px in items:
            # Si cabe en la fila actual
            if current_x == 0:
                x = 0
                # Correrá sin spacing a izquierda
            else:
                # Intentar colocar con spacing
                if current_x + SPACING_PX + w_px <= roll_width_px:
                    x = current_x + SPACING_PX
                else:
                    # Nueva fila
                    y_offset += current_row_height + SPACING_PX
                    current_x = 0
                    current_row_height = 0
                    x = 0
            # Ubicar el item
            placements.append((img, x, y_offset, w_px, h_px))
            # Actualizar current_x y current_row_height
            current_x = x + w_px
            if h_px > current_row_height:
                current_row_height = h_px

        # Después de colocar todos, calcular altura total
        total_height_px = y_offset + current_row_height
        canvas = Image.new("RGBA", (roll_width_px, total_height_px), (255, 255, 255, 0))

        for img, x, y, w_px, h_px in placements:
            canvas.paste(img, (x, y), img)

        # Cálculos de medida
        total_height_cm = total_height_px / PX_PER_CM
        total_height_m = total_height_cm / 100

        st.success(f"✅ Montaje generado — Altura total: {total_height_cm:.1f} cm ({total_height_m:.2f} m)")
        st.image(canvas, caption="🖼️ Montaje final", use_column_width=True)

        # Botón de descarga
        img_bytes = BytesIO()
        canvas.save(img_bytes, format="PNG")
        st.download_button(
            label="📥 Descargar montaje final",
            data=img_bytes.getvalue(),
            file_name="montaje_dtf_final.png",
            mime="image/png"
        )
