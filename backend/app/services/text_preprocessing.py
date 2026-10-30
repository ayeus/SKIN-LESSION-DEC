"""Optional linguistic preprocessing; preserve clinical negation by default."""

from functools import lru_cache
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

NEGATION_CUES = {"no", "not", "nor", "never", "without"}


def settings(parameters):
    configuration = parameters.get("text_preprocessing", {})
    if not isinstance(configuration, dict) or set(configuration) - {
        "lowercase",
        "stop_words",
        "lemmatize",
    }:
        raise ValueError(
            "text_preprocessing supports lowercase, stop_words and lemmatize only"
        )
    for key in ["lowercase", "lemmatize"]:
        if key in configuration and not isinstance(configuration[key], bool):
            raise ValueError(f"{key} must be true or false")
    return configuration


def stop_words(parameters):
    value = settings(parameters).get("stop_words")
    if value is None:
        return None
    if value == "clinical_english":
        return sorted(set(ENGLISH_STOP_WORDS) - NEGATION_CUES)
    if (
        not isinstance(value, list)
        or len(value) > 1000
        or any(
            not isinstance(word, str) or not word.strip() or len(word) > 64
            for word in value
        )
    ):
        raise ValueError(
            "stop_words must be clinical_english or a list of at most 1000 explicit words"
        )
    if {word.casefold() for word in value} & NEGATION_CUES:
        raise ValueError(
            "Negation cues cannot be removed by the supported clinical text preprocessing"
        )
    return value


@lru_cache(maxsize=1)
def lemmatizer():
    try:
        import spacy

        nlp = spacy.blank("en")
        nlp.add_pipe("lemmatizer", config={"mode": "lookup"})
        nlp.initialize()
        return nlp
    except (ImportError, ValueError) as error:
        raise ValueError(
            "BLOCKED: lookup lemmatization requires the full NLP environment with spacy-lookups-data"
        ) from error


def linguistic_texts(texts, parameters):
    if not settings(parameters).get("lemmatize", False):
        return texts
    return [
        " ".join(token.lemma_ or token.text for token in document if not token.is_space)
        for document in lemmatizer().pipe(texts, batch_size=16)
    ]


def vectorizer(parameters):
    return TfidfVectorizer(
        max_features=10000,
        ngram_range=(1, 2),
        lowercase=settings(parameters).get("lowercase", True),
        stop_words=stop_words(parameters),
    )


def description(parameters):
    configuration = settings(parameters)
    words = stop_words(parameters)
    return {
        "lowercase_tfidf_features": configuration.get("lowercase", True),
        "stop_words": configuration.get("stop_words"),
        "retained_negation_cues": sorted(NEGATION_CUES),
        "lookup_lemmatization": configuration.get("lemmatize", False),
        "limitation": "Generic English linguistic processing, not clinical abbreviation resolution or medical validation. NER preserves original source text and bypasses these transformations.",
    }
