
import streamlit as st
from PIL import Image
import cv2
import numpy as np
import math
from io import BytesIO

st.set_page_config(page_title="Montador DTF Single Roll", layout="wide")
st.title("🖨️ Montador DTF - Una sola hoja continua")

ROLL_WIDTH_CM = 55

# Resolutions
PPI_PREVIEW = 100
PPI_FINAL = 300
PX_PER_CM_PREVIEW = PPI_PREVIEW / 2.54
PX_PER_CM_FINAL = PPI_FINAL / 2.54

# Espaciado 0.5 cm
SPACING_CM = 0.5
SPACING_PX_PREVIEW = int(SPACING_CM * PX_PER_CM_PREVIEW)
SPACING_PX_FINAL = int(SPACING_CM * PX_PER_CM_FINAL)

# Desactivar límite BOMBS
Image.MAX_IMAGE_PIXELS = None

uploaded_files = st.file_uploader(
    "1) Sube varios diseños (PNG, JPG)", 
    type=["png", "jpg", "jpeg"], 
    accept_multiple_files=True
)

if uploaded_files:
    st.markdown("### 2) Configura cada diseño")
    configuraciones = []
    total_copias = 0
    for i, file in enumerate(uploaded_files):
        col1, col2, col3 = st.columns([2,2,1])
        with col1:
            tipo = st.selectbox(
                f"Tipo diseño #{i+1}",
                ["Espalda (22.5 cm)", "Frontal (5 cm)", "Frontal (7 cm)"],
                key=f"tipo_{i}"
            )
        with col2:
            copias = st.number_input(
                f"Copias diseño #{i+1}",
                min_value=1, value=10, key=f"copias_{i}"
            )
        with col3:
            st.image(file, width=80)
        configuraciones.append((file, tipo, copias))
        total_copias += copias

    if st.button("🧩 Generar montaje"):
        # Prepare items with dimensions for preview and final
        preview_items = []
        final_items = []
        # Roll width in pixels
        roll_w_px_preview = int(ROLL_WIDTH_CM * PX_PER_CM_PREVIEW)
        roll_w_px_final = int(ROLL_WIDTH_CM * PX_PER_CM_FINAL)

        y_offset_prev = 0
        cur_x_prev = 0
        cur_row_h_prev = 0

        # First, process each design and accumulate placement info
        for file, tipo, copias in configuraciones:
            # Load and crop transparent area using PIL for simplicity
            img = Image.open(file).convert("RGBA")
            alpha = img.split()[3]
            bbox = alpha.getbbox()
            if bbox:
                img = img.crop(bbox)
            # Determine width cm
            if "Espalda" in tipo:
                width_cm = 22.5
            elif "5" in tipo:
                width_cm = 5
            else:
                width_cm = 7
            # Preview dimensions
            w_px_prev = int(width_cm * PX_PER_CM_PREVIEW)
            h_px_prev = int((img.height / img.width) * w_px_prev)
            img_prev = img.resize((w_px_prev, h_px_prev), Image.LANCZOS)
            # Final dimensions
            w_px_fin = int(width_cm * PX_PER_CM_FINAL)
            h_px_fin = int((img.height / img.width) * w_px_fin)
            img_fin = img.resize((w_px_fin, h_px_fin), Image.LANCZOS)
            # Add each copy
            for _ in range(copias):
                # Preview placement
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
                preview_items.append((img_prev, x_prev, y_offset_prev))
                cur_x_prev = x_prev + w_px_prev
                if h_px_prev > cur_row_h_prev:
                    cur_row_h_prev = h_px_prev
                # Final placement
                final_items.append((img_fin, w_px_fin, h_px_fin))  # will place sequentially by scanning

        # Create preview canvas
        total_h_prev = y_offset_prev + cur_row_h_prev
        canvas_prev = Image.new("RGBA", (roll_w_px_preview, total_h_prev), (255,255,255,0))
        for img_prev, x_prev, y_prev in preview_items:
            canvas_prev.paste(img_prev, (x_prev, y_prev), img_prev)
        st.success("✅ Vista previa generada")
        st.image(canvas_prev, caption="👁️ Vista previa (100 ppi)", use_column_width=True)

        # Create final single roll canvas
        # Compute total height: place items in rows
        y_offset_fin = 0
        cur_x_fin = 0
        cur_row_h_fin = 0
        # First pass: calculate total height
        placements_fin = []
        for img_fin, w_px_fin, h_px_fin in final_items:
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
            placements_fin.append((img_fin, x_fin, y_offset_fin))
            cur_x_fin = x_fin + w_px_fin
            if h_px_fin > cur_row_h_fin:
                cur_row_h_fin = h_px_fin
        total_h_fin = y_offset_fin + cur_row_h_fin
        canvas_fin = Image.new("RGBA", (roll_w_px_final, total_h_fin), (255,255,255,0))
        # Paste final placements
        for img_fin, x_fin, y_fin in placements_fin:
            canvas_fin.paste(img_fin, (x_fin, y_fin), img_fin)
        # Show measurement
        total_cm = total_h_fin / PX_PER_CM_FINAL
        total_m = total_cm / 100
        st.success(f"✅ Montaje FINAL largo = {total_cm:.1f} cm ({total_m:.2f} m)")
        # Provide download
        buf = BytesIO()
        canvas_fin.save(buf, format="PNG")
        st.download_button(
            label="📥 Descargar montaje completo (PNG 300ppi)",
            data=buf.getvalue(),
            file_name="montaje_dtf_single.png",
            mime="image/png"
        )
