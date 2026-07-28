"""
Construit la base de connaissances (KB) generale du chatbot a partir du support
de formation KOFERT (pptx). A relancer si le pptx est mis a jour.

Usage:
    python build_kb.py chemin/vers/Presentation_KOFERT.pptx kofert_kb.json

Le pptx contient parfois une image corrompue (Bad CRC-32) qui fait planter les
lecteurs pptx standards (markitdown, python-pptx direct). Ce script contourne
le probleme en depaquetant l'archive en ignorant les entrees illisibles, puis
en lisant directement le XML des slides.
"""
import sys
import json
import zipfile
from pathlib import Path
from lxml import etree

NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def safe_unzip(pptx_path: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(pptx_path) as z:
        for name in z.namelist():
            try:
                data = z.read(name)
            except Exception:
                # entree corrompue (ex: Bad CRC-32 sur une image) -> on l'ignore,
                # on a besoin du texte des slides, pas des images
                continue
            target = out_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)


def slide_order(unpacked: Path):
    pres = etree.parse(str(unpacked / "ppt/presentation.xml"))
    rids = [
        s.get("{%s}id" % NS["r"])
        for s in pres.findall(".//p:sldIdLst/p:sldId", NS)
    ]
    rels = etree.parse(str(unpacked / "ppt/_rels/presentation.xml.rels"))
    relmap = {
        rel.get("Id"): rel.get("Target")
        for rel in rels.findall(".//rel:Relationship", NS)
    }
    return [relmap[r] for r in rids]


def slide_text(unpacked: Path, target: str) -> str:
    path = unpacked / "ppt" / target.replace("../", "")
    tree = etree.parse(str(path))
    texts = tree.findall(".//a:t", NS)
    return " ".join(t.text for t in texts if t.text).strip()


def looks_like_heading(text: str) -> bool:
    # heuristique : slides "titre de section" -> courts, sans ponctuation de phrase
    if len(text) == 0 or len(text) > 60:
        return False
    return "." not in text and "," not in text


def build(pptx_path: str, out_path: str):
    pptx_path = Path(pptx_path)
    unpacked = Path("/tmp/kb_unpack")
    safe_unzip(pptx_path, unpacked)
    order = slide_order(unpacked)

    chunks = []
    current_module = None
    current_section = None
    for i, target in enumerate(order, start=1):
        text = slide_text(unpacked, target)
        if not text:
            continue
        if text.upper().startswith("MODULE"):
            current_module = text
            continue
        if looks_like_heading(text):
            current_section = text
            continue
        chunks.append(
            {
                "id": f"slide_{i}",
                "slide": i,
                "module": current_module,
                "section": current_section,
                "text": text,
            }
        )

    Path(out_path).write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"{len(chunks)} chunks ecrits dans {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python build_kb.py deck.pptx kofert_kb.json")
        sys.exit(1)
    build(sys.argv[1], sys.argv[2])
