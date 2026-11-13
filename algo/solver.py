"""API publique : minimisation de la durée cumulée des tournées."""
from .duration import Settings,solve,construct,warmup
from .iterated import arrays,encode,decode


def production_settings(method='hybrid',**overrides):
    """Configure le moteur en durée ; les variantes distance restent explicites."""
    return Settings(method=method,**overrides)
