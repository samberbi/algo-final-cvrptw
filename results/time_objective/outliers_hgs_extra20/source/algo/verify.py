"""Independent final check: no search kernel, caches, or insertion helpers."""
from numbers import Integral
import math
from .model import EPS


def verify(routes, ins):
    """Recalcule toutes les contraintes indépendamment des noyaux de recherche.
    Entrées : listes de clients par tournée et instance originale.
    Sortie : validité, erreurs, distance, charge et horaires détaillés.
    Les métriques restent dans les unités internes ; un coût affiché est divisé par 10."""
    errors, details, seen = [], [], []
    used = [list(r) for r in routes if len(r)]
    if len(used) > ins.vehicles:
        errors.append("fleet exceeded")
    for ridx, route in enumerate(used):
        if any(not isinstance(i, Integral) or isinstance(i, bool) or not 1 <= i <= ins.n for i in route):
            errors.append(f"route {ridx}: invalid client")
            continue
        seen.extend(int(i) for i in route)
        clock = road = distance = idle = quantity = 0.0
        previous = 0
        schedule = []
        for client in route:
            arrival = clock + float(ins.travel[previous][client])
            # Arriver trop tôt impose une attente ; la fenêtre porte sur le début du service.
            begin = max(float(ins.early[client]), arrival)
            finish = begin + float(ins.service[client])
            if begin > float(ins.late[client]) + EPS:
                errors.append(f"route {ridx}: window {client}")
            idle += begin - arrival
            road += float(ins.travel[previous][client])
            distance += float(ins.distance[previous][client])
            quantity += float(ins.demand[client])
            schedule.append(dict(client=int(client), arrival=arrival, start=begin, finish=finish))
            clock, previous = finish, client
        # Le trajet de retour compte dans la distance et doit respecter la fermeture du dépôt.
        clock += float(ins.travel[previous][0])
        road += float(ins.travel[previous][0])
        distance += float(ins.distance[previous][0])
        if quantity > ins.capacity + EPS:
            errors.append(f"route {ridx}: capacity")
        if clock > ins.horizon + EPS:
            errors.append(f"route {ridx}: horizon")
        if not all(math.isfinite(x) for x in (clock, road, distance, idle, quantity)):
            errors.append(f"route {ridx}: nonfinite metrics")
        details.append(dict(duration=clock, travel=road, distance=distance, waiting=idle,
                            load=quantity, schedule=schedule))
    # Cette égalité vérifie simultanément la couverture et l’absence de doublons.
    if sorted(seen) != list(range(1, ins.n + 1)):
        errors.append("missing or duplicated clients")
    return dict(valid=not errors, errors=errors, vehicles=len(used),
                duration=sum(d['duration'] for d in details),
                distance=sum(d['distance'] for d in details),
                travel=sum(d['travel'] for d in details),
                waiting=sum(d['waiting'] for d in details),
                makespan=max((d['duration'] for d in details), default=0), routes=details)
