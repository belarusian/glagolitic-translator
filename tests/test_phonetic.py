"""Tests for Glagolitic translator phonetic mappings.

Verifies:
1. English → Russian phonetic mapping (QWERTY → ЙЦУКЕН)
2. Russian → Glagolitic mapping
3. English → Glagolitic direct 1:1 mapping
4. Round-trip: English → Glagolitic → English preserves text
5. Round-trip: English → Russian → Glagolitic → Russian → English preserves text
"""

import re


def extract_js_object(content: str, prefix: str) -> dict:
    """Extract a JS object literal following the given prefix."""
    idx = content.index(prefix)
    start = content.index("{", idx)
    depth = 0
    end = start
    for i in range(start, len(content)):
        if content[i] == "{":
            depth += 1
        elif content[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break

    block = content[start:end + 1]
    lines = [l for l in block.split("\n") if not l.strip().startswith("//")]
    block = "\n".join(lines)

    result = {}
    for match in re.finditer(r"'(.+?)':\s*'(.+?)'", block):
        result[match.group(1)] = match.group(2)

    return result


def get_mappings():
    """Load all mappings from index.html."""
    with open("index.html", encoding="utf-8") as f:
        content = f.read()

    ru_to_glag = extract_js_object(content, "const ruToGlag")
    lat_to_glag = extract_js_object(content, "const latToGlag")
    lat_to_cyr = extract_js_object(content, "const latToCyr")

    # Build reverse mappings
    glag_to_ru = {}
    for cyr, glag in ru_to_glag.items():
        if glag not in glag_to_ru:
            glag_to_ru[glag] = cyr

    glag_to_lat = {}
    for lat, glag in lat_to_glag.items():
        if glag not in glag_to_lat:
            glag_to_lat[glag] = lat

    return {
        "ru_to_glag": ru_to_glag,
        "lat_to_glag": lat_to_glag,
        "lat_to_cyr": lat_to_cyr,
        "glag_to_ru": glag_to_ru,
        "glag_to_lat": glag_to_lat,
    }


MAPPINGS = get_mappings()


# ── English → Russian phonetic mapping tests ────────────────────────────────

class TestEnglishToRussianPhonetic:
    """English → Russian phonetic mapping (QWERTY → ЙЦУКЕН)."""

    def test_privet_mir(self):
        """Privet mir → привет мир."""
        result = "".join(
            MAPPINGS["lat_to_cyr"].get(c, c) for c in "privet mir"
        )
        assert result == "привет мир"

    def test_dobroe_utro(self):
        """dobroe utro → доброе утро."""
        result = "".join(
            MAPPINGS["lat_to_cyr"].get(c, c) for c in "dobroe utro"
        )
        assert result == "доброе утро"

    def test_spasibo(self):
        """spasibo → спасибо."""
        result = "".join(
            MAPPINGS["lat_to_cyr"].get(c, c) for c in "spasibo"
        )
        assert result == "спасибо"

    def test_kak_dela(self):
        """kak dela → как дела."""
        result = "".join(
            MAPPINGS["lat_to_cyr"].get(c, c) for c in "kak dela"
        )
        assert result == "как дела"

    def test_q_tebq_l_bl(self):
        """q tebq l[bl[ → я тебя люблю."""
        result = "".join(
            MAPPINGS["lat_to_cyr"].get(c, c) for c in "q tebq l[bl["
        )
        assert result == "я тебя люблю"

    def test_q_el_a_tebe_xoro_ego_dn_q(self):
        """q ]ela[ tebe xorowego dnq → я желаю тебе хорошего дня."""
        result = "".join(
            MAPPINGS["lat_to_cyr"].get(c, c) for c in "q ]ela[ tebe xorowego dnq"
        )
        assert result == "я желаю тебе хорошего дня"

    def test_uvidimsq_poz_e(self):
        """uvidimsq poz]e → увидимся позже."""
        result = "".join(
            MAPPINGS["lat_to_cyr"].get(c, c) for c in "uvidimsq poz]e"
        )
        assert result == "увидимся позже"

    def test_skol_ko_vremeni(self):
        """skol-ko vremeni → сколько времени."""
        result = "".join(
            MAPPINGS["lat_to_cyr"].get(c, c) for c in "skol-ko vremeni"
        )
        assert result == "сколько времени"

    def test_gde_naxoditsq_stanciq_metro(self):
        """gde naxoditsq stanciq metro → где находится станция метро."""
        result = "".join(
            MAPPINGS["lat_to_cyr"].get(c, c) for c in "gde naxoditsq stanciq metro"
        )
        assert result == "где находится станция метро"

    def test_q_ne_ponima(self):
        """q ne ponima[ → я не понимаю."""
        result = "".join(
            MAPPINGS["lat_to_cyr"].get(c, c) for c in "q ne ponima["
        )
        assert result == "я не понимаю"


# ── English → Glagolitic direct 1:1 mapping tests ───────────────────────────

class TestEnglishToGlagoliticDirect:
    """English → Glagolitic direct 1:1 mapping (lowercase only)."""

    def test_single_letter_mappings(self):
        """Each English letter maps to a unique Glagolitic character."""
        # Check all 26 lowercase letters
        for letter in "abcdefghijklmnopqrstuvwxyz":
            assert letter in MAPPINGS["lat_to_glag"], f"Missing mapping for {letter}"
            glag = MAPPINGS["lat_to_glag"][letter]
            # Verify it's a Glagolitic character
            assert 0x2C00 <= ord(glag) <= 0x2C5F, f"{letter} maps to non-Glagolitic: {glag}"

    def test_all_glagolitic_chars_unique(self):
        """All 26 lowercase letters map to 26 unique Glagolitic characters."""
        glag_chars = set(MAPPINGS["lat_to_glag"].values())
        assert len(glag_chars) == 26, f"Expected 26 unique Glagolitic chars, got {len(glag_chars)}"

    def test_roundtrip_preserves_lowercase(self):
        """English lowercase letters round-trip perfectly."""
        test_text = "privet mir, dobroe utro!"
        glag = "".join(MAPPINGS["lat_to_glag"].get(c, c) for c in test_text.lower())
        back = "".join(MAPPINGS["glag_to_lat"].get(c, c) for c in glag)
        assert back == test_text.lower()

    def test_full_phrase_roundtrip(self):
        """Full English phrases round-trip correctly."""
        phrases = [
            "hello world",
            "thank you very much",
            "have a nice day",
            "see you later",
        ]
        for phrase in phrases:
            glag = "".join(MAPPINGS["lat_to_glag"].get(c, c) for c in phrase.lower())
            back = "".join(MAPPINGS["glag_to_lat"].get(c, c) for c in glag)
            assert back == phrase.lower(), f"Failed for: {phrase}"


# ── Russian → Glagolitic mapping tests ──────────────────────────────────────

class TestRussianToGlagolitic:
    """Russian → Glagolitic mapping."""

    def test_russian_to_glagolitic(self):
        """Russian text converts to Glagolitic."""
        # Test a simple phrase
        russian = "привет мир"
        result = "".join(
            MAPPINGS["ru_to_glag"].get(c, c) for c in russian.lower()
        )
        # Result should be Glagolitic (no Cyrillic chars)
        for ch in result:
            assert 0x2C00 <= ord(ch) <= 0x2C5F or ch == " ", f"Non-Glagolitic char: {ch}"

    def test_glagolitic_to_russian(self):
        """Glagolitic converts back to Russian."""
        # Test with known Glagolitic text
        glag = "ⰑⰏⰇⰁⰄⰑ ⰋⰇⰏ"
        result = "".join(
            MAPPINGS["glag_to_ru"].get(c, c) for c in glag
        )
        # Result should be Cyrillic
        has_cyrillic = any(0x0400 <= ord(ch) <= 0x04FF for ch in result)
        assert has_cyrillic, f"No Cyrillic in result: {result}"


# ── Complete phonetic flow tests ────────────────────────────────────────────

class TestCompletePhoneticFlow:
    """Complete English → Russian → Glagolitic → Russian → English flow."""

    def test_simple_phrase(self):
        """privet mir → привет мир → Glagolitic → привет мир → privet mir."""
        english = "privet mir"
        # English → Russian (phonetic)
        russian = "".join(MAPPINGS["lat_to_cyr"].get(c, c) for c in english.lower())
        # Russian → Glagolitic
        glag = "".join(MAPPINGS["ru_to_glag"].get(c, c) for c in russian.lower())
        # Glagolitic → Russian
        back_russian = "".join(MAPPINGS["glag_to_ru"].get(c, c) for c in glag)
        # Russian → English (phonetic reverse - inverse of lat_to_cyr)
        lat_to_cyr_inv = {v: k for k, v in MAPPINGS["lat_to_cyr"].items()}
        back_english = "".join(lat_to_cyr_inv.get(c, c) for c in back_russian.lower())
        assert back_english == english.lower()

    def test_longer_phrase(self):
        """Test a longer phrase with all phonetic characters."""
        english = "spasibo za pomosh"
        russian = "".join(MAPPINGS["lat_to_cyr"].get(c, c) for c in english.lower())
        glag = "".join(MAPPINGS["ru_to_glag"].get(c, c) for c in russian.lower())
        back_russian = "".join(MAPPINGS["glag_to_ru"].get(c, c) for c in glag)
        # Russian → English (phonetic reverse)
        lat_to_cyr_inv = {v: k for k, v in MAPPINGS["lat_to_cyr"].items()}
        back_english = "".join(lat_to_cyr_inv.get(c, c) for c in back_russian.lower())
        assert back_english == english.lower()
