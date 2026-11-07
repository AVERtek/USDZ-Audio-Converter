import os
import zipfile
import shutil
import tempfile
import streamlit as st

# --- Core Packer Logic ---
class ARAudioPacker:
    def __init__(self, model_path: str, audio_path: str, output_path: str):
        self.model_path = model_path
        self.audio_path = audio_path
        self.output_path = output_path

    def process_usdz(self, audio_spatial_position=(0, 0, 0)):
        audio_filename = os.path.basename(self.audio_path)
        temp_dir = tempfile.mkdtemp()
        
        try:
            base_name = os.path.splitext(os.path.basename(self.model_path))[0]
            usda_path = os.path.join(temp_dir, f"{base_name}.usda")
            
            if self.model_path.endswith('.usdz'):
                with zipfile.ZipFile(self.model_path, 'r') as zf:
                    zf.extractall(temp_dir)
            else:
                shutil.copy(self.model_path, usda_path)

            shutil.copy(self.audio_path, os.path.join(temp_dir, audio_filename))

            target_usda = None
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.usda'):
                        target_usda = os.path.join(root, file)
                        break

            if target_usda:
                with open(target_usda, 'r', encoding='utf-8') as f:
                    content = f.read()

                audio_snippet = f"""
                def Xform "AudioEmitter" (
                    prepend apiSchemas = ["Preliminary_AudioAPI"]
                ) {{
                    rel preliminary:audio:amplitude = 1.0
                    rel preliminary:audio:filePath = @{audio_filename}@
                    bool preliminary:audio:loop = true
                    double3 xformOp:translate = ({audio_spatial_position[0]}, {audio_spatial_position[1]}, {audio_spatial_position[2]})
                    uniform token[] xformOpOrder = ["xformOp:translate"]
                }}
                """
                content += audio_snippet

                with open(target_usda, 'w', encoding='utf-8') as f:
                    f.write(content)

            with zipfile.ZipFile(self.output_path, 'w', zipfile.ZIP_STORED) as usdz:
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        usdz.write(file_path, arcname)

        finally:
            shutil.rmtree(temp_dir)

# --- Streamlit User Interface ---
st.set_page_config(page_title="AR Audio Embedder", page_icon="🎧", layout="centered")

st.title("🎧 AR Audio Embedder for USDZ")
st.markdown("Upload your 3D model (`.usdz`) and an audio file (`.mp3` or `.wav`) to bundle them together for Apple AR Quick Look.")

# File upload boxes
col1, col2 = st.columns(2)
with col1:
    uploaded_usdz = st.file_uploader("Upload USDZ Model", type=["usdz"])
with col2:
    uploaded_audio = st.file_uploader("Upload Audio File", type=["mp3", "wav", "m4a"])

# Spatial positioning settings in an expandable section
with st.expander("Advanced: Audio Position (X, Y, Z)"):
    pos_x = st.slider("X Position", -5.0, 5.0, 0.0)
    pos_y = st.slider("Y Position", -5.0, 5.0, 0.5)
    pos_z = st.slider("Z Position", -5.0, 5.0, 0.0)

if st.button("Generate Audio-Enabled USDZ", type="primary", use_container_width=True):
    if uploaded_usdz is not None and uploaded_audio is not None:
        with st.spinner("Processing files and embedding audio..."):
            # Create a temporary directory to handle uploaded files safely
            with tempfile.TemporaryDirectory() as tmpdirname:
                input_usdz_path = os.path.join(tmpdirname, uploaded_usdz.name)
                with open(input_usdz_path, "wb") as f:
                    f.write(uploaded_usdz.getbuffer())

                input_audio_path = os.path.join(tmpdirname, uploaded_audio.name)
                with open(input_audio_path, "wb") as f:
                    f.write(uploaded_audio.getbuffer())

                output_filename = f"audio_{uploaded_usdz.name}"
                output_usdz_path = os.path.join(tmpdirname, output_filename)

                # Run packer
                packer = ARAudioPacker(input_usdz_path, input_audio_path, output_usdz_path)
                packer.process_usdz(audio_spatial_position=(pos_x, pos_y, pos_z))

                # Read output file into memory for download button
                with open(output_usdz_path, "rb") as f:
                    usdz_bytes = f.read()

            st.success("Success! Your audio-enabled USDZ file is ready.")
            st.download_button(
                label="📥 Download Output USDZ",
                data=usdz_bytes,
                file_name=output_filename,
                mime="model/vnd.usdz+zip",
                use_container_width=True
            )
    else:
        st.warning("Please upload both a USDZ file and an audio file before generating.")
