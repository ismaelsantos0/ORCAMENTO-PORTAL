import math

def ceil_div(a: float, b: float) -> int:
    """Ceil(a/b) com segurança."""
    if b == 0:
        return 0
    return int(math.ceil(float(a) / float(b)))
