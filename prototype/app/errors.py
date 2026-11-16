class BusinessError(Exception):
    def __init__(self, status, code):
        self.status = status
        self.code = code


def error_body(code):
    # Stable codes drive Slovak UI text. Never include exception or database details.
    return {"error": {"code": code, "message": code.replace("_", " ")}}
