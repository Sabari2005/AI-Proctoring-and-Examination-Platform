import uuid
import time


def generate_trace_id(prefix: str = "mrph") -> str:
    """
    Generate a short unique trace ID for each morph run.
    Format: mrph-<timestamp_hex>-<random_4chars>
    Example: mrph-1a2b3c4d-f8e2
    """
    ts = format(int(time.time()), 'x')[-6:]
    rand = uuid.uuid4().hex[:4]
    return f"{prefix}-{ts}-{rand}"