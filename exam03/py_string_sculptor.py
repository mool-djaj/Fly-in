def string_sculptor(text: str) -> str:
    result = ""
    lower_next = True 
    
    for char in text:
        if char == " ":
            result += char
            lower_next = True  # Rule: Spaces reset the alternation
            
        elif char.isalpha():   # Check if it's an A-Z / a-z letter
            if lower_next:
                result += char.lower()
            else:
                result += char.upper()
            
            lower_next = not lower_next
            
        else:
            result += char
            
    return result

# --- Test Cases ---
print(string_sculptor("hello"))         # "hElLo"
print(string_sculptor("Hello World"))   # "hElLo wOrLd"
print(string_sculptor("abc123def"))     # "aBc123DeF"
print(string_sculptor("Python3.9!"))    # "pYtHoN3.9!"
print(string_sculptor(""))              # ""