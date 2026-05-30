from packageurl import PackageURL

SUPPORTED_SCHEMES = ("pkg", "https", "http", "mcp", "afp")


class InvalidSubjectUri(ValueError):
    """El subject_uri no respeta ningún esquema soportado por AFP."""


def _scheme_of(uri: str) -> str:
    # pkg: y afp: usan ':'; http(s):// y mcp:// usan '://'
    if "://" in uri:
        return uri.split("://", 1)[0]
    if ":" in uri:
        return uri.split(":", 1)[0]
    return ""


def validate_subject_uri(uri: str) -> str:
    if not uri or not isinstance(uri, str):
        raise InvalidSubjectUri("subject_uri vacío")
    scheme = _scheme_of(uri)
    if scheme not in SUPPORTED_SCHEMES:
        raise InvalidSubjectUri(f"esquema no soportado: {scheme!r}")
    if scheme == "pkg":
        try:
            PackageURL.from_string(uri)
        except ValueError as exc:
            raise InvalidSubjectUri(f"PURL inválido: {exc}") from exc
    else:
        # para http(s)/mcp/afp exigimos algo después del separador
        rest = uri.split("://", 1)[-1] if "://" in uri else uri.split(":", 1)[-1]
        if not rest:
            raise InvalidSubjectUri(f"localizador vacío para {scheme!r}")
    return uri
