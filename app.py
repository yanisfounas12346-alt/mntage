import os
import re
from pathlib import Path
import streamlit as st
from video_factory import make_video
from auto_visuals import script_to_images
from local_ai import configured, generate_images
from job_store import enqueue, jobs, next_job, finish, update_metrics, set_youtube
from stock_media import search_images, download_images, search_videos, download_videos, scene_queries

st.set_page_config(page_title="mntage | Studio vidéo",page_icon="🎬",layout="centered",initial_sidebar_state="collapsed")
st.markdown("""
<style>
.stApp{background:radial-gradient(circle at 50% 0%,#39141e,#130d11 48%,#0d0b0d);color:#f9f5f6}
.block-container{max-width:850px;padding-top:2rem}
header[data-testid="stHeader"]{background:transparent}
h1,h2,h3{color:#fff!important}
.stButton>button[kind="primary"]{background:linear-gradient(110deg,#f33150,#b61637);border:0;border-radius:12px;min-height:3rem;font-weight:750}
.stButton>button[kind="primary"]:hover{background:#f34a66}
div[data-testid="stTextInput"] input,div[data-testid="stTextArea"] textarea{background:#23191e;color:white;border:1px solid #61303d;border-radius:12px}
.hero{background:linear-gradient(120deg,#371722,#1c1117);border:1px solid #763041;border-radius:18px;padding:25px;margin-bottom:20px}
.hero b{font-size:1.8rem;color:white}.hero small{color:#ff8299;letter-spacing:.12em}.hero p{color:#d7c0c8}
</style>""",unsafe_allow_html=True)
st.markdown('<div class="hero"><small>MNTAGE / STUDIO IA</small><br><b>Ton script. Ta vidéo. Un clic.</b><p>Studio local rouge et noir · voix · sous-titres · montage · historique</p></div>',unsafe_allow_html=True)

tab_create,tab_queue,tab_stats=st.tabs(["🎬 Créer","📂 File & historique","📊 Résultats"])
with tab_create:
    title=st.text_input("Titre","Mon premier Short")
    script=st.text_area("Script",height=230,placeholder="Colle ton script…")
    st.caption(f"{len(script.split())} mots · environ {round(len(script.split())/2.5)} secondes")
    with st.expander("⚙️ Options avancées",expanded=False):
        voice=st.selectbox("Voix française",["fr-FR-DeniseNeural","fr-FR-HenriNeural"])
        voice_speed=st.select_slider("Débit de narration",options=["-15%","-10%","-5%","+0%","+5%","+10%"],value="-5%",help="Un débit légèrement plus lent peut rendre la narration plus posée.")
        modes=[]
        if os.environ.get("PEXELS_API_KEY"):
            modes.append("Vidéos Pexels — vrais clips (recommandé)")
        modes.append("Éco — fonds animés abstraits (démonstration)")
        if configured(): modes.append("IA locale — Stable Diffusion CPU (lent)")
        if os.environ.get("PEXELS_API_KEY"):
            modes.append("Photos Pexels — recherche automatique")
        mode=st.selectbox("Visuels",modes)
        captions=st.checkbox("Sous-titres incrustés (timing estimé)",value=True)
        music=st.file_uploader("Musique MP3 autorisée (facultatif)",type=["mp3"])
        images=st.file_uploader("Mes images (facultatif)",type=["png","jpg","jpeg"],accept_multiple_files=True)
        st.caption("⚠️ Le mode Éco ne produit pas de vrais sujets vidéo. Pour de véritables clips, configure PEXELS_API_KEY et choisis Vidéos Pexels.")
        st.caption("La file d'attente enregistre uniquement le script et les options de base. Musique et images personnelles : génération immédiate.")
    def visuals():
        if images:return [i.getvalue() for i in images]
        if mode.startswith("IA locale"):
            sentences=[s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+",script) if s.strip()]
            return generate_images(["cinematic editorial illustration, no text, portrait composition, "+s[:250] for s in sentences[:6]],backend="cpu",steps=12)
        if mode.startswith("Photos"):
            items=search_images(title,limit=4)
            if not items:raise RuntimeError("Aucune photo Pexels trouvée.")
            st.info("Crédits des photos : "+", ".join(i["credit"] for i in items))
            return download_images(items)
        return script_to_images(script,title)
    if st.button("🎬 Créer ma vidéo maintenant",type="primary",use_container_width=True):
        if not script.strip():st.warning("Colle ton script.")
        else:
            try:
                with st.spinner("Génération de la vidéo…"):
                    clips=None
                    if mode.startswith("Vidéos"):
                        queries=scene_queries(script,limit=8)
                        found=[]
                        for query in queries:
                            matches=search_videos(query,limit=2)
                            if matches:found.append(matches[0])
                        if not found:raise RuntimeError("Aucun clip trouvé. Essaie le mode Éco ou reformule ton script.")
                        clips=download_videos(found)
                        st.caption("Sources des clips : "+", ".join(item["page"] for item in found))
                        st.info("Montage automatique avec de vrais clips ; vérifie que chaque plan illustre correctement ton texte.")
                    path=make_video(title,script,[] if clips else visuals(),voice,captions=captions,music=music.getvalue() if music else None,voice_rate=voice_speed,video_bytes=clips)
                st.session_state["last_video"]=str(path)
                st.success("Vidéo prête. Vérifie les images et les droits avant publication.")
            except Exception as exc:st.error(f"Erreur : {exc}")
    if st.button("➕ Ajouter à la file d'attente",use_container_width=True):
        if not script.strip():st.warning("Colle ton script.")
        elif music or images:st.warning("Pour la file, retire les fichiers ajoutés : ils ne sont pas conservés.")
        else:
            enqueue(title,script,mode,voice,captions)
            st.success("Ajouté à la file. Lance ensuite le prochain travail dans l'onglet File & historique.")
    if st.session_state.get("last_video"):
        p=Path(st.session_state["last_video"])
        if p.is_file():
            st.video(str(p))
            st.download_button("⬇️ Télécharger MP4",p.read_bytes(),file_name=p.name,mime="video/mp4",use_container_width=True)
            if p.with_suffix(".srt").exists():st.download_button("Sous-titres SRT",p.with_suffix(".srt").read_bytes(),file_name=p.with_suffix(".srt").name)
with tab_queue:
    st.caption("File locale persistante. Les tâches s'exécutent une par une, lorsque tu cliques. Pas de processus en arrière-plan.")
    if st.button("▶️ Traiter la prochaine vidéo",type="primary",use_container_width=True):
        job=next_job()
        if not job:st.info("La file est vide.")
        else:
            try:
                with st.spinner(f"Génération : {job['title']}"):
                    clips=None
                    if job["mode"].startswith("Vidéos"):
                        found=[]
                        for query in scene_queries(job["script"],limit=8):
                            matches=search_videos(query,limit=2)
                            if matches:found.append(matches[0])
                        if not found:raise RuntimeError("Aucun clip trouvé.")
                        clips=download_videos(found)
                        pics=[]
                    elif job["mode"].startswith("IA locale"):
                        if not configured():raise RuntimeError("Le moteur IA local n'est pas configuré.")
                        sentences=[s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+",job["script"]) if s.strip()]
                        pics=generate_images(["cinematic editorial illustration, no text, portrait, "+s[:250] for s in sentences[:6]],backend="cpu",steps=12)
                    elif job["mode"].startswith("Photos"):
                        pics=download_images(search_images(job["title"],limit=4))
                        if not pics:raise RuntimeError("Aucune photo trouvée.")
                    else:pics=script_to_images(job["script"],job["title"])
                    path=make_video(job["title"],job["script"],pics,job["voice"],captions=bool(job["captions"]),video_bytes=clips)
                    finish(job["id"],video=path)
                st.success(f"Vidéo #{job['id']} créée.")
            except Exception as exc:
                finish(job["id"],error=str(exc))
                st.error(f"Échec : {exc}")
    history=jobs()
    if not history:st.info("Aucune vidéo enregistrée dans l'historique.")
    for job in history:
        with st.expander(f"#{job['id']} · {job['title']} · {job['status']}"):
            st.caption(job["created"])
            if job["error"]:st.error(job["error"])
            path=Path(job["video"]) if job["video"] else None
            if path and path.is_file():
                st.video(str(path))
                st.download_button("Télécharger MP4",path.read_bytes(),file_name=path.name,key=f"dl_{job['id']}")
                st.markdown("**Publication YouTube (privée uniquement)**")
                description=st.text_area("Description YouTube",key=f"desc_{job['id']}")
                confirm=st.checkbox("Je confirme vouloir envoyer cette vidéo en privé sur mon compte YouTube",key=f"confirm_{job['id']}")
                if st.button("Envoyer sur YouTube en privé",disabled=not confirm,key=f"yt_{job['id']}"):
                    try:
                        from youtube_upload import upload_private
                        with st.spinner("Authentification et envoi YouTube…"):
                            url=upload_private(path,job["title"],description)
                        set_youtube(job["id"],url)
                        st.success("Envoi terminé : "+url)
                    except Exception as exc:st.error(str(exc))
            if job["youtube_url"]:st.markdown(f"[Ouvrir la vidéo privée]({job['youtube_url']})")
with tab_stats:
    history=jobs()
    done=[j for j in history if j["status"]=="done"]
    c1,c2,c3=st.columns(3)
    c1.metric("Vidéos produites",len(done))
    c2.metric("Vues déclarées",sum(j["views"] for j in history))
    c3.metric("Résultat net déclaré",f"{sum(j['revenue']-j['costs'] for j in history):.2f} €")
    st.caption("Données saisies manuellement : aucune connexion YouTube Analytics ni estimation de revenus.")
    if history:
        ids={f"#{j['id']} · {j['title']}":j["id"] for j in history}
        choice=st.selectbox("Vidéo à mettre à jour",list(ids))
        current=next(j for j in history if j["id"]==ids[choice])
        views=st.number_input("Vues",min_value=0,value=current["views"],step=1)
        revenue=st.number_input("Revenus réels (€)",min_value=0.0,value=float(current["revenue"]),step=0.1)
        costs=st.number_input("Coûts réels (€)",min_value=0.0,value=float(current["costs"]),step=0.1)
        if st.button("Enregistrer les chiffres"):
            update_metrics(current["id"],views,revenue,costs)
            st.success("Chiffres enregistrés. Actualise l'onglet pour voir les totaux.")
