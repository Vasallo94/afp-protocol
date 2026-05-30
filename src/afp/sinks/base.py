class Sink:
    """Interfaz común de los sinks AFP."""

    name: str = "base"

    def submit(self, report: dict) -> str:
        """Deposita el reporte y devuelve una referencia (ruta o URL)."""
        raise NotImplementedError
