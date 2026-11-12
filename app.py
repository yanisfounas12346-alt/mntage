import streamlit as st
from video_factory import make_video

st.set_page_config(page_title="mntage — AI Video Factory", page_icon="🎬", layout="centered")
st.title("🎬 mntage")
st.caption("Studio vidéo vertical léger • 1080 × 1920 • export YouTube")
title = st.text_input("Titre de la vidéo", "Mon premier test IA")
script = st.text_area("Script à narrer", height=200, placeholder="Écris ici le texte de la voix off…")
voice = st.selectbox("Voix française", ["fr-FR-DeniseNeural", "fr-FR-HenriNeural"])
uploads = st.file_uploader("Images (JPG/PNG, dans l'ordre des scènes)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
st.info("MVP : animation légère des images + voix off. Les scènes vidéo IA cloud seront ajoutées ensuite.")
if st.button("🎥 Générer mon MP4", type="primary", use_container_width=True):
    if not script.strip() or not uploads:
        st.error("Ajoute un script et au moins une image.")
    else:
        try:
            with st.spinner("Génération audio et montage vidéo…"):
                path = make_video(title, script, [u.getvalue() for u in uploads], voice)
            st.success(f"Vidéo prête : {path}")
            st.video(str(path))
            with open(path, "rb") as handle:
                st.download_button("Télécharger le MP4", handle, file_name=path.name, mime="video/mp4", use_container_width=True)
            st.caption("Pour l'upload YouTube OAuth, suis le README (publication privée par défaut).")
        except Exception as exc:
            st.error(f"Échec de génération : {exc}")
