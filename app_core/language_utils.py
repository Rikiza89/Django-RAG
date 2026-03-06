"""
Language detection utilities — no external dependencies.
Uses Unicode block analysis to identify the dominant script/language
in a text string, then maps it to an LLM instruction so the model
always responds in the user's language.
"""

# ---------------------------------------------------------------------------
# Unicode block ranges → language code
# Order matters: check more specific ranges before shared ones.
# ---------------------------------------------------------------------------
_SCRIPT_RANGES = [
    # Non-Latin scripts (clear, unambiguous detection)
    ('ar',  0x0600, 0x06FF),   # Arabic
    ('he',  0x0590, 0x05FF),   # Hebrew
    ('hi',  0x0900, 0x097F),   # Devanagari (Hindi, Marathi, Nepali …)
    ('th',  0x0E00, 0x0E7F),   # Thai
    ('ru',  0x0400, 0x04FF),   # Cyrillic (Russian, Bulgarian, Ukrainian …)
    ('ko',  0xAC00, 0xD7AF),   # Hangul syllables (Korean)
    ('ko',  0x1100, 0x11FF),   # Hangul jamo
    # Japanese: hiragana + katakana (unique identifiers — CJK alone is ambiguous)
    ('ja',  0x3040, 0x309F),   # Hiragana
    ('ja',  0x30A0, 0x30FF),   # Katakana
    # CJK unified: could be Chinese *or* Japanese (kanji) — resolved below
    ('cjk', 0x4E00, 0x9FFF),
    ('cjk', 0x3400, 0x4DBF),   # CJK extension A
    ('cjk', 0x20000, 0x2A6DF), # CJK extension B
]

# ---------------------------------------------------------------------------
# LLM instruction per detected language
# Tells the model to respond in the same language as the query.
# ---------------------------------------------------------------------------
_LLM_INSTRUCTIONS: dict[str, str] = {
    'ja': '必ず日本語で回答してください。',
    'zh': '请始终用中文（简体）回答。',
    'ko': '항상 한국어로 답변해 주세요.',
    'ar': 'يُرجى الرد دائمًا باللغة العربية.',
    'he': 'אנא השב תמיד בעברית.',
    'hi': 'कृपया हमेशा हिंदी में उत्तर दें।',
    'ru': 'Пожалуйста, отвечайте всегда на русском языке.',
    'th': 'กรุณาตอบเป็นภาษาไทยเสมอ',
    'en': 'Always respond in English.',
    # Latin-script fall-through (French, German, Spanish, etc.) handled below
}

# Human-readable names for logging / UI
LANGUAGE_NAMES: dict[str, str] = {
    'ja': 'Japanese', 'zh': 'Chinese', 'ko': 'Korean',
    'ar': 'Arabic',   'he': 'Hebrew',  'hi': 'Hindi',
    'ru': 'Russian',  'th': 'Thai',    'en': 'English',
}


# ---------------------------------------------------------------------------
def detect_language(text: str) -> str:
    """
    Detect the dominant non-Latin language in *text* via Unicode block analysis.

    Returns an ISO 639-1 code ('ja', 'zh', 'ko', 'ar', 'hi', 'ru', 'th', …)
    or 'en' for Latin-script / unknown text.

    Distinguishes Japanese from Chinese:
      • Any hiragana / katakana → Japanese ('ja')
      • Pure CJK without kana   → Chinese  ('zh')
    """
    if not text or len(text.strip()) < 2:
        return 'en'

    counts: dict[str, int] = {}
    for char in text:
        cp = ord(char)
        for lang, start, end in _SCRIPT_RANGES:
            if start <= cp <= end:
                counts[lang] = counts.get(lang, 0) + 1
                break

    if not counts:
        return 'en'  # All Latin / ASCII → fall back

    # Resolve CJK ambiguity
    has_kana = counts.get('ja', 0) > 0
    has_cjk  = counts.get('cjk', 0) > 0

    if has_kana:
        # Hiragana or katakana present → Japanese
        counts['ja'] = counts.get('ja', 0) + counts.pop('cjk', 0)
    elif has_cjk:
        # Pure CJK without kana → Chinese
        counts['zh'] = counts.pop('cjk', 0)

    dominant = max(counts, key=counts.get)
    return dominant


def get_lang_instruction(text: str) -> str:
    """
    Return a short LLM instruction to respond in the detected language.

    For Latin-script text (French, German, Spanish, etc.) the instruction
    'Always respond in the same language as the user's question.' is returned,
    which modern LLMs handle reliably.
    """
    lang = detect_language(text)
    return _LLM_INSTRUCTIONS.get(
        lang,
        "Always respond in the same language as the user's question."
    )


def get_language_name(text: str) -> str:
    """Human-readable name of the detected language (for logging)."""
    return LANGUAGE_NAMES.get(detect_language(text), 'auto-detected')
