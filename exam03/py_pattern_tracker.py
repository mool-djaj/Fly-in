def pattern_tracker(text: str) -> int:
    nb = 0
    
    for i in range(len(text) - 1):
        pair = text[i:i+2]
        
        if pair in "0123456789":
            nb += 1
            
    return nb

# --- Test Cases ---
print(pattern_tracker("123"))        # 2
print(pattern_tracker("12a34"))      # 2
print(pattern_tracker("987654321"))  # 0
print(pattern_tracker("01234567"))   # 7
print(pattern_tracker("abc"))        # 0
print(pattern_tracker("1a2b3c4"))    # 0 (Your original code failed this one)
print(pattern_tracker("112233"))     # 2