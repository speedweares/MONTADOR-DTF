
import streamlit as st
import cv2
import numpy as np
import math
from io import BytesIO
import zipfile
import tempfile
import os
from PIL import Image

st.set_page_config(page_title="Montador DTF Ultra-Optimizado", layout="wide")
st.title("🖨️ Montador DTF - Ultra-Optimizado (sin crashes)")

ROLL_WIDTH_CM = 55

# Resolutions
PPI_FINAL = 300
PX_CM_FINAL = PPI_FINAL / 2.54

# Spacing 0.5 cm
SPACING_CM = 0.5
SPACING_PX_FINAL = int(SPACING_CM * PX_CM_FINAL)

# Page threshold (1 m at 300 ppi)
UMBRAL_PX_PAGE = int(100 * PX_CM_FINAL)

# Preview threshold
UMBRAL_SIN_PREVIEW = 50

# Disable PIL BOMBS
Image.MAX_IMAGE_PIXELS = None

uploaded_files = st.file_uploader(
    "1) Sube uno o varios diseños (PNG/JPG)", 
    type=["png", "jpg", "jpeg"], 
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("📥 Sube al menos un archivo para comenzar.")
    st.stop()

st.markdown("### 2) Configura cada diseño")
configuraciones = []
total_copias_estimadas = 0

for i, upload in enumerate(uploaded_files):
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        tipo = st.selectbox(
            f"Tipo diseño #{i+1}",
            ["Espalda (22.5 cm)", "Frontal (5 cm)", "Frontal (7 cm)"],
            key=f"tipo_{i}"
        )
    with col2:
        copias = st.number_input(
            f"Copias para diseño #{i+1}",
            min_value=1, value=10, key=f"copias_{i}"
        )
    with col3:
        st.image(upload, width=80)
    configuraciones.append((upload, tipo, copias))
    total_copias_estimadas += copias

st.markdown(f"**Total de copias estimadas:** {total_copias_estimadas:,}")

show_preview = total_copias_estimadas <= UMBRAL_SIN_PREVIEW

if not show_preview:
    st.warning("⚠️ Se omitirá la vista previa gráfica porque hay muchas copias. Solo generaré un resumen en texto.")

if st.button("🧩 Generar montaje FINAL"):
    # Prepare page buffer
    roll_w_px = int(ROLL_WIDTH_CM * PX_CM_FINAL)
    canvas_page = Image.new("RGBA", (roll_w_px, UMBRAL_PX_PAGE), (255, 255, 255, 0))
    page_index = 1
    y_offset_page = 0
    current_row_height = 0
    x_offset_page = 0

    temp_dir = tempfile.mkdtemp(prefix="montajedtf_")
    pages_paths = []

    for upload, tipo, copias in configuraciones:
        file_bytes = np.frombuffer(upload.read(), dtype=np.uint8)
        img_cv = cv2.imdecode(file_bytes, cv2.IMREAD_UNCHANGED)

        if img_cv.shape[2] == 4:
            alpha = img_cv[:, :, 3]
            coords = cv2.findNonZero(alpha)
            x, y, w, h = cv2.boundingRect(coords)
            img_cv = img_cv[y : y + h, x : x + w]

        if img_cv.shape[2] == 3:
            b, g, r = cv2.split(img_cv)
            alpha = np.ones(b.shape, dtype=b.dtype) * 255
            img_cv = cv2.merge((b, g, r, alpha))

        if "Espalda" in tipo:
            width_cm = 22.5
        elif "5" in tipo:
            width_cm = 5.0
        else:
            width_cm = 7.0

        w_px_final = int(width_cm * PX_CM_FINAL)
        aspect_ratio = img_cv.shape[0] / img_cv.shape[1]
        h_px_final = int(w_px_final * aspect_ratio)

        img_resized_cv = cv2.resize(
            img_cv, (w_px_final, h_px_final), interpolation=cv2.INTER_CUBIC
        )
        img_resized_pil = Image.fromarray(
            cv2.cvtColor(img_resized_cv, cv2.COLOR_BGRA2RGBA)
        )

        for _ in range(copias):
            if x_offset_page > 0:
                if x_offset_page + SPACING_PX_FINAL + w_px_final <= roll_w_px:
                    x_pos = x_offset_page + SPACING_PX_FINAL
                else:
                    y_offset_page += current_row_height + SPACING_PX_FINAL
                    x_offset_page = 0
                    current_row_height = 0
                    x_pos = 0
            else:
                x_pos = 0

            if y_offset_page + h_px_final > page_index * UMBRAL_PX_PAGE:
                page_path = os.path.join(temp_dir, f"pagina_{page_index:02d}.png")
                canvas_page.save(page_path)
                pages_paths.append(page_path)

                page_index += 1
                canvas_page = Image.new(
                    "RGBA", (roll_w_px, UMBRAL_PX_PAGE), (255, 255, 255, 0)
                )
                y_offset_page = ( (page_index - 1) * UMBRAL_PX_PAGE )
                current_row_height = 0
                x_offset_page = 0
                x_pos = 0

            y_local = y_offset_page - ( (page_index - 1) * UMBRAL_PX_PAGE )
            canvas_page.paste(img_resized_pil, (x_pos, y_local), img_resized_pil)

            x_offset_page = x_pos + w_px_final
            if h_px_final > current_row_height:
                current_row_height = h_px_final

    last_page_path = os.path.join(temp_dir, f"pagina_{page_index:02d}.png")
    canvas_page.save(last_page_path)
    pages_paths.append(last_page_path)

    total_px_height = (page_index - 1) * UMBRAL_PX_PAGE + current_row_height
    total_cm_height = total_px_height / PX_CM_FINAL
    total_m_height = total_cm_height / 100

    st.success(
        f"✅ Montaje creado: Altura total = {total_cm_height:.1f} cm  ({total_m_height:.2f} m)."
    )
    st.write(f"• Páginas generadas: **{len(pages_paths)}** (cada una ~1 m a 300 ppi).")

    if show_preview:
        st.success("✅ Vista previa no se muestra, hay demasiadas copias.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmpzip:
        with zipfile.ZipFile(tmpzip.name, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in pages_paths:
                zf.write(p, os.path.basename(p))
        tmpzip.flush()
        tmpzip.seek(0)
        zip_bytes = open(tmpzip.name, "rb").read()
        st.download_button(
            label="📥 Descargar ZIP con todas las páginas (300 ppi)",
            data=zip_bytes,
            file_name="montaje_dtf_pages.zip",
            mime="application/zip",
        )

    for p in pages_paths:
        os.remove(p)
    os.rmdir(temp_dir)
