import streamlit as st
from video_factory import make_video
from auto_visuals import script_to_images

st.set_page_config(page_title="mntage — AI Video Factory", page_icon="🎬", layout="centered")
st.title("🎬 mntage")
st.caption("Écris ton script → génère automatiquement une vidéo verticale")
title = st.text_input("Titre de la vidéo", "Mon premier test IA")
script = st.text_area("Ton script (seule saisie nécessaire)", height=260, placeholder="Colle ton script ici…")
voice = st.selectbox("Voix française", ["fr-FR-DeniseNeural", "fr-FR-HenriNeural"])
st.caption("Mode gratuit : visuels graphiques originaux générés automatiquement, voix Edge TTS et montage FFmpeg. Aucune image à fournir.")
uploads = st.file_uploader("Optionnel : remplacer les visuels par tes images", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
if st.button("🎥 Générer automatiquement mon MP4", type="primary", use_container_width=True):
    if not script.strip():
        st.error("Colle d'abord ton script.")
    else:
        try:
            with st.spinner("Création des scènes, narration et montage…"):
                images = [u.getvalue() for u in uploads] if uploads else script_to_images(script, title)
                path = make_video(title, script, images, voice)
            st.success("Vidéo prête. Vérifie le rendu avant toute publication.")
            st.video(str(path))
            with open(path, "rb") as handle:
                st.download_button("Télécharger le MP4", handle, file_name=path.name, mime="video/mp4", use_container_width=True)
            st.caption("Upload YouTube privé disponible via youtube_upload.py (voir README).")
        except Exception as exc:
            st.error(f"Échec de génération : {exc}")
