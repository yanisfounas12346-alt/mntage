import re
import streamlit as st
from video_factory import make_video
from auto_visuals import script_to_images
from local_ai import configured, generate_images

st.set_page_config(page_title="mntage — AI Video Factory", page_icon="🎬", layout="centered")
st.title("🎬 mntage")
st.caption("Un script → images → narration → sous-titres → montage MP4")
title = st.text_input("Titre", "Mon premier test IA")
script = st.text_area("Ton script", height=240, placeholder="Colle ton texte ici…")
voice = st.selectbox("Voix française", ["fr-FR-DeniseNeural", "fr-FR-HenriNeural"])
modes = ["Éco — visuels automatiques (gratuit)"]
if configured():
    modes.append("IA locale — Stable Diffusion (CPU lent)")
mode = st.selectbox("Moteur visuel", modes)
captions = st.checkbox("Ajouter des sous-titres automatiques (timing estimé)", value=True)
music = st.file_uploader("Musique de fond MP3 (facultative, avec droits)", type=["mp3"])
uploads = st.file_uploader("Images personnelles (facultatives)", type=["jpg","jpeg","png"], accept_multiple_files=True)
if st.button("🎥 Générer mon MP4", type="primary", use_container_width=True):
    if not script.strip():
        st.error("Colle ton script.")
    else:
        try:
            with st.spinner("Production en cours…"):
                if uploads:
                    images = [u.getvalue() for u in uploads]
                elif mode.startswith("IA locale"):
                    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", script) if s.strip()]
                    prompts = ["cinematic editorial illustration, no text, vertical composition, "+s[:250] for s in sentences[:6]]
                    images = generate_images(prompts, backend="cpu", steps=12)
                else:
                    images = script_to_images(script, title)
                path = make_video(title, script, images, voice, captions=captions,
                                  music=music.getvalue() if music else None)
            st.success("MP4 prêt — vérifie-le avant publication.")
            st.video(str(path))
            with open(path,"rb") as handle:
                st.download_button("Télécharger le MP4",handle,file_name=path.name,mime="video/mp4",use_container_width=True)
            if captions:
                srt = path.with_suffix(".srt")
                st.download_button("Télécharger les sous-titres SRT",srt.read_bytes(),file_name=srt.name)
        except Exception as exc:
            st.error(f"Erreur : {exc}")
