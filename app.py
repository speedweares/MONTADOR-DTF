import streamlit as st
from PIL import Image
import math
from io import BytesIO

st.set_page_config(page_title="Montador DTF - Two Espaldas Per Row", layout="wide")
st.title("🖨️ Montador DTF - Packing 2 Espaldas x Fila, Espalda 27.5cm, Frontal 9cm")

ROLL_WIDTH_CM = 55
PPI_PREVIEW = 100   # PPI para vista previa
PPI_FINAL = 100     # PPI para imagen final (para reducir memoria)
PX_PER_CM_PREVIEW = PPI_PREVIEW / 2.54
PX_PER_CM_FINAL = PPI_FINAL / 2.54

# Espaciado 0.5 cm
SPACING_CM = 0.5
SPACING_PX = int(round(SPACING_CM * PX_PER_CM_FINAL))

# Permitir imágenes grandes
Image.MAX_IMAGE_PIXELS = None

uploaded_files = st.file_uploader(
    "Sube varios diseños (PNG, JPG)", 
    type=["png", "jpg", "jpeg"], 
    accept_multiple_files=True,
    accept_multiple_files=True
)

if uploaded_files:
    st.markdown("### 📋 Configura cada diseño")
    configuraciones = []
    for i, file in enumerate(uploaded_files):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            tipo = st.selectbox(
                f"Tipo diseño #{i+1}",
                ["Espalda (27.5 cm)", "Frontal (9 cm)"],
                key=f"tipo_{i}"
            )
        with col2:
            copias = st.number_input(
                f"Copias para diseño #{i+1}",
                min_value=1, value=10, key=f"copias_{i}"
            )
        with col3:
            st.image(file, width=80)
        configuraciones.append((file, tipo, copias))

    if st.button("🧩 Generar montaje"):
        items = []
        # Obtener anchura de rollo en px
        roll_w_px = int(round(ROLL_WIDTH_CM * PX_PER_CM_FINAL))

        for file, tipo_diseño, copias in configuraciones:
            try:
                img = Image.open(file).convert("RGBA")
            except Exception as e:
                st.error(f"Error cargando {file.name}: {e}")
                continue

            # Recortar transparencias
            alpha = img.split()[3]
            bbox = alpha.getbbox()
            if bbox:
                img = img.crop(bbox)

            # Ancho en cm
            if "Espalda" in tipo_diseño:
                ancho_cm = 27.5
            else:
                ancho_cm = 9

            # Calcular px exacto usando ancho_cm
            w_px = int(round(ancho_cm * PX_PER_CM_FINAL))
            h_px = int(round((img.height / img.width) * w_px))
            img_resized = img.resize((w_px, h_px), Image.LANCZOS)

            for _ in range(copias):
                items.append((img_resized, w_px, h_px))

        # Packing en una sola hoja
        x_offset = 0
        y_offset = 0
        current_row_h = 0

        placements = []
        for img, w_px, h_px in items:
            # Si no cabe en la fila actual, saltar a la siguiente
            if x_offset + w_px > roll_w_px:
                y_offset += current_row_h + SPACING_PX
                x_offset = 0
                current_row_h = 0

            placements.append((img, x_offset, y_offset))
            x_offset += w_px + SPACING_PX
            if h_px > current_row_h:
                current_row_h = h_px

        total_height = y_offset + current_row_h
        if total_height < 1:
            total_height = current_row_h

        # Crear canvas final
        canvas = Image.new("RGBA", (roll_w_px, total_height), (255, 255, 255, 0))
        for img, x, y in placements:
            canvas.paste(img, (x, y), img)

        total_cm = total_height / PX_PER_CM_FINAL
        total_m = total_cm / 100
        st.success(f"✅ Montaje FINAL → Alto: {total_cm:.1f} cm ({total_m:.2f} m)  con ancho fijo {ROLL_WIDTH_CM} cm")
        st.image(canvas, caption="🖼️ Montaje final", use_column_width=True)

        img_bytes = BytesIO()
        canvas.save(img_bytes, format="PNG")
        st.download_button(
            label="📥 Descargar montaje (PNG)",
            data=img_bytes.getvalue(),
            file_name="montaje_dtf_single.png",
            mime="image/png"
        )
