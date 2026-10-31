"""Führt die vielen Genre-Varianten auf eine überschaubare Liste zurück."""
import json
import os

RULES_NAME = "genre-regeln.json"
# Reihenfolge zählt: "Punk Rock" soll Punk werden, nicht Rock
KEYWORDS = (("metal", "Metal"), ("punk", "Punk"), ("hardcore", "Punk"), ("hip hop", "Hip-Hop"),
            ("hip-hop", "Hip-Hop"), ("hiphop", "Hip-Hop"), ("rap", "Hip-Hop"), ("r&b", "R&B"),
            ("rnb", "R&B"), ("soul", "R&B"), ("funk", "R&B"), ("house", "Electronic"),
            ("techno", "Electronic"), ("trance", "Electronic"), ("electro", "Electronic"),
            ("synth", "Electronic"), ("edm", "Electronic"), ("drum and bass", "Electronic"),
            ("ambient", "Electronic"), ("dance", "Electronic"), ("schlager", "Schlager"),
            ("reggae", "Reggae"), ("ska", "Reggae"), ("jazz", "Jazz"), ("blues", "Blues"),
            ("country", "Country"), ("folk", "Folk"), ("classical", "Klassik"), ("klassik", "Klassik"),
            ("soundtrack", "Soundtrack"), ("latin", "Latin"), ("rock", "Rock"), ("pop", "Pop"))
EXAMPLE = {"neue deutsche welle": "Pop", "krautrock": "Rock"}


def rules_path(folder):
    return os.path.join(folder, RULES_NAME)


def load_rules(folder):
    """Eigene Zuordnungen aus der Regeldatei; Schlüssel in Kleinbuchstaben."""
    try:
        with open(rules_path(folder), encoding="utf-8") as f:
            return {str(k).casefold(): str(v) for k, v in json.load(f).items()}
    except (OSError, ValueError, AttributeError):
        return {}


def ensure_rules_file(folder):
    path = rules_path(folder)
    if not os.path.exists(path):
        os.makedirs(folder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(EXAMPLE, f, ensure_ascii=False, indent=2)
    return path


def canonical(genre, rules):
    text = genre.strip().casefold()
    if text in rules:
        return rules[text]
    for keyword, target in KEYWORDS:
        if keyword in text:
            return target
    return genre.strip()
