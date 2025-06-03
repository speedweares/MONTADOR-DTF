
import streamlit as st
from PIL import Image
import math
from io import BytesIO

st.set_page_config(page_title="Montador DTF - Varios Diseños", layout="wide")
st.title("🖨️ Montador DTF con múltiples diseños cargados a la vez")

ROLL_WIDTH_CM = 55
PPI = 300
PX_PER_CM = PPI / 2.54
SEPARACION_ENTRE_BLOQUES_CM = 5
SEPARACION_ENTRE_BLOQUES_PX = int(SEPARACION_ENTRE_BLOQUES_CM * PX_PER_CM)
SEPARACION_ENTRE_COPIAS_CM = 1
SEPARACION_ENTRE_COPIAS_PX = int(SEPARACION_ENTRE_COPIAS_CM * PX_PER_CM)

uploaded_files = st.file_uploader("Sube varios diseños (PNG, JPG)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    config = []
    st.markdown("### 📋 Configura cada diseño")
    for i, file in enumerate(uploaded_files):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            tipo = st.selectbox(f"Tipo diseño {i+1}", ["Espalda (22.5 cm)", "Frontal (5 cm)", "Frontal (7 cm)"], key=f"tipo_{i}")
        with col2:
            copias = st.number_input(f"Copias para diseño {i+1}", min_value=1, value=5, key=f"copias_{i}")
        with col3:
            st.image(file, width=80)
        config.append((file, tipo, copias))

    if st.button("🧩 Generar montaje"):
        bloques = []

        for file, tipo_diseño, copias in config:
            image = Image.open(file).convert("RGBA")
            if "Espalda" in tipo_diseño:
                ancho_cm = 22.5
            elif "5" in tipo_diseño:
                ancho_cm = 5
            else:
                ancho_cm = 7

            aspect_ratio = image.height / image.width
            ancho_px = int(ancho_cm * PX_PER_CM)
            alto_px = int(ancho_px * aspect_ratio)
            img_resized = image.resize((ancho_px, alto_px))

            por_fila = math.floor(ROLL_WIDTH_CM / ancho_cm)
            filas = math.ceil(copias / por_fila)

            canvas_w_px = int(ROLL_WIDTH_CM * PX_PER_CM)
            canvas_h_px = filas * (alto_px + SEPARACION_ENTRE_COPIAS_PX)

            bloque = Image.new("RGBA", (canvas_w_px, canvas_h_px), (255, 255, 255, 0))
            for i in range(copias):
                fila = i // por_fila
                col = i % por_fila
                x = col * (ancho_px + SEPARACION_ENTRE_COPIAS_PX)
                y = fila * (alto_px + SEPARACION_ENTRE_COPIAS_PX)
                bloque.paste(img_resized, (x, y), img_resized)

            bloques.append(bloque)

        total_width = bloques[0].width
        total_height = sum(b.height for b in bloques) + SEPARACION_ENTRE_BLOQUES_PX * (len(bloques) - 1)
        final_img = Image.new("RGBA", (total_width, total_height), (255, 255, 255, 0))

        y_offset = 0
        for b in bloques:
            final_img.paste(b, (0, y_offset), b)
            y_offset += b.height + SEPARACION_ENTRE_BLOQUES_PX

        metros = total_height / PX_PER_CM / 100
        st.success(f"✅ Montaje generado — Altura total: {metros:.2f} m")
        st.image(final_img, caption="🖼️ Montaje final", use_column_width=True)

        img_bytes = BytesIO()
        final_img.save(img_bytes, format="PNG")
        st.download_button(
            label="📥 Descargar montaje final",
            data=img_bytes.getvalue(),
            file_name="montaje_dtf_multi.png",
            mime="image/png"
        )
