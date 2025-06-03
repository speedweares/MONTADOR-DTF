
import streamlit as st
from PIL import Image
import math
from io import BytesIO

st.set_page_config(page_title="Montador DTF Múltiple", layout="wide")
st.title("🖨️ Montador DTF con múltiples diseños")

ROLL_WIDTH_CM = 55
PPI = 300
PX_PER_CM = PPI / 2.54
SEPARACION_ENTRE_BLOQUES_CM = 5
SEPARACION_ENTRE_BLOQUES_PX = int(SEPARACION_ENTRE_BLOQUES_CM * PX_PER_CM)

if "montaje_bloques" not in st.session_state:
    st.session_state.montaje_bloques = []

uploaded_file = st.file_uploader("Sube un diseño (PNG, JPG)", type=["png", "jpg", "jpeg"])
if uploaded_file:
    image = Image.open(uploaded_file).convert("RGBA")
    st.image(image, caption="Diseño cargado", width=250)

    col1, col2 = st.columns(2)
    with col1:
        tipo_diseño = st.selectbox("Tipo de diseño", ["Espalda (22.5 cm)", "Frontal (5 cm)", "Frontal (7 cm)"])
        if "Espalda" in tipo_diseño:
            target_width_cm = 22.5
        elif "5" in tipo_diseño:
            target_width_cm = 5
        else:
            target_width_cm = 7
    with col2:
        copias = st.number_input("¿Cuántas copias?", min_value=1, value=10)

    if st.button("➕ Agregar al montaje"):
        aspect_ratio = image.height / image.width
        target_w_px = int(target_width_cm * PX_PER_CM)
        target_h_px = int(target_w_px * aspect_ratio)
        resized_img = image.resize((target_w_px, target_h_px))

        por_fila = math.floor(ROLL_WIDTH_CM / target_width_cm)
        filas = math.ceil(copias / por_fila)

        canvas_w_px = int(ROLL_WIDTH_CM * PX_PER_CM)
        canvas_h_px = filas * (target_h_px + int(1 * PX_PER_CM))

        bloque = Image.new("RGBA", (canvas_w_px, canvas_h_px), (255, 255, 255, 0))
        for i in range(copias):
            fila = i // por_fila
            col = i % por_fila
            x = col * (target_w_px + int(1 * PX_PER_CM))
            y = fila * (target_h_px + int(1 * PX_PER_CM))
            bloque.paste(resized_img, (x, y), resized_img)

        st.session_state.montaje_bloques.append(bloque)
        st.success("✅ Diseño agregado correctamente.")

if st.button("🧩 Generar montaje final"):
    if not st.session_state.montaje_bloques:
        st.warning("Primero debes subir al menos un diseño.")
    else:
        total_width = st.session_state.montaje_bloques[0].width
        total_height = sum(img.height for img in st.session_state.montaje_bloques)
        total_height += SEPARACION_ENTRE_BLOQUES_PX * (len(st.session_state.montaje_bloques) - 1)

        montaje_final = Image.new("RGBA", (total_width, total_height), (255, 255, 255, 0))

        y_offset = 0
        for bloque in st.session_state.montaje_bloques:
            montaje_final.paste(bloque, (0, y_offset), bloque)
            y_offset += bloque.height + SEPARACION_ENTRE_BLOQUES_PX

        metros = total_height / PX_PER_CM / 100
        st.markdown(f"📐 **Altura total del montaje:** `{metros:.2f} m`")
        st.image(montaje_final, caption="🖼️ Montaje final generado", use_column_width=True)

        img_bytes = BytesIO()
        montaje_final.save(img_bytes, format="PNG")
        st.download_button(
            label="📥 Descargar montaje final",
            data=img_bytes.getvalue(),
            file_name="montaje_dtf_final.png",
            mime="image/png"
        )

if st.button("🔁 Reiniciar montaje"):
    st.session_state.montaje_bloques = []
    st.success("Montaje reiniciado.")
