"""Verify the checker's evidence before acting on it (pure functions, no LLM).

The checker LLM sometimes flags problems that are not there. A flag is kept only if its
evidence holds up:

- ``fix_fact``: ``quote`` (a sentence the checker says is unsupported) must really be in
  that chunk.
- ``missing_fact``: ``quote`` (the SOURCE sentence the checker says is missing) must be in
  the SOURCE, and most of its key words must NOT already appear anywhere in the lesson.
  Only one ``missing_fact`` flag per source sentence.
- ``simplify`` / ``add_glossary``: need a non-empty reason.

The kept reviews are then normalised to exactly one per chunk (missing chunks -> approve).

Grounding pre-check (before the checker runs): every sentence of each chunk's hook and body is
scored by the share of its content words that appear in the SOURCE. Low-scoring sentences are
"suspect"; the checker must judge each one, and confirmed ones become ``fix_fact`` flags.
Glossary text is not checked (it may use everyday definitions).
"""

import re
from dataclasses import dataclass

from humzehan.agents.state import ChunkReview, SuspectJudgment
from humzehan.schemas.lesson import Chunk

# A missing_fact flag is dropped when more than this share of its key words is in the lesson.
COVERED_SHARE = 0.5
# Words are compared by their first STEM_LENGTH letters ("evaporation" ~ "evaporates").
STEM_LENGTH = 5

_STOPWORDS_TEXT = """
    a about above after again against all also although am an and any are as at be because
    been before being below between both but by can could did do does doing down during each
    either even ever every few for from further had has have having he her here hers him his
    how however i if in into is it its itself just known let may me might more most much must
    my no nor not of off on once only or other our ours out over own per same she should so
    some such than that the their theirs them then there these they this those through thus
    to too under until up upon us very was we were what when where whether which while who
    whom whose why will with within without would yet you your
"""
STOPWORDS = frozenset(_STOPWORDS_TEXT.split())


# A sentence is "suspect" when less than this share of its content words is in the SOURCE.
# 0.6, not 0.5: on the sample, invented claims scored 0.50-0.57 and paraphrases 0.67+.
# A false suspect only costs the checker one judgment, not a rewrite.
GROUNDING_THRESHOLD = 0.6

# Simple suffix stripping, first match wins ("evaporation" -> "evaporat", "rises" -> "ris").
_SUFFIXES = (
    ("ational", "ate"),
    ("ation", "ate"),
    ("ies", "y"),
    ("ied", "y"),
    ("ing", ""),
    ("ed", ""),
    ("en", ""),
    ("es", ""),
    ("ly", ""),
    ("s", ""),
)


@dataclass(frozen=True)
class DroppedFlag:
    review: ChunkReview
    why: str


@dataclass(frozen=True)
class VerifiedReviews:
    reviews: list[ChunkReview]  # exactly one per chunk, in chunk order
    dropped: list[DroppedFlag]


# Curly quotes and long dashes -> plain ASCII, so quotes match however the model typed them.
_TYPOGRAPHIC = str.maketrans(
    {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-"}
)


def normalize_text(text: str) -> str:
    """Lowercase, remove Markdown emphasis, unify quotes and dashes, collapse whitespace."""
    text = text.lower().translate(_TYPOGRAPHIC)
    text = re.sub(r"[*_`#>]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _quote_core(quote: str) -> str:
    """The normalised quote without surrounding quotes, bullets and end punctuation."""
    return normalize_text(quote).strip(" \"'-.,;:!?")


def contains_quote(text: str, quote: str) -> bool:
    core = _quote_core(quote)
    return bool(core) and core in normalize_text(text)


def chunk_text(chunk: Chunk) -> str:
    glossary = " ".join(f"{g.term} {g.meaning}" for g in chunk.glossary)
    return "\n".join([chunk.heading, chunk.hook or "", chunk.body, glossary])


def key_stems(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", normalize_text(text))
    return {w[:STEM_LENGTH] for w in words if w not in STOPWORDS and len(w) > 2}


def is_covered(sentence: str, lesson_text: str) -> bool:
    """True when more than COVERED_SHARE of the sentence's key words appear in the lesson."""
    wanted = key_stems(sentence)
    if not wanted:
        return True
    found = wanted & key_stems(lesson_text)
    return len(found) / len(wanted) > COVERED_SHARE


def verify_reviews(
    reviews: list[ChunkReview], chunks: list[Chunk], source_text: str
) -> VerifiedReviews:
    """Keep only flags whose evidence holds up; return one review per chunk."""
    lesson_text = "\n".join(chunk_text(chunk) for chunk in chunks)
    kept: dict[int, ChunkReview] = {}
    dropped: list[DroppedFlag] = []
    missing_seen: set[str] = set()

    def drop(review: ChunkReview, why: str) -> None:
        dropped.append(DroppedFlag(review=review, why=why))

    for review in reviews:
        index = review.chunk_index
        if not 0 <= index < len(chunks):
            if review.action != "approve":
                drop(review, f"chunk {index} does not exist")
            continue
        if index in kept:
            if review.action != "approve":
                drop(review, f"chunk {index} already has a review")
            continue

        quote = review.quote or ""
        if review.action == "fix_fact":
            if not contains_quote(chunk_text(chunks[index]), quote):
                drop(review, "quoted sentence is not in the chunk")
                continue
        elif review.action == "missing_fact":
            if not contains_quote(source_text, quote):
                drop(review, "quoted sentence is not in the SOURCE")
                continue
            if is_covered(quote, lesson_text):
                drop(review, "fact is already covered in the lesson")
                continue
            if _quote_core(quote) in missing_seen:
                drop(review, "same missing fact already flagged")
                continue
            missing_seen.add(_quote_core(quote))
        elif review.action in ("simplify", "add_glossary") and not review.reason.strip():
            drop(review, "no reason given")
            continue

        kept[index] = review

    normalized = [
        kept.get(i, ChunkReview(chunk_index=i, action="approve", reason="Not flagged", quote=None))
        for i in range(len(chunks))
    ]
    return VerifiedReviews(reviews=normalized, dropped=dropped)


# --- Grounding pre-check -------------------------------------------------------------


@dataclass(frozen=True)
class SuspectSentence:
    chunk_index: int
    sentence: str
    share: float  # share of content words found in the SOURCE


def stem(word: str) -> str:
    """Strip one common suffix, then a final "e" ("rivers" -> "river", "rise" -> "ris")."""
    for suffix, replacement in _SUFFIXES:
        if (suffix == "s" and word.endswith("ss")) or (suffix == "ly" and word.endswith("ply")):
            continue
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)] + replacement
            break
    if word.endswith("e") and len(word) > 3:
        word = word[:-1]
    return word


def content_words(text: str) -> set[str]:
    """Lowercased, stemmed words without stopwords, numbers kept."""
    words = re.findall(r"[a-z0-9]+", normalize_text(text))
    return {stem(w) for w in words if w not in STOPWORDS and (len(w) > 2 or w.isdigit())}


def split_sentences(text: str) -> list[str]:
    """Split Markdown text into sentences; drop bold-only sub-heading lines ("**What it is**")."""
    sentences: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or re.fullmatch(r"(#+\s*)?\*\*[^*]+\*\*:?", line) or line.startswith("#"):
            continue
        line = re.sub(r"^([-*+]|\d+[.)])\s+", "", line)  # list bullets
        for part in re.split(r"(?<=[.!?])\s+", line):
            if content_words(part):
                sentences.append(part.strip())
    return sentences


def grounding_share(sentence: str, source_words: set[str]) -> float:
    words = content_words(sentence)
    if not words:
        return 1.0
    return len(words & source_words) / len(words)


def find_suspect_sentences(
    chunks: list[Chunk], source_text: str, threshold: float = GROUNDING_THRESHOLD
) -> list[SuspectSentence]:
    """Hook and body sentences whose content words are mostly not in the SOURCE."""
    source_words = content_words(source_text)
    suspects: list[SuspectSentence] = []
    for index, chunk in enumerate(chunks):
        for sentence in split_sentences(f"{chunk.hook or ''}\n{chunk.body}"):
            share = grounding_share(sentence, source_words)
            if share < threshold:
                suspects.append(SuspectSentence(index, sentence, round(share, 2)))
    return suspects


@dataclass(frozen=True)
class SuspectOutcome:
    reviews: list[ChunkReview]  # one per chunk, with confirmed suspects as fix_fact
    unsupported: list[SuspectSentence]
    supported: list[SuspectSentence]
    unjudged: list[SuspectSentence]


def apply_suspect_judgments(
    reviews: list[ChunkReview],
    suspects: list[SuspectSentence],
    judgments: list[SuspectJudgment],
) -> SuspectOutcome:
    """Turn suspect sentences the checker confirmed as unsupported into fix_fact flags.

    ``reviews`` must be one per chunk (output of ``verify_reviews``). A confirmed sentence
    replaces a lower-priority flag on its chunk, or is merged into an existing fix_fact.
    """
    verdicts: dict[int, SuspectJudgment] = {}
    for judgment in judgments:
        if 0 <= judgment.suspect_id < len(suspects):
            verdicts.setdefault(judgment.suspect_id, judgment)

    unsupported: list[SuspectSentence] = []
    supported: list[SuspectSentence] = []
    unjudged: list[SuspectSentence] = []
    reasons: dict[int, list[str]] = {}
    for suspect_id, suspect in enumerate(suspects):
        verdict = verdicts.get(suspect_id)
        if verdict is None:
            unjudged.append(suspect)
        elif verdict.supported:
            supported.append(suspect)
        else:
            unsupported.append(suspect)
            reasons.setdefault(suspect.chunk_index, []).append(verdict.reason)

    result = list(reviews)
    for index, chunk_reasons in reasons.items():
        sentences = [s.sentence for s in unsupported if s.chunk_index == index]
        current = result[index]
        quotes = [current.quote] if current.action == "fix_fact" and current.quote else []
        quotes += [s for s in sentences if s not in quotes]
        result[index] = ChunkReview(
            chunk_index=index,
            action="fix_fact",
            reason="Not supported by the SOURCE: " + "; ".join(chunk_reasons),
            quote="\n".join(quotes),
        )
    return SuspectOutcome(
        reviews=result, unsupported=unsupported, supported=supported, unjudged=unjudged
    )
