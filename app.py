import re
import streamlit as st
from video_factory import make_video
from auto_visuals import script_to_images
from local_ai import configured, generate_images

st.set_page_config(page_title="mntage — AI Video Factory", page_icon="🎬", layout="centered")
st.title("🎬 mntage")
st.caption("Un script → visuels → voix française → montage MP4 vertical")
title = st.text_input("Titre", "Mon premier test IA")
script = st.text_area("Ton script", height=260, placeholder="Colle ton texte ici…")
voice = st.selectbox("Voix française", ["fr-FR-DeniseNeural", "fr-FR-HenriNeural"])
choices = ["Éco — cartes graphiques automatiques (gratuit, recommandé)"]
if configured():
    choices.append("IA locale — Stable Diffusion (CPU, lent)")
mode = st.selectbox("Moteur visuel", choices)
uploads = st.file_uploader("Images personnelles (optionnel)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
st.caption("Le mode IA locale apparaît uniquement après configuration du moteur et du modèle (README).")
if st.button("🎥 Générer mon MP4", type="primary", use_container_width=True):
    if not script.strip():
        st.error("Colle ton script avant de commencer.")
    else:
        try:
            with st.spinner("Création des scènes, de la voix et du montage…"):
                if uploads:
                    images = [u.getvalue() for u in uploads]
                elif mode.startswith("IA locale"):
                    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", script) if s.strip()]
                    prompts = [
                        "cinematic editorial illustration, no text, vertical composition, "
                        "high contrast, professional, " + s[:260]
                        for s in sentences[:6]
                    ]
                    images = generate_images(prompts, backend="cpu", steps=12)
                else:
                    images = script_to_images(script, title)
                path = make_video(title, script, images, voice)
            st.success("Vidéo générée : vérifie-la avant publication.")
            st.video(str(path))
            with open(path, "rb") as handle:
                st.download_button("Télécharger le MP4", handle, file_name=path.name,
                                   mime="video/mp4", use_container_width=True)
        except Exception as exc:
            st.error(f"Erreur : {exc}")
