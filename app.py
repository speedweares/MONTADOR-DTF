
import streamlit as st
from PIL import Image
import math
from io import BytesIO
import zipfile
import tempfile
import os

st.set_page_config(page_title="Montador DTF con muchas copias", layout="wide")
st.title("🖨️ Montador DTF: Packing con muchas copias y páginas")

ROLL_WIDTH_CM = 55

# Usamos dos modalidades de resolución:
PPI_PREVIEW = 100  # para que la previsualización no explote memoria
PPI_FINAL = 300    # para la descarga definitiva
PX_PER_CM_PREVIEW = PPI_PREVIEW / 2.54
PX_PER_CM_FINAL = PPI_FINAL / 2.54

SPACING_CM = 1.5  # 1.5 cm de espacio para tijera
SPACING_PX_PREVIEW = int(SPACING_CM * PX_PER_CM_PREVIEW)
SPACING_PX_FINAL = int(SPACING_CM * PX_PER_CM_FINAL)

# Umbral para dividir en "páginas" (1 m en 300 ppi)
UMBRAL_PX_FINAL = int((100) * PX_PER_CM_FINAL)  # 100 cm * px_por_cm

# Desactivar el límite de BOMBS (imágenes grandes)
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

    if st.button("🧩 Generar montaje"):
        # 1) Preparamos la lista de "items" con la imagen ya redimensionada
        items = []
        preview_placements = []
        final_placements = []

        # Recorremos cada configuración
        for file, tipo_diseño, copias in configuraciones:
            try:
                img = Image.open(file).convert("RGBA")
            except Exception as e:
                st.error(f"Error cargando {file.name}: {e}")
                continue

            # Determinar ancho en cm según tipo
            if "Espalda" in tipo_diseño:
                ancho_cm = 22.5
            elif "5" in tipo_diseño:
                ancho_cm = 5
            else:
                ancho_cm = 7

            # Calcular px para preview y px para final
            w_px_preview = int(ancho_cm * PX_PER_CM_PREVIEW)
            h_px_preview = int((img.height / img.width) * w_px_preview)
            img_preview = img.resize((w_px_preview, h_px_preview), Image.LANCZOS)

            w_px_final = int(ancho_cm * PX_PER_CM_FINAL)
            h_px_final = int((img.height / img.width) * w_px_final)
            img_final = img.resize((w_px_final, h_px_final), Image.LANCZOS)

            # Añadimos la misma imagen tantas veces como "copias"
            for _ in range(copias):
                items.append((img_preview, img_final, w_px_preview, h_px_preview, w_px_final, h_px_final))

        # 2) Calculamos la colocación por filas para "preview" y para "final"
        roll_w_px_preview = int(ROLL_WIDTH_CM * PX_PER_CM_PREVIEW)
        roll_w_px_final = int(ROLL_WIDTH_CM * PX_PER_CM_FINAL)

        # Variables de estado para recorrer items
        cur_x_prev = 0
        cur_row_h_prev = 0
        y_offset_prev = 0

        cur_x_fin = 0
        cur_row_h_fin = 0
        y_offset_fin = 0

        # Lista de tuplas (img_preview, x_prev, y_prev), (img_final, x_fin, y_fin)
        for img_p, img_f, w_p, h_p, w_f, h_f in items:
            # --- COLOCACIÓN EN PREVIEW ---
            if cur_x_prev == 0:
                x_prev = 0
            else:
                if cur_x_prev + SPACING_PX_PREVIEW + w_p <= roll_w_px_preview:
                    x_prev = cur_x_prev + SPACING_PX_PREVIEW
                else:
                    # nueva fila en preview
                    y_offset_prev += cur_row_h_prev + SPACING_PX_PREVIEW
                    cur_x_prev = 0
                    cur_row_h_prev = 0
                    x_prev = 0

            preview_placements.append((img_p, x_prev, y_offset_prev, w_p, h_p))
            cur_x_prev = x_prev + w_p
            if h_p > cur_row_h_prev:
                cur_row_h_prev = h_p

            # --- COLOCACIÓN EN FINAL ---
            if cur_x_fin == 0:
                x_fin = 0
            else:
                if cur_x_fin + SPACING_PX_FINAL + w_f <= roll_w_px_final:
                    x_fin = cur_x_fin + SPACING_PX_FINAL
                else:
                    # nueva fila en final
                    y_offset_fin += cur_row_h_fin + SPACING_PX_FINAL
                    cur_x_fin = 0
                    cur_row_h_fin = 0
                    x_fin = 0

            final_placements.append((img_f, x_fin, y_offset_fin, w_f, h_f))
            cur_x_fin = x_fin + w_f
            if h_f > cur_row_h_fin:
                cur_row_h_fin = h_f

        # 3) Creamos lienzo de preview
        total_h_prev = y_offset_prev + cur_row_h_prev
        canvas_prev = Image.new("RGBA", (roll_w_px_preview, total_h_prev), (255, 255, 255, 0))
        for img_p, x_p, y_p, w_p, h_p in preview_placements:
            canvas_prev.paste(img_p, (x_p, y_p), img_p)

        st.success("✅ Vista previa generada (baja resolución).")
        st.image(canvas_prev, caption="👁️ Vista previa (PPI reducido)", use_column_width=True)

        # 4) Creamos “páginas” en resolución final (300 ppi) si superamos el umbral
        pages = []
        # Preparamos un “lienzo de trabajo” que va creciendo
        # pero cuando y + h_f > UMBRAL_PX_FINAL, guardamos la página y reiniciamos
        cur_page = Image.new("RGBA", (roll_w_px_final, UMBRAL_PX_FINAL), (255, 255, 255, 0))
        page_index = 1

        for (img_f, x_f, y_f, w_f, h_f) in final_placements:
            # Si esta copia excede el límite de la página actual:
            if y_f + h_f > (page_index * UMBRAL_PX_FINAL):
                # Guardamos la página actual
                pages.append(cur_page)
                # Creamos nueva página, y mudamos a la siguiente
                cur_page = Image.new("RGBA", (roll_w_px_final, UMBRAL_PX_FINAL), (255, 255, 255, 0))
                page_index += 1

            # Para calcular la posición dentro de la página actual:
            y_local = y_f - ((page_index - 1) * UMBRAL_PX_FINAL)
            cur_page.paste(img_f, (x_f, y_local), img_f)

        # Guardamos la última página parcial
        pages.append(cur_page)

        # 5) Mostramos datos finales y botón de descarga
        total_h_fin = y_offset_fin + cur_row_h_fin
        total_cm = total_h_fin / PX_PER_CM_FINAL
        total_m = total_cm / 100
        st.success(f"✅ Montaje FINAL preparado → Altura total: {total_cm:.1f} cm ({total_m:.2f} m)")
        st.write(f"• Se generaron **{len(pages)} página(s)** de {UMBRAL_PX_FINAL} px (~1 m a 300 ppi).")

        # Crear un ZIP en memoria con todas las páginas (PNG)
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
                label="📥 Descargar TODO en ZIP (imágenes 300ppi)",
                data=zip_data,
                file_name="montaje_dtf_pages.zip",
                mime="application/zip"
            )

        # Eliminar archivo temporal
        os.remove(tmpzip.name)
