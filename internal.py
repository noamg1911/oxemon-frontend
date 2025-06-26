# Very basic sanitization for Prometheus metric names
def replace_whitespace(name):
    return name.strip().lower().replace(" ", "_")
