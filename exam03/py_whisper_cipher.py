def whisper_cipher(text: str, shift: int) -> str:
    # 1. Define our alphabets
    lower = "abcdefghijklmnopqrstuvwxyz"
    upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    result = ""
    
    for c in text:
        # 2. If it's a lowercase letter, shift it
        if c in lower:
            # find() gets the current position, add shift, modulo 26 wraps it around
            new_pos = (lower.find(c) + shift) % 26
            result += lower[new_pos]
            
        # 3. If it's an uppercase letter, shift it
        elif c in upper:
            new_pos = (upper.find(c) + shift) % 26
            result += upper[new_pos]
            
        # 4. If it's anything else (spaces, numbers, punctuation), leave it alone
        else:
            result += c
            
    return result

# --- Test cases ---
print(whisper_cipher("hello", 3))           # "khoor"
print(whisper_cipher("Hello World!", 1))    # "Ifmmp Xpsme!"
print(whisper_cipher("xyz", 3))             # "abc"
print(whisper_cipher("ABC123def", 5))       # "FGH123ijk"
print(whisper_cipher("", 10))               # ""
print(whisper_cipher("abc", -3))            # "xyz"