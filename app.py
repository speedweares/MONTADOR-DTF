
import streamlit as st
from PIL import Image
import math
from io import BytesIO

st.set_page_config(page_title="Montador DTF", layout="wide")
st.title("🖨️ Montador Automático para DTF (55 cm ancho)")

ROLL_WIDTH_CM = 55
PPI = 300
PX_PER_CM = PPI / 2.54

uploaded_file = st.file_uploader("Sube tu diseño (PNG, JPG)", type=["png", "jpg", "jpeg"])
if uploaded_file:
    image = Image.open(uploaded_file).convert("RGBA")
    st.image(image, caption="Diseño original", width=300)

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
        copias = st.number_input("¿Cuántas copias deseas?", min_value=1, value=10)

    # Redimensionar imagen manteniendo aspecto
    orig_w, orig_h = image.size
    aspect_ratio = orig_h / orig_w
    target_w_px = int(target_width_cm * PX_PER_CM)
    target_h_px = int(target_w_px * aspect_ratio)
    resized_img = image.resize((target_w_px, target_h_px))

    diseños_por_fila = math.floor(ROLL_WIDTH_CM / target_width_cm)
    filas = math.ceil(copias / diseños_por_fila)
    alto_total_cm = filas * (target_h_px / PX_PER_CM)
    alto_total_m = alto_total_cm / 100

    st.markdown(f"📏 **Alto total necesario:** `{alto_total_cm:.1f} cm` → `{alto_total_m:.2f} m`")

    canvas_w_px = int(ROLL_WIDTH_CM * PX_PER_CM)
    canvas_h_px = filas * target_h_px
    montage = Image.new("RGBA", (canvas_w_px, canvas_h_px), (255, 255, 255, 0))

    for i in range(copias):
        fila = i // diseños_por_fila
        col = i % diseños_por_fila
        x = col * target_w_px
        y = fila * target_h_px
        montage.paste(resized_img, (x, y), resized_img)

    st.image(montage, caption="🖼️ Montaje generado", use_column_width=True)

    img_bytes = BytesIO()
    montage.save(img_bytes, format="PNG")
    st.download_button(
        label="📥 Descargar montaje (PNG transparente)",
        data=img_bytes.getvalue(),
        file_name="montaje_dtf.png",
        mime="image/png"
    )
