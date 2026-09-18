def echo_validator(text: str) -> bool:
    s = ""
    for i in text:
        if i.isalpha():
            s += i
    if not s:
        return False
    return s[::-1].lower() == s.lower()


print(echo_validator(""))