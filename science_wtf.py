"""Science WTF France: original low-cost illustrated scenes, no cloud calls."""
from __future__ import annotations
from io import BytesIO
import re
from PIL import Image, ImageDraw, ImageFont

TOPICS = {
    "abysses": ("LES ABYSSES", ["0 m : la lumière disparaît peu à peu", "1 000 m : l'obscurité domine", "Certaines espèces fabriquent leur lumière", "La baudroie attire ses proies avec un leurre", "La pression augmente avec la profondeur", "Le vivant s'adapte à des conditions extrêmes"]),
    "trous noirs": ("TROUS NOIRS", ["Une étoile massive peut s'effondrer", "Sa gravité déforme l'espace-temps", "L'horizon des événements marque une limite", "La lumière ne peut plus en ressortir", "Le disque d'accrétion peut être très lumineux", "On les étudie grâce à leurs effets observables"]),
    "tardigrades": ("TARDIGRADES", ["Un animal microscopique à huit pattes", "Il vit notamment dans les mousses", "Il peut entrer en cryptobiose", "Son métabolisme ralentit fortement", "Certains survivent à des conditions extrêmes", "Ce n'est pas un animal indestructible"]),
}
def _font(size):
    for name in ("C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try: return ImageFont.truetype(name, size)
        except OSError: pass
    return ImageFont.load_default()

def science_scenes(script: str, topic: str = "abysses", count: int = 12) -> list[bytes]:
    """Create vertical original cartoon cards with a recurring stick figure."""
    if not script.strip(): raise ValueError("Script vide.")
    if topic not in TOPICS: raise ValueError("Sujet Science WTF inconnu.")
    if not 1 <= count <= 24: raise ValueError("Entre 1 et 24 scènes.")
    title, facts = TOPICS[topic]
    colors = [(13, 22, 42), (23, 17, 48), (10, 37, 46)]
    output = []
    for i in range(count):
        im = Image.new("RGB", (540, 960), colors[i % len(colors)])
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((25, 25, 515, 935), radius=30, outline=(70, 220, 210), width=4)
        d.text((45, 65), "SCIENCE WTF", fill=(255, 218, 87), font=_font(38))
        d.text((45, 128), title, fill="white", font=_font(34))
        # Original recurring character with expressive gestures.
        x, y = 270, 430
        d.ellipse((x-48, y-140, x+48, y-44), outline="white", width=9)
        d.ellipse((x-22, y-104, x-13, y-95), fill="white")
        d.ellipse((x+13, y-104, x+22, y-95), fill="white")
        d.arc((x-18, y-92, x+18, y-65), 0, 180, fill=(255, 218, 87), width=5)
        d.line((x, y-44, x, y+105), fill="white", width=11)
        d.line((x, y+8, x-95, y-32+(i%3)*22), fill="white", width=9)
        d.line((x, y+8, x+95, y-42+(i%3)*22), fill="white", width=9)
        d.line((x, y+105, x-80, y+205), fill="white", width=9)
        d.line((x, y+105, x+80, y+205), fill="white", width=9)
        fact = facts[i % len(facts)]
        words, lines, line = fact.split(), [], ""
        for word in words:
            if len(line+" "+word)>28:
                lines.append(line); line=word
            else: line=(line+" "+word).strip()
        if line: lines.append(line)
        d.rounded_rectangle((42, 695, 498, 860), radius=24, fill=(26, 71, 82))
        for j, line in enumerate(lines[:4]):
            d.text((58, 714+j*36), line, fill="white", font=_font(25))
        d.text((45, 888), f"EPISODE  /  {i+1:02d}", fill=(255, 218, 87), font=_font(20))
        b = BytesIO(); im.save(b, format="PNG"); output.append(b.getvalue())
    return output

def sample_script(topic: str) -> str:
    if topic not in TOPICS: raise ValueError("Sujet Science WTF inconnu.")
    title, facts = TOPICS[topic]
    return ("Tu penses connaître ce sujet ? Attends de voir ce que la science a découvert.\n\n"
            + ". ".join(facts) + ".\n\n"
            "Mais attention : il faut distinguer ce qui est démontré de ce qui reste une hypothèse. "
            "La réalité scientifique est souvent plus étonnante que les légendes. "
            "Et toi, quelle question aimerais-tu qu'on explore ensuite ?")

def cloud_scene_prompts(topic: str, count: int = 8) -> list[str]:
    """Original scene-by-scene art direction; never invokes the paid API itself."""
    if topic not in TOPICS: raise ValueError("Sujet Science WTF inconnu.")
    if not 1 <= count <= 12: raise ValueError("Entre 1 et 12 scènes.")
    subject = {
        "abysses": [
            "ocean surface with a tiny research submarine preparing to dive",
            "descent into dark deep ocean, dramatic depth gradient",
            "bioluminescent jellyfish illuminating the black water",
            "anglerfish showing its glowing lure, scientifically recognizable",
            "hydrothermal vent and unusual deep sea creatures",
            "deep sea giant isopod on the ocean floor",
            "research submarine discovering the diversity of abyssal life",
            "dramatic final wide view of the deep sea ecosystem",
        ],
        "trous noirs": [
            "astronomer looking at a star-filled sky",
            "massive star collapsing into a black hole, educational illustration",
            "curved spacetime grid around a dark gravitational object",
            "black hole event horizon with bright accretion disk",
            "light bending around a black hole, gravitational lensing",
            "a distant star orbiting an invisible massive object",
            "radio telescopes observing a faraway galaxy",
            "scientific visualization of a black hole against the cosmos",
        ],
        "tardigrades": [
            "moss forest seen from microscopic perspective",
            "accurate eight-legged tardigrade walking on moss",
            "microscope view of a tardigrade in a water droplet",
            "tardigrade entering dormant tun state as water disappears",
            "diagram-like visual metaphor for extreme cold survival",
            "tardigrade reviving after rehydration",
            "scientist examining a microscopic water sample",
            "close-up of a tardigrade in its natural moss habitat",
        ],
    }[topic]
    style = ("Vertical 9:16, premium original educational cartoon illustration, "
             "cohesive 2D vector-like art, dark midnight blue, teal and warm yellow accents, "
             "clean bold silhouettes, playful but scientifically grounded, "
             "same recurring mascot: small friendly white stick-figure scientist "
             "with round head, two black dot eyes, yellow explorer backpack, "
             "mascot in a corner gesturing toward the main subject, "
             "strong central composition, large clear shapes, "
             "no text, no letters, no watermark, no logos, "
             "keep lower 30 percent visually quiet for subtitles. ")
    return [style + subject[i % len(subject)] for i in range(count)]

def script_scene_prompts(script: str, subject: str, count: int = 8) -> list[str]:
    """Build visual prompts from the actual narration, not a preset topic."""
    if not script.strip(): raise ValueError("Script vide.")
    if not subject.strip(): raise ValueError("Indique le sujet de l'épisode.")
    if not 1 <= count <= 12: raise ValueError("Entre 1 et 12 scènes.")
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", script) if s.strip()]
    if not sentences: raise ValueError("Script vide.")
    # Group consecutive sentences so the whole story is represented.
    chunks = [[] for _ in range(min(count, len(sentences)))]
    for i, sentence in enumerate(sentences):
        index = min(i * len(chunks) // len(sentences), len(chunks)-1)
        chunks[index].append(sentence)
    direction = ("Original vertical 9:16 premium educational 2D cartoon illustration, "
                 "dark midnight blue with teal and yellow accents, cinematic lighting, "
                 "one recurring simple white stick-figure scientist mascot with a small "
                 "yellow explorer backpack, expressive gestures, scientifically plausible "
                 "visual storytelling, no text, no letters, no logo, no watermark, "
                 "leave bottom 30 percent uncluttered for subtitles. ")
    return [direction + "Episode subject: " + subject[:120] +
            ". Illustrate this specific moment in the narration: " + " ".join(group)[:600]
            for group in chunks if group]

def free_script_scenes(script: str, subject: str, count: int = 12) -> list[bytes]:
    """Free fallback cards tied to a custom subject, never to unrelated presets."""
    if not script.strip() or not subject.strip(): raise ValueError("Sujet et script requis.")
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", script) if s.strip()]
    if not sentences: raise ValueError("Script vide.")
    output = []
    for i in range(count):
        im = Image.new("RGB", (540, 960), (13, 22, 42))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((25, 25, 515, 935), radius=30, outline=(70, 220, 210), width=4)
        d.text((42, 65), "SCIENCE WTF", fill=(255, 218, 87), font=_font(38))
        words = subject.upper().split()
        title_lines, line = [], ""
        for word in words:
            if len(line + " " + word) > 19:
                title_lines.append(line); line = word
            else: line = (line + " " + word).strip()
        if line: title_lines.append(line)
        for j, item in enumerate(title_lines[:2]):
            d.text((42, 128 + j*42), item, fill="white", font=_font(28))
        x,y=270,440
        d.ellipse((x-48,y-140,x+48,y-44),outline="white",width=9)
        d.ellipse((x-22,y-104,x-13,y-95),fill="white")
        d.ellipse((x+13,y-104,x+22,y-95),fill="white")
        d.arc((x-18,y-92,x+18,y-65),0,180,fill=(255,218,87),width=5)
        d.line((x,y-44,x,y+105),fill="white",width=11)
        d.line((x,y+8,x-95,y-32+(i%3)*22),fill="white",width=9)
        d.line((x,y+8,x+95,y-42+(i%3)*22),fill="white",width=9)
        d.line((x,y+105,x-80,y+205),fill="white",width=9)
        d.line((x,y+105,x+80,y+205),fill="white",width=9)
        fact = sentences[min(i*len(sentences)//count,len(sentences)-1)]
        lines=[]; line=""
        for word in fact.split():
            if len(line+" "+word)>29:
                lines.append(line); line=word
            else: line=(line+" "+word).strip()
        if line: lines.append(line)
        d.rounded_rectangle((42,680,498,870),radius=24,fill=(26,71,82))
        for j,item in enumerate(lines[:5]):
            d.text((55,699+j*33),item,fill="white",font=_font(23))
        b=BytesIO(); im.save(b,format="PNG"); output.append(b.getvalue())
    return output
