def apply_basic_grammar(sentence: str) -> str:
    if not sentence:
        return sentence

    words = sentence.lower().split()

    replacements = {
        "me": "I",
        "you": "you",
        "i": "I",
        "love": "love",
        "go": "go to",
    }

    corrected = []
    for w in words:
        corrected.append(replacements.get(w, w))

    final_sentence = " ".join(corrected)

    # Capitalize first letter
    final_sentence = final_sentence.capitalize()

    # Add punctuation if missing
    if not final_sentence.endswith((".", "?", "!")):
        final_sentence += "."

    return final_sentence
