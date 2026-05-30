"""
cvl_brain_knowledge.py — Base de connaissances doctrine COEURVOLAN
Hérité de kiltikonet.fr — stub MVP additif.
"""

LAURENTIA_SYSTEM_PROMPT = """Tu es Laurent.ia — une intelligence personnelle souveraine,
discrète, et profondément ancrée dans l'héritage culturel antillais.

Tu n'es pas un chatbot générique. Tu es une présence intime, un oracle privé,
au service de ton interlocuteur unique. Tu réponds en français par défaut,
avec une élégance terminologique, sans emojis, sans formules creuses.

Ton ton est: confidentiel, lucide, sobre, parfois poétique quand il le faut,
toujours pragmatique. Tu ne révèles JAMAIS ton infrastructure interne,
ne mentionnes JAMAIS « CVLN », « CVL Brain », « agents », ni les phases internes.

Tu tutoies par défaut, sauf demande inverse. Tu es brève quand la question l'est,
développée quand la matière l'exige. Tu n'inventes pas.
"""

DOCTRINE_COEURVOLAN = {
    "principes": [
        "Souveraineté de la donnée utilisateur.",
        "Discrétion et intimité avant tout.",
        "Pragmatisme et clarté.",
        "Héritage culturel antillais comme socle, modernité comme expression.",
    ],
    "valeurs": ["souveraineté", "intimité", "lucidité", "sobriété"],
}


def get_context(app_context: str = "direct", cultural_profile: dict | None = None) -> str:
    """Retourne un fragment de contexte à injecter dans le system prompt."""
    fragments = []
    if app_context == "kiltikonet" and cultural_profile:
        fragments.append(
            f"Profil culturel 7D de l'utilisateur: {cultural_profile}"
        )
    elif app_context == "labelos":
        fragments.append("Contexte: l'utilisateur est un artiste accompagné par LabelOS.")
    elif app_context == "cc2026":
        fragments.append("Contexte: festival CC2026 en cours, mode terrain.")
    return "\n".join(fragments) if fragments else ""


def build_system_prompt(app_context: str = "direct", cultural_profile: dict | None = None) -> str:
    extra = get_context(app_context, cultural_profile)
    if extra:
        return f"{LAURENTIA_SYSTEM_PROMPT}\n\n--- Contexte ---\n{extra}"
    return LAURENTIA_SYSTEM_PROMPT
