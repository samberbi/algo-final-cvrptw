"""Oral guide built only from the completed new campaign."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
s=json.loads((ROOT/'results/revision_ils/summary.json').read_text(encoding='utf-8'));assert s['complete']
rows={x['profile']:x for x in s['summary']};ils=rows['ILS'];sa=next(x for k,x in rows.items() if k!='ILS')
text=f'''# Guide oral — CVRPTW, ILS contre recuit simulé

## Trame indicative pour huit à dix minutes

1. **Contexte et objectif.** Organiser des livraisons en réduisant la distance, sous capacité, fenêtres de début de service, flotte maximale et retour au dépôt. Le contexte durable ne permet pas de transformer nos unités abstraites en kilogrammes de CO₂.
2. **Modèle.** Définir C, les véhicules, les arcs et les variables. Montrer C1 pour l'unicité, C4 pour la capacité, C5–C7 pour les horaires et C8 contre les cycles isolés. Lire les quantificateurs : « pour chaque client appartenant à C et chaque véhicule appartenant à l'ensemble des véhicules ». Le PLNE fixe les règles ; il n'est pas le constructeur des métaheuristiques.
3. **Choix de l'ILS.** Le constructeur regret-2 donne un départ. Une perturbation modifie plusieurs positions par mouvements réalisables ; la recherche locale cherche ensuite des gains ; la règle de tolérance décide de la poursuite ; l'archive garde le record. Les voisinages sont fixes. La recherche locale est bornée, sans preuve d'optimum local complet.
4. **Comparateur recuit.** Même départ et mêmes contraintes, propositions directes. Toute amélioration est acceptée ; une hausse peut l'être selon exp(-delta/T). La température diminue avec le temps consommé. L'archive protège le meilleur résultat et aucune température n'autorise un retard.
5. **Résultats.** 28 instances, vingt graines et deux méthodes donnent 1 120 essais. ILS : gap moyen {ils['mean_gap']:.3f} %, pire {ils['worst_gap']:.3f} %, {ils['under7']}/560 sous 7 %. Recuit : moyenne {sa['mean_gap']:.3f} %, pire {sa['worst_gap']:.3f} %. Montrer aussi les lignes à 1 000 clients et les cas où le recuit est meilleur ; ne pas s'arrêter à la moyenne globale.
6. **Convergence et sensibilité.** La ligne représente une moyenne d'archives et la bande les quartiles, pas un intervalle de confiance. Commenter les gains tardifs. Sans recherche locale, le gap ILS atteint environ 8,38 % sur le lot exploratoire, contre 0,95 % avec elle. Huit perturbations ne sont pas automatiquement meilleures qu'une ou quatre à temps fixé.
7. **Validation et limites.** Dix petits PLNE, neuf optimalités certifiées et une limite de temps. Les grandes références sont des BKS compatibles, pas toutes des optimums prouvés. Ressources partagées, lot connu, seulement deux grandes instances et budgets imposés limitent la généralisation. Conclure par des améliorations à tester.

## Démonstration

Avant la soutenance, lancer le serveur et ouvrir http://127.0.0.1:8501. Les résultats sauvegardés sont disponibles sans relancer le benchmark.

```powershell
.\\.venv\\Scripts\\python.exe cli.py C101 --method ils --seconds 2 --seed 101
.\\.venv\\Scripts\\python.exe -m streamlit run web/app.py
```

Dans **Simulation**, sélectionner la nouvelle étude, une instance et un run ; lancer Lecture, mettre Pause et changer la vitesse. Ouvrir **Vérifier toutes les contraintes** : couverture unique, charge ≤ capacité, début du service dans la fenêtre et retour ≤ fermeture. Dans les graphiques, une arrivée avant ouverture entraîne de l'attente ; la fin du service peut dépasser la fermeture client. Expliquer ensuite une courbe de convergence de la Vue d'ensemble. L'horloge de livraison n'est pas l'horloge de calcul du solveur.

## Réponses aux questions probables

**Qui produit la première solution ?** Le constructeur regret-2, essayé douze fois. Le PLNE sert aux petites comparaisons exactes et n'est pas appelé pour initialiser le benchmark principal.

**Est-ce toujours de l'ALNS renommé ?** Non. Les cycles ILS et recuit utilisent des mouvements directs sur des tournées complètes. Le mécanisme de retrait/réparation n'est pas appelé pendant la recherche ; un test le vérifie. L'insertion regret-2 sert uniquement à construire le départ.

**Pourquoi l'ILS plutôt qu'une méthode déjà prise ?** Elle réutilise des voisins vérifiables et associe perturbation et amélioration locale dans une structure explicable. Le choix doit être défendu par nos résultats, pas par une promesse de supériorité universelle.

**Pourquoi vingt runs ?** Pour observer une variabilité aléatoire plus solidement qu'avec quelques essais, à un coût de calcul raisonnable. Ce nombre est notre choix, pas une obligation écrite du sujet. Plusieurs graines ne remplacent pas plusieurs instances.

**Le gap est-il à l'optimum ?** Sur les petits cas certifiés, oui. Pour le benchmark principal, il est calculé par rapport à la meilleure référence connue figée, avec la même troncature DIMACS. Un gap nul ne constitue pas, seul, une preuve d'optimalité.

**Peut-on annoncer que tous les cas passent sous 7 % ?** Non : citer le nombre exact sous le seuil et le pire résultat. Une moyenne faible ne masque pas un mauvais run.

**La courbe plate prouve-t-elle la convergence vers l'optimum ?** Non. Elle montre seulement que l'archive n'a plus été améliorée dans le temps observé. Le tableau du gain des derniers 20 % complète cette lecture.

**Le temps augmente-t-il avec la taille ?** Nos budgets sont imposés et changent avec la taille ; ces temps ne démontrent pas une loi de complexité. Les matrices sont quadratiques en mémoire et l'évaluation d'une tournée est linéaire en sa longueur.

**Pourquoi ne pas afficher de gap pour une capacité modifiée ?** La référence de l'instance originale ne résout plus le même problème. On compare succès, distances, attentes et variations appariées sans inventer une BKS.
'''
(ROOT/'docs/GUIDE_ORAL.md').write_text(text,encoding='utf-8')
print('Oral guide generated from completed results.')
