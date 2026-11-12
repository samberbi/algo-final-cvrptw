"""Production configurations frozen after development, before validation.

Only numeric algorithm parameters are stored here. No instance name, solution
or BKS is available to the search through this module.
"""

from .optimized import Settings

PRODUCTION_CONFIGS = {
    "ils": {
        "method": "ils",
        "temperature_ratio": 0.2,
        "perturbation_strength": 4,
        "acceptance_tolerance": 0.005,
        "construction_attempts": 12,
        "local_search": True,
        "iterations": 1000000000,
        "neighbor_count": 24,
        "neighbor_mode": "geographic",
        "swap_star": False,
        "decomposition": True,
        "group_size": 240,
        "adaptive_groups": True,
        "sub_seconds": 0.2,
        "temperature_mode": "edge",
    },
    "sa": {
        "method": "sa",
        "temperature_ratio": 0.02,
        "perturbation_strength": 4,
        "acceptance_tolerance": 0.005,
        "construction_attempts": 12,
        "local_search": True,
        "iterations": 1000000000,
        "neighbor_count": 24,
        "neighbor_mode": "geographic",
        "swap_star": False,
        "decomposition": True,
        "group_size": 120,
        "sub_seconds": 0.2,
        "temperature_mode": "total",
        "adaptive_groups": False,
    },
}


def production_settings(method="ils", **overrides):
    """Copie le profil mesuré puis applique les paramètres explicitement demandés.
    Les profils ne dépendent ni du nom de l’instance ni de sa BKS."""
    if method not in PRODUCTION_CONFIGS:
        raise ValueError("Choose ils or sa")
    parameters = dict(PRODUCTION_CONFIGS[method])
    parameters.update(overrides)
    parameters["method"] = method
    return Settings(**parameters)
