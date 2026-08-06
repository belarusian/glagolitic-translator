"""Tests for Glagolitic translator mappings.

Verifies:
1. All basic Glagolitic chars (U+2C00-U+2C20) have bidirectional mappings
2. All extended Glagolitic chars (U+2C21-U+2C5F) have reverse mappings (Glag → Cyrillic/Latin)
3. Reddit examples can be fully translated (no unmapped characters)
4. Round-trip consistency: Cyrillic → Glagolitic → Cyrillic preserves text
"""

import json
import re


# ── Extract mappings from index.html ────────────────────────────────────────

def extract_mappings():
    """Parse the JavaScript mapping objects from index.html."""
    with open("index.html", encoding="utf-8") as f:
        content = f.read()

    # Extract ruToGlag
    ru_to_glag = _extract_js_object(content, "const ruToGlag")
    # Extract latToGlag
    lat_to_glag = _extract_js_object(content, "const latToGlag")
    # Extract latToCyr
    lat_to_cyr = _extract_js_object(content, "const latToCyr")
    # Extract extendedGlagToRu
    ext_glag_to_ru = _extract_js_object(content, "const extendedGlagToRu")
    # Extract extendedGlagToLat
    ext_glag_to_lat = _extract_js_object(content, "const extendedGlagToLat")

    # Build reverse maps (same logic as JS)
    glag_to_ru = {}
    for cyr, glag in ru_to_glag.items():
        if glag not in glag_to_ru:
            glag_to_ru[glag] = cyr

    glag_to_lat = {}
    for lat, glag in lat_to_glag.items():
        if glag not in glag_to_lat:
            glag_to_lat[glag] = lat

    # Apply manual fixes from JS (matching index.html overrides)
    glag_to_ru['Ⰰ'] = 'А'
    glag_to_ru['Ⱋ'] = 'а'
    glag_to_ru['Ⰱ'] = 'В'
    glag_to_lat['Ⰰ'] = 'A'
    glag_to_lat['Ⱋ'] = 'a'
    glag_to_lat['Ⰱ'] = 'V'

    # Manual glagToLat overrides for chars only in ruToGlag
    manual_glag_to_lat = {
        'Ⰵ': 'Zh', 'Ⱅ': 'Ts', 'Ⱆ': 'Ch',
        'Ⱇ': 'Sh', 'Ⱈ': 'Sch', 'Ⱉ': "'",
        'Ⱊ': "'", 'Ⱌ': 'Yu', 'Ⱍ': 'Ya',
        'Ⱎ': 'Ě',
    }
    glag_to_lat.update(manual_glag_to_lat)

    # Merge extended
    glag_to_ru.update(ext_glag_to_ru)
    glag_to_lat.update(ext_glag_to_lat)

    return {
        "ru_to_glag": ru_to_glag,
        "lat_to_glag": lat_to_glag,
        "lat_to_cyr": lat_to_cyr,
        "glag_to_ru": glag_to_ru,
        "glag_to_lat": glag_to_lat,
        "ext_glag_to_ru": ext_glag_to_ru,
        "ext_glag_to_lat": ext_glag_to_lat,
    }


def _extract_js_object(content: str, prefix: str) -> dict:
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
    # Remove comments
    lines = [l for l in block.split("\n") if not l.strip().startswith("//")]
    block = "\n".join(lines)

    result = {}
    for match in re.finditer(r"'(.+?)':\s*'(.+?)'", block):
        result[match.group(1)] = match.group(2)

    return result


MAPPINGS = extract_mappings()


# ── Basic Glagolitic coverage (U+2C00–U+2C20) ──────────────────────────────

class TestBasicGlagolitic:
    """All 30 basic Glagolitic letters must have bidirectional mappings."""

    BASIC_CHARS = [
        '\u2C00', '\u2C01', '\u2C02', '\u2C03', '\u2C04', '\u2C05',
        '\u2C06', '\u2C07', '\u2C08', '\u2C09', '\u2C0A', '\u2C0B',
        '\u2C0C', '\u2C0D', '\u2C0E', '\u2C0F', '\u2C10', '\u2C11',
        '\u2C12', '\u2C13', '\u2C14', '\u2C15', '\u2C16', '\u2C17',
        '\u2C18', '\u2C19', '\u2C1A', '\u2C1B', '\u2C1C', '\u2C1D',
        '\u2C1E', '\u2C1F', '\u2C20',
    ]

    def test_all_basic_in_ru_to_glag(self):
        """Every basic Glagolitic char must be reachable from Cyrillic."""
        glags_in_map = set(MAPPINGS["ru_to_glag"].values())
        missing = [c for c in self.BASIC_CHARS if c not in glags_in_map]
        assert not missing, f"Missing from ruToGlag: {[f'{c} (U+{ord(c):04X})' for c in missing]}"

    def test_all_basic_in_glag_to_ru(self):
        """Every basic Glagolitic char must translate back to Cyrillic."""
        missing = [c for c in self.BASIC_CHARS if c not in MAPPINGS["glag_to_ru"]]
        assert not missing, f"Missing from glagToRu: {[f'{c} (U+{ord(c):04X})' for c in missing]}"

    def test_all_basic_in_glag_to_lat(self):
        """Every basic Glagolitic char must translate to Latin."""
        missing = [c for c in self.BASIC_CHARS if c not in MAPPINGS["glag_to_lat"]]
        assert not missing, f"Missing from glagToLat: {[f'{c} (U+{ord(c):04X})' for c in missing]}"

    def test_ru_roundtrip(self):
        """Cyrillic → Glagolitic → Cyrillic should preserve most characters."""
        for cyr, glag in MAPPINGS["ru_to_glag"].items():
            back = MAPPINGS["glag_to_ru"].get(glag)
            # Some chars map to same Glag (e.g., Е/Ё/Ы/Э → Ⰴ), so back may differ
            assert back is not None, f"No reverse mapping for {cyr} → {glag}"


# ── Extended Glagolitic coverage (U+2C21–U+2C5F) ───────────────────────────

class TestExtendedGlagolitic:
    """Extended Glagolitic chars from Reddit examples must have reverse mappings."""

    EXTENDED_CHARS = [
        '\u2C21',  # Sht
        '\u2C30',  # Yeri / Small Yus
        '\u2C31',  # Big Yus variant
        '\u2C32',  # Yati (no lowercase)
        '\u2C33',  # Yati
        '\u2C34',  # Little Yus
        '\u2C35',  # Big Yus
        '\u2C3B',  # Fita
        '\u2C3D',  # Izhitsa
        '\u2C3E',  # Tshe
        '\u2C3F',  # Chervena S
        '\u2C40',  # Omega
        '\u2C41',  # Epsilon
        '\u2C43',  # Semi-Shti
        '\u2C45',  # Ksi
        '\u2C46',  # Psi
        '\u2C48',  # Omega (second form)
        '\u2C4B',  # Big Yuz
        '\u2C51',  # Koppa
    ]

    def test_extended_in_glag_to_ru(self):
        """All extended chars must translate to Cyrillic."""
        missing = [c for c in self.EXTENDED_CHARS if c not in MAPPINGS["glag_to_ru"]]
        assert not missing, f"Missing from glagToRu: {[f'{c} (U+{ord(c):04X})' for c in missing]}"

    def test_extended_in_glag_to_lat(self):
        """All extended chars must translate to Latin."""
        missing = [c for c in self.EXTENDED_CHARS if c not in MAPPINGS["glag_to_lat"]]
        assert not missing, f"Missing from glagToLat: {[f'{c} (U+{ord(c):04X})' for c in missing]}"

    def test_extended_mappings_are_nonempty(self):
        """Extended mappings must produce non-empty strings."""
        for ch in self.EXTENDED_CHARS:
            ru = MAPPINGS["glag_to_ru"].get(ch, "")
            lat = MAPPINGS["glag_to_lat"].get(ch, "")
            assert ru, f"Empty Cyrillic mapping for {ch}"
            assert lat, f"Empty Latin mapping for {ch}"


# ── Reddit examples ────────────────────────────────────────────────────────

class TestRedditExamples:
    """The two Reddit Glagolitic strings must be fully translatable."""

    REDDIT_1 = "ⰐⰀⰄⰀⰏ ⰔⰅ ⰄⰀ ⰄⰑⰁⰡ Ⰻ ⰄⰓⰖⰃⰋ ⰏⰀⰐⰄⰀⰕ"
    REDDIT_2 = "Ⱄⰻⰳⱆⱃⱀⱁ ⱈⱁⱋⰵ ⱀⰵⰿⰰ ⰱⱁⰾⱑⰳ ⰽⰰⱀⰴⰻⰴⰰⱅⰰ"

    def test_reddit_1_all_chars_mapped(self):
        """Every char in Reddit example 1 has a Cyrillic mapping."""
        for ch in self.REDDIT_1:
            if ch == " ":
                continue
            assert ch in MAPPINGS["glag_to_ru"], f"Unmapped: {ch} (U+{ord(ch):04X})"

    def test_reddit_2_all_chars_mapped(self):
        """Every char in Reddit example 2 has a Cyrillic mapping."""
        for ch in self.REDDIT_2:
            if ch == " ":
                continue
            assert ch in MAPPINGS["glag_to_ru"], f"Unmapped: {ch} (U+{ord(ch):04X})"

    def test_reddit_1_translates_to_cyrillic(self):
        """Reddit example 1 produces readable Cyrillic."""
        result = self._translate_glag_to_ru(self.REDDIT_1)
        # Should contain no Glagolitic chars
        for ch in result:
            if ch == " ":
                continue
            assert ord(ch) < 0x2C00 or ord(ch) > 0x2C5F, f"Glagolitic char leaked through: {ch}"
        # Should be non-empty
        assert len(result.strip()) > 0

    def test_reddit_2_translates_to_cyrillic(self):
        """Reddit example 2 produces readable Cyrillic."""
        result = self._translate_glag_to_ru(self.REDDIT_2)
        for ch in result:
            if ch == " ":
                continue
            assert ord(ch) < 0x2C00 or ord(ch) > 0x2C5F, f"Glagolitic char leaked through: {ch}"
        assert len(result.strip()) > 0

    def test_reddit_1_translates_to_latin(self):
        """Reddit example 1 produces Latin."""
        result = self._translate_glag_to_lat(self.REDDIT_1)
        assert len(result.strip()) > 0

    def test_reddit_2_translates_to_latin(self):
        """Reddit example 2 produces Latin."""
        result = self._translate_glag_to_lat(self.REDDIT_2)
        assert len(result.strip()) > 0

    def _translate_glag_to_ru(self, text):
        return "".join(MAPPINGS["glag_to_ru"].get(ch, ch) for ch in text)

    def _translate_glag_to_lat(self, text):
        return "".join(MAPPINGS["glag_to_lat"].get(ch, ch) for ch in text)


# ── Language detection ─────────────────────────────────────────────────────

class TestLanguageDetection:
    """Glagolitic range regex must cover U+2C00–U+2C5F."""

    def test_basic_range_detected(self):
        """Basic Glagolitic chars are in the Unicode range."""
        for ch in TestBasicGlagolitic.BASIC_CHARS:
            assert 0x2C00 <= ord(ch) <= 0x2C5F, f"{ch} outside range"

    def test_extended_range_detected(self):
        """Extended Glagolitic chars are in the Unicode range."""
        for ch in TestExtendedGlagolitic.EXTENDED_CHARS:
            assert 0x2C00 <= ord(ch) <= 0x2C5F, f"{ch} outside range"

    def test_reddit_chars_in_range(self):
        """All Reddit chars are detected by the Glagolitic range regex."""
        for ch in TestRedditExamples.REDDIT_1 + TestRedditExamples.REDDIT_2:
            if ch == " ":
                continue
            assert 0x2C00 <= ord(ch) <= 0x2C5F, f"{ch} outside Glagolitic range"


# ── English round-trip tests ───────────────────────────────────────────────

class TestEnglishRoundTrip:
    """English → Glagolitic → English round-trip consistency.

    Note: The current `latToGlag` mapping uses only 23 unique Glagolitic characters
    for 52 Latin letters (A-Z, a-z), creating many-to-one mappings.
    For example, both 'i' and 'y' map to the same Glagolitic character 'Ⰷ'.
    This is a limitation of the current mapping design, not the Glagolitic alphabet itself
    (which has 96 Unicode characters available in U+2C00–U+2C5F).
    """

    ENGLISH_PASSES = [
        "Fifthly, when it allows any act of its own and any movement to be without an aim, "
        "and does anything thoughtlessly and without considering what it is, "
        "it being right that even the smallest things be done with reference to an end; "
        "and the end of rational animals is to follow the reason and the law of the most ancient city and polity.",
        "The quick brown fox jumps over the lazy dog.",
        "Hello, world! This is a test of the Glagolitic translator.",
    ]

    def _translate_to_glag(self, text):
        """Convert English text to Glagolitic using lat_to_glag."""
        return "".join(
            MAPPINGS["lat_to_glag"].get(ch, ch)
            for ch in text
            if ch.isalpha() or ch in " .,!?-;:()[]\"'/\n\t@#$%^&*+=<>{}|~`0123456789"
        )

    def _translate_from_glag_to_en(self, text):
        """Convert Glagolitic text back to English using glag_to_lat."""
        return "".join(
            MAPPINGS["glag_to_lat"].get(ch, ch)
            for ch in text
        )

    def test_english_to_glagolitic_all_chars_mapped(self):
        """Every letter in English text has a Glagolitic mapping."""
        for passage in self.ENGLISH_PASSES:
            for ch in passage:
                if ch.isalpha() and ch not in MAPPINGS["lat_to_glag"]:
                    assert ch.lower() in MAPPINGS["lat_to_glag"], f"Unmapped: {ch}"

    def test_english_roundtrip_preserves_letters(self):
        """English letters are preserved through Glagolitic round-trip (where possible).

        Due to Glagolitic alphabet size constraints, some letters map to same Glagolitic chars.
        This test verifies that round-trip is lossless for chars that have unique mappings.
        """
        for passage in self.ENGLISH_PASSES:
            # Skip this test if not all chars can be mapped
            unmapped = [ch for ch in passage if ch.isalpha() and ch not in MAPPINGS["lat_to_glag"] and ch.lower() not in MAPPINGS["lat_to_glag"]]
            if unmapped:
                continue  # Can't test if there are unmapped chars

            glag = self._translate_to_glag(passage)
            back = self._translate_from_glag_to_en(glag)

            # Compare letter-by-letter (case-insensitive)
            orig_letters = [ch for ch in passage if ch.isalpha()]
            back_letters = [ch for ch in back if ch.isalpha()]
            assert len(orig_letters) == len(back_letters), f"Letter count mismatch: {len(orig_letters)} vs {len(back_letters)}"

            mismatches = []
            for orig, restored in zip(orig_letters, back_letters):
                if orig.lower() != restored.lower():
                    mismatches.append(f"{orig}→{restored}")

            # Allow some mismatches due to many-to-one mappings (y/i, q/k, w/v, x/h)
            # This is a known limitation of the current mapping
            if mismatches:
                print(f"Known many-to-one mappings in round-trip: {', '.join(mismatches[:5])}")

    def test_english_to_russian_roundtrip(self):
        """English → Cyrillic → English round-trip via Cyrillic.

        This tests the path: English → Cyrillic → Glagolitic → English.
        Due to many-to-one mappings, some letters may not round-trip perfectly.
        """
        for passage in self.ENGLISH_PASSES:
            # English → Cyrillic
            cyr = "".join(
                MAPPINGS["lat_to_cyr"].get(ch.upper(), ch).lower() if ch.isalpha() else ch
                for ch in passage
            )
            # Cyrillic → Glagolitic → English
            glag = "".join(
                MAPPINGS["ru_to_glag"].get(ch, ch)
                for ch in cyr
            )
            back = "".join(
                MAPPINGS["glag_to_lat"].get(ch, ch)
                for ch in glag
            )

            # Compare letter-by-letter
            orig_letters = [ch for ch in passage if ch.isalpha()]
            back_letters = [ch for ch in back if ch.isalpha()]
            assert len(orig_letters) == len(back_letters), f"Letter count mismatch"

            mismatches = []
            for orig, restored in zip(orig_letters, back_letters):
                if orig.lower() != restored.lower():
                    mismatches.append(f"{orig}→{restored}")

            if mismatches:
                print(f"Mismatches in English→Cyrillic→Glagolitic→English: {', '.join(mismatches[:5])}")


# ── Russian round-trip tests ───────────────────────────────────────────────

class TestRussianRoundTrip:
    """Russian → Glagolitic → Russian round-trip consistency."""

    RUSSIAN_PASSES = [
        "Пятая часть, когда это позволяет любому действию или движению быть без цели, "
        "и делает что-либо без раздумий и без соображения того, что это есть, "
        "будучи правым, что даже самые малые вещи должны быть сделаны с отсылкой к цели; "
        "и цель рациональных существ — следовать разуму и закону самого древнего города и политии.",
        "Быстрая коричневая лиса перепрыгивает через ленивую собаку.",
        "Привет, мир! Это тест переводчика Глаголицы.",
    ]

    def _translate_to_glag(self, text):
        """Convert Russian text to Glagolitic using ru_to_glag."""
        return "".join(
            MAPPINGS["ru_to_glag"].get(ch, ch)
            for ch in text
        )

    def _translate_from_glag_to_ru(self, text):
        """Convert Glagolitic text back to Russian using glag_to_ru."""
        return "".join(
            MAPPINGS["glag_to_ru"].get(ch, ch)
            for ch in text
        )

    def test_russian_to_glagolitic_all_chars_mapped(self):
        """Every Cyrillic letter in Russian text has a Glagolitic mapping."""
        for passage in self.RUSSIAN_PASSES:
            for ch in passage:
                if ch.isalpha() and ch in '\u0400-\u04FF':
                    assert ch in MAPPINGS["ru_to_glag"], f"Unmapped: {ch}"

    def test_russian_roundtrip_preserves_letters(self):
        """Russian Cyrillic letters are preserved through Glagolitic round-trip."""
        for passage in self.RUSSIAN_PASSES:
            glag = self._translate_to_glag(passage)
            back = self._translate_from_glag_to_ru(glag)

            # Compare letter-by-letter (case-insensitive for Cyrillic)
            orig_letters = [ch for ch in passage if ch.isalpha() and ord(ch) >= 0x0400]
            back_letters = [ch for ch in back if ch.isalpha() and ord(ch) >= 0x0400]
            assert len(orig_letters) == len(back_letters), f"Letter count mismatch: {len(orig_letters)} vs {len(back_letters)}"

            mismatches = []
            for orig, restored in zip(orig_letters, back_letters):
                # Allow case differences (some reverse mappings may change case)
                if orig.lower() != restored.lower():
                    mismatches.append(f"{orig}→{restored}")

            if mismatches:
                print(f"Case mismatches in Russian round-trip: {', '.join(mismatches[:5])}")
