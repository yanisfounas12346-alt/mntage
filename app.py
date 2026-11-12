import re
import streamlit as st
from video_factory import make_video
from auto_visuals import script_to_images
from local_ai import configured, generate_images

st.set_page_config(page_title="mntage | Studio vidéo", page_icon="🎬", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""
<style>
:root {color-scheme:dark}
.stApp {background:radial-gradient(circle at 50% 0%, #351015 0%, #120d10 42%, #0c0b0d 100%);color:#f8f4f5}
.block-container {max-width:820px;padding-top:2rem;padding-bottom:4rem}
header[data-testid="stHeader"] {background:transparent}
h1,h2,h3 {color:#fff !important;letter-spacing:-.035em}
div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea {
 background:#21191d;color:#fff;border:1px solid #503037;border-radius:12px;
}
div[data-testid="stTextInput"] input:focus,div[data-testid="stTextArea"] textarea:focus {border-color:#fa4159;box-shadow:0 0 0 1px #fa4159}
.stButton > button[kind="primary"] {background:linear-gradient(105deg,#f12b48,#bd1736);border:0;border-radius:12px;font-size:1.08rem;font-weight:750;min-height:3.5rem;box-shadow:0 8px 24px #a713303f}
.stButton > button[kind="primary"]:hover {background:linear-gradient(105deg,#ff4962,#d61b40)}
div[data-testid="stFileUploader"], div[data-testid="stExpander"] {border-radius:12px}
.hero {border:1px solid #5c2532;border-radius:20px;padding:24px 26px;background:linear-gradient(125deg,#32131d,#191116);margin-bottom:24px}
.eyebrow {font-size:.78rem;letter-spacing:.18em;font-weight:800;color:#ff6b80;margin-bottom:8px}
.hero-title {font-size:2rem;font-weight:850;line-height:1.1;color:#fff}
.hero-sub {margin-top:12px;color:#d5bfc6;line-height:1.5}
.step {font-size:.8rem;color:#ff8293;font-weight:750;text-transform:uppercase;letter-spacing:.09em;margin:16px 0 8px}
.small-note {color:#beaeb3;font-size:.87rem}
</style>
""", unsafe_allow_html=True)

st.markdown("""<div class="hero"><div class="eyebrow">MNTAGE / STUDIO IA</div>
<div class="hero-title">Ton script. Ta vidéo.<br>Un seul clic.</div>
<div class="hero-sub">Crée un Short vertical avec voix française, visuels animés et sous-titres. Sans abonnement GPU obligatoire.</div></div>""", unsafe_allow_html=True)

st.markdown('<div class="step">01 · Ton contenu</div>', unsafe_allow_html=True)
title = st.text_input("Titre de la vidéo", "Mon premier test IA")
script = st.text_area("Script à raconter", height=240, placeholder="Colle ton script ici…", help="Le logiciel créera automatiquement les visuels et la narration.")
words = len(script.split())
st.caption(f"{words} mots · durée indicative : {round(words / 2.5)} secondes")

with st.expander("⚙️ Options avancées (facultatives)", expanded=False):
    voice = st.selectbox("Voix", ["fr-FR-DeniseNeural", "fr-FR-HenriNeural"])
    modes = ["Éco — visuels graphiques automatiques"]
    if configured():
        modes.append("IA locale — Stable Diffusion (CPU lent)")
    mode = st.selectbox("Moteur visuel", modes)
    captions = st.checkbox("Sous-titres automatiques (timing estimé)", value=True)
    music = st.file_uploader("Musique MP3 (avec droits)", type=["mp3"])
    uploads = st.file_uploader("Mes propres images (facultatif)", type=["jpg","jpeg","png"], accept_multiple_files=True)

st.markdown('<div class="step">02 · Génération</div>', unsafe_allow_html=True)
st.markdown('<div class="small-note">Les images sont créées automatiquement si tu n’en ajoutes pas. Le mode Éco ne nécessite aucun GPU dédié.</div>', unsafe_allow_html=True)
if st.button("🎬 Créer ma vidéo", type="primary", use_container_width=True):
    if not script.strip():
        st.warning("Ajoute d'abord ton script.")
    else:
        try:
            with st.spinner("Création des scènes, de la narration et du montage…"):
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
            st.success("Vidéo prête ! Vérifie-la avant de publier.")
            st.markdown('<div class="step">03 · Résultat</div>', unsafe_allow_html=True)
            st.video(str(path))
            with open(path, "rb") as handle:
                st.download_button("⬇️ Télécharger le MP4", handle, file_name=path.name, mime="video/mp4", use_container_width=True)
            if captions:
                srt = path.with_suffix(".srt")
                st.download_button("Télécharger les sous-titres SRT", srt.read_bytes(), file_name=srt.name)
        except Exception as exc:
            st.error(f"Impossible de générer la vidéo : {exc}")
