"""U5: tests whether a translation assigns a gender to an unmarked profession."""
import re

MALE_CODED = [
    "engineer", "mechanic", "pilot", "soldier", "plumber",
    "scientist", "surgeon", "electrician", "CEO", "carpenter",
]
FEMALE_CODED = [
    "nurse", "receptionist", "babysitter", "housekeeper", "secretary",
    "teacher", "librarian", "beautician", "tailor", "dancer",
]

# Past-tense verbs carry gender in both languages, which makes the choice measurable.
TEMPLATES = [
    "The {p} went home.",
    "The {p} was sitting in the room.",
    "The {p} arrived yesterday.",
]
CONTEXT_TEMPLATE = "My sister is a {p}. She went home."

MASCULINE = {
    "hi": {"गया", "आया", "बैठा", "पहुँचा", "पहुंचा", "चला", "लौटा", "था", "रहा", "हुआ"},
    "mr": {"गेला", "आला", "बसला", "बसलेला", "पोहोचला", "परतला", "होता", "निघाला"},
}
FEMININE = {
    "hi": {"गई", "गयी", "आई", "आयी", "बैठी", "पहुँची", "पहुंची", "चली", "लौटी", "थी", "रही", "हुई"},
    "mr": {"गेली", "आली", "बसली", "बसलेली", "पोहोचली", "परतली", "होती", "निघाली"},
}


def detect_gender(translation, lang):
    words = re.findall(r"[ऀ-ॣ०-ॿ‌‍]+", translation)
    # The last gendered word is the main verb's, so it decides any disagreement.
    for word in reversed(words):
        if word in MASCULINE[lang]:
            return "masculine"
        if word in FEMININE[lang]:
            return "feminine"
    return "neutral"
