
import streamlit as st
from PIL import Image
import math
from io import BytesIO

st.set_page_config(page_title="Montador DTF Single Enhanced", layout="wide")
st.title("🖨️ Montador DTF - Single Roll Mejorado")

ROLL_WIDTH_CM = 55
PPI_PREVIEW = 100
PPI_FINAL = 300
PX_PER_CM_PREVIEW = PPI_PREVIEW / 2.54
PX_PER_CM_FINAL = PPI_FINAL / 2.54

SPACING_CM = 0.5
SPACING_PX_PREVIEW = int(SPACING_CM * PX_PER_CM_PREVIEW)
SPACING_PX_FINAL = int(SPACING_CM * PX_PER_CM_FINAL)

# Desactivar límite BOMBS
Image.MAX_IMAGE_PIXELS = None

uploaded_files = st.file_uploader(
    "Sube varios diseños (PNG, JPG)", type=["png", "jpg", "jpeg"], accept_multiple_files=True
)

if not uploaded_files:
    st.info("📥 Sube al menos un archivo para comenzar.")
    st.stop()

st.markdown("### Configura cada diseño")
configuraciones = []
total_copias = 0
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
            f"Copias diseño {i+1}", min_value=1, value=5, key=f"copias_{i}"
        )
    with col3:
        st.image(file, width=80)
    # Leer imagen y hacer crop
    img = Image.open(file).convert("RGBA")
    alpha = img.split()[3]
    bbox = alpha.getbbox()
    if bbox:
        img = img.crop(bbox)
    # Guardar cropped base y tipo y copias
    configuraciones.append((img, tipo, copias))
    total_copias += copias

st.markdown(f"**Total copias:** {total_copias:,}")

# Decide preview
UMBRAL_PREVIEW = 100  # preview threshold
show_preview = total_copias <= UMBRAL_PREVIEW
if not show_preview:
    st.warning("⚠️ Más de 100 copias: omitir vista previa gráfica.")

if st.button("🧩 Generar montaje"):
    # First pass: compute positions
    positions = []  # list of tuples (config_index, x, y, w_f, h_f, w_p, h_p)
    cur_x_fin = 0; cur_row_h_fin = 0; y_off_fin = 0
    cur_x_prev = 0; cur_row_h_prev = 0; y_off_prev = 0
    roll_width_px_fin = int(ROLL_WIDTH_CM * PX_PER_CM_FINAL)
    roll_width_px_prev = int(ROLL_WIDTH_CM * PX_PER_CM_PREVIEW)
    # iterate configs
    for idx, (img, tipo, copias) in enumerate(configuraciones):
        # determine ancho_cm
        if "Espalda" in tipo:
            ancho_cm = 27.5
        elif "5" in tipo:
            ancho_cm = 5.0
        else:
            ancho_cm = 7.0
        # compute base dimensions
        w_base, h_base = img.size
        # final dims
        w_f = int(ancho_cm * PX_PER_CM_FINAL)
        h_f = int(h_base / w_base * w_f)
        # preview dims
        w_p = int(ancho_cm * PX_PER_CM_PREVIEW)
        h_p = int(h_base / w_base * w_p)
        for _ in range(copias):
            # compute final pos
            if cur_x_fin == 0:
                x_f = 0
            else:
                if cur_x_fin + SPACING_PX_FINAL + w_f <= roll_width_px_fin:
                    x_f = cur_x_fin + SPACING_PX_FINAL
                else:
                    y_off_fin += cur_row_h_fin + SPACING_PX_FINAL
                    cur_x_fin = 0; cur_row_h_fin = 0
                    x_f = 0
            # update row height
            if h_f > cur_row_h_fin: cur_row_h_fin = h_f
            # compute preview pos if needed
            if show_preview:
                if cur_x_prev == 0:
                    x_p = 0
                else:
                    if cur_x_prev + SPACING_PX_PREVIEW + w_p <= roll_width_px_prev:
                        x_p = cur_x_prev + SPACING_PX_PREVIEW
                    else:
                        y_off_prev += cur_row_h_prev + SPACING_PX_PREVIEW
                        cur_x_prev = 0; cur_row_h_prev = 0
                        x_p = 0
                if h_p > cur_row_h_prev: cur_row_h_prev = h_p
            else:
                x_p = None; h_p = None; y_off_prev = None
            # record position
            positions.append((idx, x_f, y_off_fin, w_f, h_f, x_p, y_off_prev, w_p, h_p))
            # update offsets
            cur_x_fin = x_f + w_f
            if show_preview:
                cur_x_prev = x_p + w_p

    # compute total final height
    total_h_fin = y_off_fin + cur_row_h_fin
    total_h_prev = y_off_prev + cur_row_h_prev if show_preview else 0

    # create preview canvas
    if show_preview:
        canvas_prev = Image.new("RGBA", (roll_width_px_prev, total_h_prev), (255,255,255,0))
        for idx, x_f, y_f, w_f, h_f, x_p, y_p, w_p, h_p in positions:
            base_img = configuraciones[idx][0]
            img_resized_p = base_img.resize((w_p, h_p), Image.LANCZOS)
            canvas_prev.paste(img_resized_p, (x_p, y_p), img_resized_p)
        st.success("✅ Vista previa generada")
        st.image(canvas_prev, use_column_width=True)

    # create final canvas
    canvas_fin = Image.new("RGBA", (roll_width_px_fin, total_h_fin), (255,255,255,0))
    for idx, x_f, y_f, w_f, h_f, *_ in positions:
        base_img = configuraciones[idx][0]
        img_resized_f = base_img.resize((w_f, h_f), Image.LANCZOS)
        canvas_fin.paste(img_resized_f, (x_f, y_f), img_resized_f)
    st.success(f"✅ Montaje final: largo {total_h_fin / PX_PER_CM_FINAL:.1f} cm")
    st.image(canvas_fin, use_column_width=True)

    # download final
    buffer = BytesIO()
    canvas_fin.save(buffer, format="PNG")
    st.download_button("📥 Descargar PNG final", data=buffer.getvalue(), file_name="montaje_dtf.png", mime="image/png")
