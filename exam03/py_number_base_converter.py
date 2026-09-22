def number_base_converter(number: str, from_base: int, to_base: int) -> str:
    # 1. Quick check for valid bases and empty string
    if not (2 <= from_base <= 36 and 2 <= to_base <= 36) or not number:
        return "ERROR"
        
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    base10 = 0
    
    # 2. Convert to Base 10
    for c in number:
        val = chars.find(c) # Finds the numeric value of the character
        if val == -1 or val >= from_base:
            return "ERROR"
        base10 = (base10 * from_base) + val
        
    # 3. Convert from Base 10 to Target Base
    if base10 == 0:
        return "0"
        
    result = ""
    while base10 > 0:
        result = chars[base10 % to_base] + result
        base10 //= to_base
        
    return result