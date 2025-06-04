import streamlit as st
from PIL import Image
import math
from io import BytesIO
import zipfile
import tempfile
import os

st.set_page_config(page_title="Montador DTF Actualizado", layout="wide")
st.title("🖨️ Montador DTF - Espalda 27.5cm, Frontales 9cm, 0.5cm spacing")

ROLL_WIDTH_CM = 55

# Resoluciones
PPI_PREVIEW = 100
PPI_FINAL = 300
PX_PER_CM_PREVIEW = PPI_PREVIEW / 2.54
PX_PER_CM_FINAL = PPI_FINAL / 2.54

# Espaciado para corte 0.5 cm
SPACING_CM = 0.5
SPACING_PX_PREVIEW = int(SPACING_CM * PX_PER_CM_PREVIEW)
SPACING_PX_FINAL = int(SPACING_CM * PX_PER_CM_FINAL)

# Umbral para páginas (1m a 300ppi)
UMBRAL_PX_FINAL = int((100) * PX_PER_CM_FINAL)

# Desactivar límite para imágenes grandes
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
        preview_placements = []
        final_placements = []

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

            # Determinar ancho en cm
            if "Espalda" in tipo_diseño:
                ancho_cm = 27.5
            else:
                ancho_cm = 9

            # Calcular px para preview y final
            w_px_preview = int(ancho_cm * PX_PER_CM_PREVIEW)
            h_px_preview = int((img.height / img.width) * w_px_preview)
            img_preview = img.resize((w_px_preview, h_px_preview), Image.LANCZOS)

            w_px_final = int(ancho_cm * PX_PER_CM_FINAL)
            h_px_final = int((img.height / img.width) * w_px_final)
            img_final = img.resize((w_px_final, h_px_final), Image.LANCZOS)

            for _ in range(copias):
                items.append((img_preview, img_final, w_px_preview, h_px_preview, w_px_final, h_px_final))

        # Ubicar items en filas
        roll_w_px_preview = int(ROLL_WIDTH_CM * PX_PER_CM_PREVIEW)
        roll_w_px_final = int(ROLL_WIDTH_CM * PX_PER_CM_FINAL)

        cur_x_prev = 0
        cur_row_h_prev = 0
        y_offset_prev = 0

        cur_x_fin = 0
        cur_row_h_fin = 0
        y_offset_fin = 0

        for img_p, img_f, w_p, h_p, w_f, h_f in items:
            # Preview
            if cur_x_prev == 0:
                x_prev = 0
            else:
                if cur_x_prev + SPACING_PX_PREVIEW + w_p <= roll_w_px_preview:
                    x_prev = cur_x_prev + SPACING_PX_PREVIEW
                else:
                    y_offset_prev += cur_row_h_prev + SPACING_PX_PREVIEW
                    cur_x_prev = 0
                    cur_row_h_prev = 0
                    x_prev = 0

            preview_placements.append((img_p, x_prev, y_offset_prev, w_p, h_p))
            cur_x_prev = x_prev + w_p
            if h_p > cur_row_h_prev:
                cur_row_h_prev = h_p

            # Final
            if cur_x_fin == 0:
                x_fin = 0
            else:
                if cur_x_fin + SPACING_PX_FINAL + w_f <= roll_w_px_final:
                    x_fin = cur_x_fin + SPACING_PX_FINAL
                else:
                    y_offset_fin += cur_row_h_fin + SPACING_PX_FINAL
                    cur_x_fin = 0
                    cur_row_h_fin = 0
                    x_fin = 0

            final_placements.append((img_f, x_fin, y_offset_fin, w_f, h_f))
            cur_x_fin = x_fin + w_f
            if h_f > cur_row_h_fin:
                cur_row_h_fin = h_f

        # Lienzo preview
        total_h_prev = y_offset_prev + cur_row_h_prev
        canvas_prev = Image.new("RGBA", (roll_w_px_preview, total_h_prev), (255, 255, 255, 0))
        for img_p, x_p, y_p, w_p, h_p in preview_placements:
            canvas_prev.paste(img_p, (x_p, y_p), img_p)

        st.success("✅ Vista previa generada.")
        st.image(canvas_prev, caption="👁️ Vista previa", use_column_width=True)

        # Crear páginas final
        pages = []
        cur_page = Image.new("RGBA", (roll_w_px_final, UMBRAL_PX_FINAL), (255, 255, 255, 0))
        page_index = 1

        for (img_f, x_f, y_f, w_f, h_f) in final_placements:
            if y_f + h_f > (page_index * UMBRAL_PX_FINAL):
                pages.append(cur_page)
                cur_page = Image.new("RGBA", (roll_w_px_final, UMBRAL_PX_FINAL), (255, 255, 255, 0))
                page_index += 1

            y_local = y_f - ((page_index - 1) * UMBRAL_PX_FINAL)
            cur_page.paste(img_f, (x_f, y_local), img_f)

        pages.append(cur_page)

        total_h_fin = y_offset_fin + cur_row_h_fin
        total_cm = total_h_fin / PX_PER_CM_FINAL
        total_m = total_cm / 100
        st.success(f"✅ Montaje FINAL → Altura total: {total_cm:.1f} cm ({total_m:.2f} m)")
        st.write(f"• Se generaron **{len(pages)} página(s)** de {UMBRAL_PX_FINAL} px (~1 m).")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmpzip:
            with zipfile.ZipFile(tmpzip.name, "w", zipfile.ZIP_DEFLATED) as z:
                for idx, pg in enumerate(pages, start=1):
                    img_bytes = BytesIO()
                    pg.save(img_bytes, format="PNG")
                    z.writestr(f"montaje_page_{idx:02d}.png", img_bytes.getvalue())

            tmpzip.flush()
            tmpzip.seek(0)
            zip_data = open(tmpzip.name, "rb").read()
            st.download_button(
                label="📥 Descargar TODO en ZIP (300ppi)",
                data=zip_data,
                file_name="montaje_dtf_pages.zip",
                mime="application/zip"
            )

        os.remove(tmpzip.name)
