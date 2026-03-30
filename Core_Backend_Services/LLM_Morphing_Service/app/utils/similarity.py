from functools import lru_cache
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from app.core.config import settings


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """Load once, reuse everywhere. ~80MB download on first call."""
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def compute_similarity(text_a: str, text_b: str) -> float:
    """
    Compute cosine similarity between two question strings.
    Returns a float between 0.0 (totally different) and 1.0 (identical).

    Example:
        score = compute_similarity(
            "A train travels 60 km in 1 hour. How long to travel 210 km?",
            "A locomotive moves at 60 km/h. Time to cover 210 km?"
        )
        # Returns ~0.94
    """
    model = get_embedding_model()
    embeddings = model.encode([text_a, text_b])
    score = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    return float(np.clip(score, 0.0, 1.0))