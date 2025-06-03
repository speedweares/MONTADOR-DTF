
import streamlit as st
import cv2
import numpy as np
import math
from io import BytesIO
import zipfile
import tempfile
import os
from PIL import Image

st.set_page_config(page_title="Montador DTF Optimizado", layout="wide")
st.title("🖨️ Montador DTF - Versión Optimizada para Muchos Imágenes")

ROLL_WIDTH_CM = 55

# Resoluciones
PPI_PREVIEW = 50   # aún más baja para previsualización (50 ppi)
PPI_FINAL = 300    # descarga final
PX_PER_CM_PREVIEW = PPI_PREVIEW / 2.54
PX_PER_CM_FINAL = PPI_FINAL / 2.54

# Espaciado 0.5 cm
SPACING_CM = 0.5
SPACING_PX_PREVIEW = int(SPACING_CM * PX_PER_CM_PREVIEW)
SPACING_PX_FINAL = int(SPACING_CM * PX_PER_CM_FINAL)

# Umbral para dividir en "páginas" (1 m en 300 ppi)
UMBRAL_PX_FINAL = int(100 * PX_PER_CM_FINAL)

# Desactivar límite BOMBS para PIL
Image.MAX_IMAGE_PIXELS = None

uploaded_files = st.file_uploader(
    "Sube varios diseños (PNG, JPG)", 
    type=["png", "jpg", "jpeg"], 
    accept_multiple_files=True
)

if uploaded_files:
    st.markdown("### 📋 Configura cada diseño")
    configuraciones = []
    total_items = 0
    for i, file in enumerate(uploaded_files):
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
            st.image(file, width=80)
        configuraciones.append((file, tipo, copias))
        total_items += copias

    # Advertencia si muchos ítems
    if total_items > 200:
        st.warning("Se detectaron muchos diseños, la previsualización puede tardar. Se omitirá la vista previa.")
        show_preview = False
    else:
        show_preview = True

    if st.button("🧩 Generar montaje"):
        # Preprarar carpetas temporales
        temp_dir = tempfile.mkdtemp()
        page_index = 1
        pages_files = []
        # Variables de colocación final
        roll_w_px_final = int(ROLL_WIDTH_CM * PX_PER_CM_FINAL)
        cur_x_fin = 0
        cur_row_h_fin = 0
        y_offset_fin = 0
        # Variables para page
        cur_page = Image.new("RGBA", (roll_w_px_final, UMBRAL_PX_FINAL), (255,255,255,0))

        # Para preview si aplica
        if show_preview:
            roll_w_px_preview = int(ROLL_WIDTH_CM * PX_PER_CM_PREVIEW)
            cur_x_prev = 0
            cur_row_h_prev = 0
            y_offset_prev = 0
            canvas_prev = Image.new("RGBA", (roll_w_px_preview, 1), (255,255,255,0))  # altura inicial mínima

        # Procesar cada diseño
        for file, tipo_diseño, copias in configuraciones:
            # Leer con OpenCV para velocidad
            file_bytes = np.asarray(bytearray(file.read()), dtype=np.uint8)
            img_cv = cv2.imdecode(file_bytes, cv2.IMREAD_UNCHANGED)
            # Dividir canales y recortar alpha
            if img_cv.shape[2] == 4:
                alpha = img_cv[:,:,3]
                coords = cv2.findNonZero(alpha)
                x,y,w,h = cv2.boundingRect(coords)
                img_cv = img_cv[y:y+h, x:x+w]
            # Convertir a BGRA si no tiene alpha
            if img_cv.shape[2] == 3:
                b,g,r = cv2.split(img_cv)
                alpha = np.ones(b.shape, dtype=b.dtype) * 255
                img_cv = cv2.merge((b,g,r,alpha))

            # Determinar ancho en cm
            if "Espalda" in tipo_diseño:
                ancho_cm = 22.5
            elif "5" in tipo_diseño:
                ancho_cm = 5
            else:
                ancho_cm = 7

            # Calcular dimensiones en preview y final
            h_cv, w_cv = img_cv.shape[:2]
            w_px_prev = int(ancho_cm * PX_PER_CM_PREVIEW)
            h_px_prev = int((h_cv / w_cv) * w_px_prev)
            w_px_fin = int(ancho_cm * PX_PER_CM_FINAL)
            h_px_fin = int((h_cv / w_cv) * w_px_fin)

            # Redimensionar con OpenCV (bicúbico)
            img_prev = cv2.resize(img_cv, (w_px_prev, h_px_prev), interpolation=cv2.INTER_CUBIC)
            img_fin = cv2.resize(img_cv, (w_px_fin, h_px_fin), interpolation=cv2.INTER_CUBIC)

            # Convertir preview a PIL si es necesario
            if show_preview:
                img_prev_pil = Image.fromarray(cv2.cvtColor(img_prev, cv2.COLOR_BGRA2RGBA))

            # Convertir final a PIL
            img_fin_pil = Image.fromarray(cv2.cvtColor(img_fin, cv2.COLOR_BGRA2RGBA))

            # Añadir copias
            for _ in range(copias):
                # Colocación final
                if cur_x_fin == 0:
                    x_fin = 0
                else:
                    if cur_x_fin + SPACING_PX_FINAL + w_px_fin <= roll_w_px_final:
                        x_fin = cur_x_fin + SPACING_PX_FINAL
                    else:
                        y_offset_fin += cur_row_h_fin + SPACING_PX_FINAL
                        cur_x_fin = 0
                        cur_row_h_fin = 0
                        x_fin = 0
                # Si excede página
                if y_offset_fin + h_px_fin > page_index * UMBRAL_PX_FINAL:
                    # Guardar página actual
                    page_path = os.path.join(temp_dir, f"page_{page_index}.png")
                    cur_page.save(page_path)
                    pages_files.append(page_path)
                    page_index += 1
                    cur_page = Image.new("RGBA", (roll_w_px_final, UMBRAL_PX_FINAL), (255,255,255,0))
                # Posición local en página
                y_local = y_offset_fin - ((page_index-1) * UMBRAL_PX_FINAL)
                cur_page.paste(img_fin_pil, (x_fin, y_local), img_fin_pil)
                # Actualizar offsets
                cur_x_fin = x_fin + w_px_fin
                if h_px_fin > cur_row_h_fin:
                    cur_row_h_fin = h_px_fin

                # Colocación preview si aplica
                if show_preview:
                    if cur_x_prev == 0:
                        x_prev = 0
                    else:
                        if cur_x_prev + SPACING_PX_PREVIEW + w_px_prev <= roll_w_px_preview:
                            x_prev = cur_x_prev + SPACING_PX_PREVIEW
                        else:
                            y_offset_prev += cur_row_h_prev + SPACING_PX_PREVIEW
                            cur_x_prev = 0
                            cur_row_h_prev = 0
                            x_prev = 0
                    canvas_prev_temp = Image.new("RGBA", (roll_w_px_preview, y_offset_prev + cur_row_h_prev + h_px_prev), (255,255,255,0))
                    for img_p, xp, yp, wp, hp in [(img_prev_pil, x_prev, y_offset_prev, w_px_prev, h_px_prev)]:
                        canvas_prev_temp.paste(img_p, (xp, yp), img_p)
                    canvas_prev = canvas_prev_temp
                    cur_x_prev = x_prev + w_px_prev
                    if h_px_prev > cur_row_h_prev:
                        cur_row_h_prev = h_px_prev

        # Guardar última página final
        pages_files.append(os.path.join(temp_dir, f"page_{page_index}.png"))
        cur_page.save(pages_files[-1])

        # Mostrar preview
        if show_preview:
            st.success("✅ Vista previa generada (baja resolución).")
            st.image(canvas_prev, caption="👁️ Vista previa (PPI bajo)", use_column_width=True)

        # Calcular medidas totales
        total_h_fin = y_offset_fin + cur_row_h_fin
        total_cm = total_h_fin / PX_PER_CM_FINAL
        total_m = total_cm / 100
        st.success(f"✅ Montaje FINAL preparado → Altura total: {total_cm:.1f} cm ({total_m:.2f} m)")
        st.write(f"• Se generaron **{len(pages_files)} página(s)** de {UMBRAL_PX_FINAL} px (~1 m a 300 ppi).")

        # Crear ZIP con páginas
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmpzip:
            with zipfile.ZipFile(tmpzip.name, "w", zipfile.ZIP_DEFLATED) as zf:
                for pf in pages_files:
                    zf.write(pf, os.path.basename(pf))
            tmpzip.flush()
            tmpzip.seek(0)
            zip_data = open(tmpzip.name, "rb").read()
            st.download_button(
                label="📥 Descargar TODO en ZIP (300ppi)",
                data=zip_data,
                file_name="montaje_dtf_pages.zip",
                mime="application/zip"
            )

        # Limpiar temporales
        for pf in pages_files:
            os.remove(pf)
        os.rmdir(temp_dir)
