import streamlit as st
from PIL import Image
import math
from io import BytesIO

st.set_page_config(page_title="Montador DTF Optimizado", layout="wide")
st.title("🖨️ Montador DTF - Single Sheet 55cm Width (Memoria Optimizada)")

ROLL_WIDTH_CM = 55
PPI_PREVIEW = 100   # baja resolución para preview
PPI_FINAL = 100     # reducir a 100 ppi para final y ahorrar memoria
PX_PER_CM_PREVIEW = PPI_PREVIEW / 2.54
PX_PER_CM_FINAL = PPI_FINAL / 2.54

# Espaciado 0.5 cm
SPACING_CM = 0.5
SPACING_PX = int(SPACING_CM * PX_PER_CM_FINAL)  # usar escala final

# Permitir imágenes grandes
Image.MAX_IMAGE_PIXELS = None

uploaded_files = st.file_uploader(
    "Sube varios diseños (PNG, JPG)",
    type=["png", "jpg", "jpeg"],
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
        # Procesar cada imagen
        roll_w_px = int(ROLL_WIDTH_CM * PX_PER_CM_FINAL)
        for file, tipo_diseño, copias in configuraciones:
            try:
                img = Image.open(file).convert("RGBA")
            except Exception as e:
                st.error(f"Error cargando {file.name}: {e}")
                continue

            # Crop transparente
            alpha = img.split()[3]
            bbox = alpha.getbbox()
            if bbox:
                img = img.crop(bbox)

            # Ancho en cm
            if "Espalda" in tipo_diseño:
                ancho_cm = 27.5
            else:
                ancho_cm = 9

            w_px = int(ancho_cm * PX_PER_CM_FINAL)
            h_px = int((img.height / img.width) * w_px)
            img_resized = img.resize((w_px, h_px), Image.LANCZOS)

            for _ in range(copias):
                items.append((img_resized, w_px, h_px))

        # Calcular ubicaciones
        x_offset = 0
        y_offset = 0
        current_row_h = 0
        placements = []
        for img, w_px, h_px in items:
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
        st.success(f"✅ Montaje FINAL → Alto: {total_cm:.1f} cm ({total_m:.2f} m)")
        st.image(canvas, caption="🖼️ Montaje final", use_column_width=True)

        # Descarga
        img_bytes = BytesIO()
        canvas.save(img_bytes, format="PNG")
        st.download_button(
            label="📥 Descargar montaje (PNG)",
            data=img_bytes.getvalue(),
            file_name="montaje_dtf_single.png",
            mime="image/png"
        )
