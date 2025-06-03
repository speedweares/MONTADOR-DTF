
import streamlit as st
from PIL import Image
import math
from io import BytesIO

st.set_page_config(page_title="Montador DTF Single Roll 27.5", layout="wide")
st.title("🖨️ Montador DTF - Single Roll con Espaldas de 27.5 cm")

ROLL_WIDTH_CM = 55
PPI_PREVIEW = 100
PPI_FINAL = 300
PX_PER_CM_PREVIEW = PPI_PREVIEW / 2.54
PX_PER_CM_FINAL = PPI_FINAL / 2.54

# Espaciado de 0.5 cm entre copias
SPACING_CM = 0.5
SPACING_PX_PREVIEW = int(SPACING_CM * PX_PER_CM_PREVIEW)
SPACING_PX_FINAL = int(SPACING_CM * PX_PER_CM_FINAL)

# Desactivar límite BOMBS
Image.MAX_IMAGE_PIXELS = None

uploaded_files = st.file_uploader(
    "Sube varios diseños (PNG, JPG)", type=["png", "jpg", "jpeg"], accept_multiple_files=True
)

if uploaded_files:
    st.markdown("### Configura cada diseño")
    configuraciones = []
    for i, file in enumerate(uploaded_files):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            tipo = st.selectbox(
                f"Tipo diseño {i+1}",
                ["Espalda (27.5 cm)", "Frontal (5 cm)", "Frontal (7 cm)"],
                key=f"tipo_{i}"
            )
        with col2:
            copias = st.number_input(
                f"Copias para diseño {i+1}", min_value=1, value=5, key=f"copias_{i}"
            )
        with col3:
            st.image(file, width=80)
        configuraciones.append((file, tipo, copias))

    if st.button("🧩 Generar montaje"):
        # Calcular lista de items
        items = []
        for file, tipo_diseño, copias in configuraciones:
            image = Image.open(file).convert("RGBA")
            # Crop de transparencia
            alpha = image.split()[3]
            bbox = alpha.getbbox()
            if bbox:
                image = image.crop(bbox)
            # Ancho según tipo
            if "Espalda" in tipo_diseño:
                ancho_cm = 27.5
            elif "5 cm" in tipo_diseño:
                ancho_cm = 5
            else:
                ancho_cm = 7
            # Tamaño preview
            ancho_px_prev = int(ancho_cm * PX_PER_CM_PREVIEW)
            alto_px_prev = int((image.height / image.width) * ancho_px_prev)
            img_prev = image.resize((ancho_px_prev, alto_px_prev), Image.LANCZOS)
            # Tamaño final
            ancho_px_fin = int(ancho_cm * PX_PER_CM_FINAL)
            alto_px_fin = int((image.height / image.width) * ancho_px_fin)
            img_fin = image.resize((ancho_px_fin, alto_px_fin), Image.LANCZOS)
            for _ in range(copias):
                items.append((img_prev, img_fin, ancho_px_prev, alto_px_prev, ancho_px_fin, alto_px_fin))

        # Packing en un rollo continuo
        roll_w_px_prev = int(ROLL_WIDTH_CM * PX_PER_CM_PREVIEW)
        roll_w_px_fin = int(ROLL_WIDTH_CM * PX_PER_CM_FINAL)

        # Colocaciones
        prev_placements = []
        fin_placements = []
        cur_x_prev = 0; cur_row_h_prev = 0; y_off_prev = 0
        cur_x_fin = 0; cur_row_h_fin = 0; y_off_fin = 0

        for img_p, img_f, w_p, h_p, w_f, h_f in items:
            # Preview
            if cur_x_prev == 0:
                x_p = 0
            else:
                if cur_x_prev + SPACING_PX_PREVIEW + w_p <= roll_w_px_prev:
                    x_p = cur_x_prev + SPACING_PX_PREVIEW
                else:
                    y_off_prev += cur_row_h_prev + SPACING_PX_PREVIEW
                    cur_x_prev = 0; cur_row_h_prev = 0
                    x_p = 0
            prev_placements.append((img_p, x_p, y_off_prev))
            cur_x_prev = x_p + w_p
            if h_p > cur_row_h_prev: cur_row_h_prev = h_p
            # Final
            if cur_x_fin == 0:
                x_f = 0
            else:
                if cur_x_fin + SPACING_PX_FINAL + w_f <= roll_w_px_fin:
                    x_f = cur_x_fin + SPACING_PX_FINAL
                else:
                    y_off_fin += cur_row_h_fin + SPACING_PX_FINAL
                    cur_x_fin = 0; cur_row_h_fin = 0
                    x_f = 0
            fin_placements.append((img_f, x_f, y_off_fin))
            cur_x_fin = x_f + w_f
            if h_f > cur_row_h_fin: cur_row_h_fin = h_f

        # Crear canvas preview
        total_h_prev = y_off_prev + cur_row_h_prev
        canvas_prev = Image.new("RGBA", (roll_w_px_prev, total_h_prev), (255,255,255,0))
        for img_p, x_p, y_p in prev_placements:
            canvas_prev.paste(img_p, (x_p,y_p), img_p)
        st.success("✅ Vista previa generada")
        st.image(canvas_prev, use_column_width=True)

        # Canvas final único
        total_h_fin = y_off_fin + cur_row_h_fin
        canvas_fin = Image.new("RGBA", (roll_w_px_fin, total_h_fin), (255,255,255,0))
        for img_f, x_f, y_f in fin_placements:
            canvas_fin.paste(img_f, (x_f,y_f), img_f)
        st.success(f"✅ Montaje final: {total_h_fin/ (PX_PER_CM_FINAL):.1f} cm de largo")
        st.image(canvas_fin, use_column_width=True)

        # Descargar final
        bytes_io = BytesIO()
        canvas_fin.save(bytes_io, format="PNG")
        st.download_button("📥 Descargar PNG final", data=bytes_io.getvalue(), file_name="montaje_dtf.png", mime="image/png")
