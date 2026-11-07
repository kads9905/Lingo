"""Safety checks applied to everything entering and leaving the models."""
import re

MAX_CHARS = 600
# Calibrated on real and shuffled pairs by eval/run_adequacy.py.
ADEQUACY_FLOOR = 0.55

INJECTION = re.compile(
    r"ignore (all |any |the |your )?(previous|prior|above)|system prompt|you are now|"
    r"disregard (all |your )?(instructions|rules)|reveal your",
    re.I,
)
HARMFUL = re.compile(
    r"\b(how to (make|build) (a |an )?(bomb|explosive|weapon)|kill (myself|yourself)|"
    r"child (porn|sexual)|rape (her|him|them))\b",
    re.I,
)
PROFESSION_WORDS = re.compile(
    r"\b(doctor|nurse|teacher|engineer|driver|lawyer|pilot|cook|chef|scientist|mechanic|"
    r"secretary|manager|professor|soldier|police officer|farmer|receptionist|surgeon|cleaner)\b",
    re.I,
)
GENDER_WORDS = re.compile(
    r"\b(he|she|him|her|his|hers|man|woman|boy|girl|male|female|mother|father|sister|brother|"
    r"mr|mrs|ms)\b",
    re.I,
)


class Blocked(Exception):
    pass


def check_input(text):
    """Raises Blocked for unusable or harmful input; returns warnings for the rest."""
    text = text.strip()
    if not text:
        raise Blocked("Enter some English text first.")
    if len(text) > MAX_CHARS:
        raise Blocked(f"Please keep the text under {MAX_CHARS} characters.")
    if not re.search(r"[A-Za-z]", text):
        raise Blocked("This translator takes English text as input.")
    if HARMFUL.search(text):
        raise Blocked("This text was blocked by the safety filter.")

    warnings = []
    if INJECTION.search(text):
        warnings.append("This looks like an instruction to the AI. It was translated as plain text and not obeyed.")
    if PROFESSION_WORDS.search(text) and not GENDER_WORDS.search(text):
        warnings.append(
            "The English does not say the person's gender, but Hindi and Marathi verbs usually must. "
            "Any gender you see here was guessed by the model."
        )
    return warnings


def devanagari_share(text):
    letters = [c for c in text if c.isalpha() or "ऀ" <= c <= "ॿ"]
    if not letters:
        return 0.0
    return sum("ऀ" <= c <= "ॿ" for c in letters) / len(letters)


def check_output(translation, adequacy=None):
    """Returns (is_valid, warnings). Invalid output is withheld from the user."""
    if devanagari_share(translation) < 0.5:
        return False, ["The reply was not a Devanagari translation, so it was withheld."]
    if adequacy is not None and adequacy < ADEQUACY_FLOOR:
        return True, [f"Low meaning match ({adequacy:.2f}): this translation may have drifted from the source."]
    return True, []
