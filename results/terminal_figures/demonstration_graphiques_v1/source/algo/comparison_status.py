"""Présentation honnête des comparaisons ; aucune modification des coûts."""
import math

BETTER='Référence dépassée — solution améliorante validée'
EQUAL='Référence égalée — optimalité non démontrée'
OPTIMAL='Optimum atteint'
MISSING='Référence insuffisante — comparaison non concluante'
FAILED='Échec de recherche — aucun coût validé'
POSITIVE='Écart positif comparable'


def classify(cost,reference,*,valid=True,certified=False,tolerance=1e-8):
    if not valid:return FAILED
    if cost is None or reference is None:return MISSING
    if not math.isfinite(cost) or not math.isfinite(reference) or cost<0 or reference<0:
        raise ValueError('Coûts finis et non négatifs requis')
    difference=cost-reference
    if certified and difference < -tolerance:
        raise ValueError('Contradiction : coût inférieur à un optimum certifié compatible')
    if abs(difference)<=tolerance:return OPTIMAL if certified else EQUAL
    if reference==0:return MISSING
    return BETTER if difference<0 else POSITIVE


def positive_text(value):
    """Conserve toute valeur positive, y compris celles au-dessus de six."""
    if value is None or not math.isfinite(value) or value<=0:
        raise ValueError('Pourcentage strictement positif requis')
    return f'{value:.4f}' if value>=.0001 else f'{value:.8g}'


def present(cost,reference,**kwargs):
    status=classify(cost,reference,**kwargs)
    if status==POSITIVE:return positive_text(100*(cost/reference-1))+' %'
    return status


def describe_positive(values):
    """Statistiques conditionnelles ; effectifs des autres statuts conservés."""
    import numpy as np
    data=np.asarray([v for v in values if v is not None and math.isfinite(v)],float)
    positive=data[data>0]
    return dict(comparisons=len(data),positive_count=len(positive),
        reference_better_count=int((data<0).sum()),equal_count=int((data==0).sum()),
        positive_mean=float(positive.mean()) if len(positive) else None,
        positive_median=float(np.median(positive)) if len(positive) else None,
        above_six=int((positive>6).sum()))
