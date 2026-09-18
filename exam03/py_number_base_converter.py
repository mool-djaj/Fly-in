def number_base_converter(number: str, from_base: int, to_base: int) -> str:
    if not number or not (2 <= from_base <= 32 and 2 <= to_base <= 32):
        return "ERROR"

    CHAR = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    dec = 0
    for c in number:
        if c not in CHAR[:from_base]:
            return "ERROR"
        dec = (dec * to_base) + c.index