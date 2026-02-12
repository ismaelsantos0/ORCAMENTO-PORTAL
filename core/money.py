def brl(value: float) -> str:
    try:
        v = float(value)
    except Exception:
        v = 0.0
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
