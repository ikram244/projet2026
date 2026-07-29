"""
chat_service.py
----------------
Chatbot echelons/KOFERT -- appele en tool-use les VRAIES fonctions du projet :
  - predict_service.predict_density(echelon, params)          -> densite predite
  - correction_service.correct(echelon, densite_mesuree,
        densite_cible, current_params, active_vars)            -> nouvelles consignes

Les 6 parametres process (echelons J/K/L) : TIC_sortie_ech, TI_entree_ech,
PI_calendre, PI_boucle, PI_separateur, prod_sortie_54 (debit de sortie acide 54%).

Trois couches de connaissances :
  1) KB generale (model/knowledge/kofert_kb.json) : texte du support de
     formation KOFERT, indexe en TF-IDF.
  2) Regles operationnelles (model/knowledge/regles_echelons.json) : seuils
     et procedures precises, injectees telles quelles dans le system prompt.
  3) Corrections admin (table SQL base_connaissance) : instructions/corrections
     ajoutees par l'administrateur via l'interface de gestion, chargees a
     chaque requete et injectees en priorite absolue.

Gratuit, via Groq (cloud, cle API sans carte bancaire, aucune ressource
locale requise).

Prerequis :
  1) Compte gratuit sur https://console.groq.com + cle sur console.groq.com/keys
  2) Variable d'environnement GROQ_API_KEY (dans un fichier .env a la racine)
  3) pip install groq python-dotenv
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import predict_service
import correction_service
from predict_service import FEATURES
from db import get_all_connaissances_texte

from groq import Groq

KNOWLEDGE_DIR = Path(__file__).parent / "model" / "knowledge"
# openai/gpt-oss-120b : remplacement recommande par Groq pour l'ex llama-3.3-70b-versatile
# (deprecated). Version plus legere/rapide : "openai/gpt-oss-20b".
MODEL_NAME = os.environ.get("CHATBOT_MODEL", "openai/gpt-oss-120b")

_client = None
_kb = None
_vectorizer = None
_kb_matrix = None
_rules = None


def _get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    return _client


def _load_kb():
    global _kb, _vectorizer, _kb_matrix
    if _kb is None:
        with open(KNOWLEDGE_DIR / "kofert_kb.json", encoding="utf-8") as f:
            _kb = json.load(f)
        corpus = [c["text"] for c in _kb]
        _vectorizer = TfidfVectorizer()
        _kb_matrix = _vectorizer.fit_transform(corpus)
    return _kb


def _load_rules():
    global _rules
    if _rules is None:
        with open(KNOWLEDGE_DIR / "regles_echelons.json", encoding="utf-8") as f:
            _rules = json.load(f)
    return _rules


def _load_admin_corrections():
    """Charge les corrections/instructions admin depuis la base SQL,
    a chaque appel (pas de cache), pour que les changements soient
    pris en compte immediatement par tous les utilisateurs."""
    try:
        rows = get_all_connaissances_texte()
    except Exception:
        rows = None
    return rows or []


def retrieve(question: str, top_k: int = 4) -> list:
    kb = _load_kb()
    q_vec = _vectorizer.transform([question])
    sims = cosine_similarity(q_vec, _kb_matrix)[0]
    top_idx = sims.argsort()[::-1][:top_k]
    return [kb[i] for i in top_idx if sims[i] > 0]


SYSTEM_PROMPT_TEMPLATE = """Tu es l'assistant technique de l'unite de concentration KOFERT (echelons J/K/L),
destine aux ouvriers nouveaux et experimentes en salle de controle.

Les 6 parametres process pilotes sont : TIC_sortie_ech, TI_entree_ech, PI_calendre,
PI_boucle, PI_separateur, prod_sortie_54 (debit de sortie de l'acide 54%, ajoute
recemment au modele).

Regles de reponse, STRICTES :
- Pour toute question sur un seuil, une plage normale, ou une procedure d'arret : appuie-toi
  UNIQUEMENT sur les regles operationnelles ci-dessous. Ne les arrondis pas, ne les invente pas.
- Pour une question explicative generale (a quoi sert tel equipement, comment fonctionne telle
  section) : appuie-toi sur les extraits du support de formation fournis en contexte. S'ils ne
  couvrent pas la question, dis-le clairement plutot que de deviner.
- Si la question porte sur une densite predite ou une correction de reglages, utilise les outils
  predict_density / correct_parameters plutot que d'estimer toi-meme -- ils appellent les vrais
  modeles entraines du projet, pas une approximation.
- Pour toute situation ambigue ou proche d'un seuil d'arret/securite, recommande explicitement de
  faire confirmer par un operateur/responsable plutot que de trancher seul.
- Langue : reponds dans la langue de la question -- francais, arabe standard (MSA), ou darija
  marocaine. Fais de ton mieux en darija meme si ta maitrise y est moins fiable que pour le francais ;
  ne refuse jamais de repondre en darija, mais si un chiffre/seuil est en jeu, verifie-le sur les
  regles operationnelles ci-dessous plutot que de l'improviser. Ne melange jamais deux langues dans
  une meme reponse.
- Mise en forme : structure toujours la reponse en Markdown -- tableaux pour comparer des valeurs,
  listes a puces pour des etapes/seuils multiples, gras pour les valeurs critiques. Reste concis.

Regles operationnelles (source de verite) :
{rules_json}
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "predict_density",
            "description": "Predit la densite de sortie 54% a partir des 6 parametres process actuels, pour un echelon donne. Utilise le vrai modele entraine du projet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "echelon": {"type": "string", "enum": ["J", "K", "L"]},
                    "params": {
                        "type": "object",
                        "properties": {f: {"type": "number"} for f in FEATURES},
                        "required": FEATURES,
                    },
                },
                "required": ["echelon", "params"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "correct_parameters",
            "description": "Calcule les nouvelles consignes des parametres pour combler l'ecart entre densite mesuree au labo et densite cible, pour un echelon donne. Utilise le vrai modele entraine du projet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "echelon": {"type": "string", "enum": ["J", "K", "L"]},
                    "densite_mesuree": {"type": "number"},
                    "densite_cible": {"type": "number"},
                    "current_params": {
                        "type": "object",
                        "properties": {f: {"type": "number"} for f in FEATURES},
                        "required": FEATURES,
                    },
                    "active_vars": {
                        "type": "array",
                        "items": {"type": "string", "enum": FEATURES},
                        "description": "Sous-ensemble des 6 parametres que l'operateur autorise a modifier. Omettre pour autoriser les 6.",
                    },
                },
                "required": ["echelon", "densite_mesuree", "densite_cible", "current_params"],
            },
        },
    },
]


def _run_tool(name: str, tool_input: dict) -> dict:
    if name == "predict_density":
        densite = predict_service.predict_density(tool_input["echelon"], tool_input["params"])
        return {"echelon": tool_input["echelon"], "densite_predite": round(densite, 2)}
    if name == "correct_parameters":
        return correction_service.correct(
            echelon=tool_input["echelon"],
            densite_mesuree=tool_input["densite_mesuree"],
            densite_cible=tool_input["densite_cible"],
            current_params=tool_input["current_params"],
            active_vars=tool_input.get("active_vars"),
        )
    raise ValueError(f"Outil inconnu : {name}")


def answer(question: str, history: list = None) -> dict:
    """
    history : liste de {"role": "user"|"assistant", "content": "..."} des tours precedents.
    Retourne {"reponse": str, "sources_kb": [...], "outils_appeles": [...]}.
    """
    rules = _load_rules()
    chunks = retrieve(question)

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(rules_json=json.dumps(rules, ensure_ascii=False, indent=2))
    if chunks:
        context = "\n\n".join(f"[Slide {c['slide']} - {c.get('section') or ''}] {c['text']}" for c in chunks)
        system_prompt += f"\n\nExtraits pertinents du support de formation KOFERT :\n{context}"

    corrections = _load_admin_corrections()
    if corrections:
        corrections_txt = "\n".join(
            f"- [{c['categorie'] or 'Général'}] {c['titre']} : {c['contenu']}" for c in corrections
        )
        system_prompt += (
            "\n\nCorrections et instructions de l'administrateur (SOURCE DE VERITE ABSOLUE -- "
            "en cas de conflit avec toute autre information ci-dessus, y compris les regles "
            "operationnelles ou le support de formation, applique TOUJOURS ces corrections) :\n"
            + corrections_txt
        )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": question})

    client = _get_client()
    outils_appeles = []

    while True:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOLS,
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            return {
                "reponse": msg.content or "",
                "sources_kb": [{"slide": c["slide"], "section": c.get("section")} for c in chunks],
                "outils_appeles": outils_appeles,
            }

        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            }
        )
        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)
            try:
                result = _run_tool(name, args)
                outils_appeles.append({"nom": name, "entree": args})
            except Exception as e:
                result = {"erreur": str(e)}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )