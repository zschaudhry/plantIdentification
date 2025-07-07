import re

def highlight_toxicity(text):
    """
    Highlights warning words in toxicity text for better visibility in the UI.
    """
    highlight_words = [
        (r'(?i)danger(ous)?', '<span style="color:#b30000; font-weight:bold;">\\g<0></span>'),
        (r'(?i)toxic(ity)?', '<span style="color:#b30000; font-weight:bold;">\\g<0></span>'),
        (r'(?i)poison(ous)?', '<span style="color:#b30000; font-weight:bold;">\\g<0></span>'),
        (r'(?i)allergic', '<span style="color:#e67300; font-weight:bold;">\\g<0></span>'),
        (r'(?i)anaphylaxis', '<span style="color:#e67300; font-weight:bold;">\\g<0></span>'),
        (r'(?i)rash|blister|itch', '<span style="color:#e67300; font-weight:bold;">\\g<0></span>'),
    ]
    for pattern, repl in highlight_words:
        text = re.sub(pattern, repl, text)
    return text
