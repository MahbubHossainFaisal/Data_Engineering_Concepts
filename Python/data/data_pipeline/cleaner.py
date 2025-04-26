def clean_data(data):
    """Public cleaning function"""
    return [item.strip() for item in data]

def _sanitize(text):  # Internal helper (not exported)
    return text.replace('\x00', '')