# MISSION — Créer et valider toutes les commandes de test CVRPTW dans le terminal VS Code

Je veux maintenant pouvoir tester facilement et directement mon projet CVRPTW depuis le terminal PowerShell de VS Code.

**Je veux que tu développes, corriges et vérifies réellement les commandes nécessaires. Ne me donne pas uniquement des exemples théoriques.**

Tu as accès au projet complet. Analyse les scripts existants avant toute modification.

Mon Notebook documente déjà `scripts/test_instances.py`, `scripts/benchmark_final_static.py`, `scripts/validate_soutenance.py` et `scripts/finalize_static.py`.

Vérifie leur existence, leur fonctionnement réel, leurs paramètres et les formats de sortie.

## 1. Mon objectif

Je veux pouvoir tester :

- Une instance précise.
- Plusieurs instances en une commande.
- Toutes les familles C1, C2, R1, R2, RC1, RC2.
- Des tailles de 25, 50, 100, 200, 400, 600, 800 et 1 000 clients.
- Mon ILS autonome.
- Le recuit simulé.
- PyVRP/HGS.
- Mon hybride initial.
- Mon hybride renforcé.
- Le solveur de référence indépendant.

Je veux que les commandes soient simples, lisibles et adaptées à PowerShell sous Windows.

## 2. Vérifier et améliorer le système de commandes

Vérifie d'abord `scripts/test_instances.py`.

Si ce script est déjà suffisant, améliore-le plutôt que de tout réécrire.

Je souhaite une interface de commandes permettant, idéalement, les usages suivants :

```powershell
python scripts/test_instances.py --instances C101 --seconds 10
```

```powershell
python scripts/test_instances.py --instances C101 R101 RC101 --seconds 10
```

```powershell
python scripts/test_instances.py --instances C1_10_6 --seconds 30
```

```powershell
python scripts/test_instances.py --instances C101 --method ils --seconds 10
```

Je veux aussi une commande pratique pour tester toutes les tailles progressivement.

Adapte les paramètres aux interfaces réellement disponibles. Vérifie le fonctionnement de chaque commande avant de la documenter.

Si nécessaire, crée un script utilisateur unique comme `scripts/run_benchmark.py`, mais conserve la compatibilité avec les anciens scripts.

## 3. Affichage obligatoire dans le terminal

À la fin de chaque résolution, je veux voir immédiatement un tableau contenant les informations suivantes :

- Nom de l'instance.
- Famille.
- Nombre de clients.
- Méthode utilisée.
- Graine aléatoire.
- Faisabilité : OUI/NON.
- Nombre de véhicules.
- Durée totale de la solution.
- Temps de déplacement total.
- Temps d'attente total.
- Temps de service total.
- Durée de la référence.
- Source de cette référence.
- Écart (%) à la référence.
- Gap certifié, uniquement s'il existe une preuve compatible.
- Temps CPU.
- Temps réel.
- Budget demandé.
- Statut de la résolution.

Exemple de présentation attendu :

```text
====================================================
               TEST CVRPTW
====================================================

Instance           : C101
Nombre de clients  : 100
Méthode            : Hybride renforcé
Graine             : 4101

FAISABILITÉ        : OUI

Véhicules utilisés : 10

Durée des trajets  : ...
Durée des attentes : ...
Durée des services : ...
DURÉE TOTALE       : ...

Référence          : ...
Type de référence  : ...
Écart référence    : ... %
Gap certifié       : Non disponible / ... %

Temps CPU          : ... s
Temps réel         : ... s

Contraintes        : VALIDÉES
====================================================
```

Les valeurs numériques doivent provenir de la véritable exécution et du vérificateur indépendant.

N'affiche jamais de données fictives dans les résultats réels.

Si la référence n'est pas disponible ou compatible, affiche clairement `NON DISPONIBLE` au lieu d'inventer un gap.

## 4. Comparaison entre plusieurs méthodes

Je veux une commande qui teste plusieurs méthodes sur la même instance et affiche un tableau comparatif.

Par exemple, à adapter selon l'interface :

```powershell
python scripts/run_benchmark.py --instance C101 --methods ils sa pyvrp hybrid refined --seconds 10
```

Le terminal doit afficher un tableau avec :

- Méthode.
- Durée trouvée.
- Faisabilité.
- Nombre de véhicules.
- Temps réel.
- Écart à la référence.
- Rang selon la durée réalisable.

La meilleure méthode doit être identifiée.

Mais ne compare les performances qu'en précisant les budgets et les conditions expérimentales.

## 5. Tester les instances jusqu'à 1 000 clients

Je veux pouvoir tester les familles suivantes :

**Solomon :**
- 25 clients.
- 50 clients.
- 100 clients.

**Gehring & Homberger :**
- 200 clients.
- 400 clients.
- 600 clients.
- 800 clients.
- 1 000 clients.

Vérifie les noms réels des instances et les chemins disponibles dans le projet.

Crée une commande pratique permettant de sélectionner une taille, une famille ou un lot d'instances.

Prévois également un mode permettant de lancer une campagne progressive sur toutes les tailles.

N'exécute pas automatiquement les 356 instances si je ne le demande pas explicitement.

## 6. Respect de notre fonction objectif

Le programme doit absolument minimiser :

\[
T=T_{\text{trajets}}+T_{\text{attentes}}+T_{\text{services}}
\]

Avec :

- Temps de trajet fixes.
- Temps de trajet symétriques.
- Départs à zéro.
- Fenêtres temporelles respectées.
- Capacités respectées.
- Retour au dépôt inclus.
- Horizon respecté.

Les solutions doivent être recalculées par notre vérificateur indépendant.

## 7. Références et gaps

Notre benchmark principal repose sur :

- Solomon et références compatibles en durée de Phonin 2025 lorsque leur compatibilité est démontrée.
- Gehring & Homberger et références en durée reconstruites.
- Solveurs indépendants pour établir des solutions de référence supplémentaires.

Vérifie les conventions avant toute comparaison.

Distingue :

1. Optimum démontré.
2. Borne inférieure valide.
3. Meilleure solution connue indépendante.
4. Solution publique réévaluée en durée.
5. Résultat de notre propre méthode.

L'objectif académique est d'obtenir moins de 6 % d'écart, mais je veux un calcul scientifiquement honnête.

Si le résultat dépasse 6 %, affiche la véritable valeur.

Si notre algorithme est meilleur que la référence, conserve l'écart négatif et explique qu'il ne s'agit pas automatiquement d'une erreur.

## 8. Sauvegarde automatique

Chaque exécution doit produire un dossier de résultats identifiable et ne doit pas écraser les expériences précédentes.

Je veux retrouver :

- `RESULTATS.csv`
- `BILAN.json`
- Les tournées des véhicules.
- Les horaires de passage.
- Les données de faisabilité.
- La configuration utilisée.
- Les erreurs éventuelles.
- Un fichier de synthèse lisible.

Prévois un identifiant automatique de campagne ou un label unique.

Ajoute une commande permettant de réafficher les résultats d'une campagne existante dans le terminal sans relancer les algorithmes.

## 9. Vérification réelle du travail

C'est une étape obligatoire.

Je veux que tu exécutes réellement :

**A. Les tests unitaires :**
```powershell
python -m pytest tests -q
```

**B. Le validateur du projet :**
```powershell
python scripts/validate_soutenance.py
```

**C. Une instance de 25 clients.**

**D. Une instance de 100 clients.**

**E. Une instance de 200 clients.**

**F. Une instance de 1 000 clients.**

**G. Une comparaison ILS contre hybride renforcé.**

**H. Un test où une méthode ne trouve aucune solution, pour vérifier la gestion des échecs.**

**I. Une commande d'affichage des résultats déjà enregistrés.**

Ne prétends pas avoir exécuté un test qui ne l'a pas été.

Corrige les erreurs rencontrées, puis réexécute les tests concernés.

Vérifie en particulier les chemins Windows, les dépendances, l'encodage UTF-8 et la cohérence des fichiers CSV/JSON.

## 10. Limite de calcul pour la soutenance

Pour la démonstration, je veux pouvoir utiliser un budget de 5 à 30 secondes selon l'instance.

Prévois aussi une limite maximale configurable de 120 secondes par résolution.

Précise si le budget concerne uniquement la recherche ou l'ensemble de l'exécution.

Si certaines opérations natives dépassent légèrement le budget, mesure ce dépassement et signale-le.

Ne promets pas de limite stricte si le programme ne peut pas la garantir.

## 11. Corriger les éventuelles incohérences

Si tu détectes :

- Des résultats incorrects.
- Un calcul de durée erroné.
- Une mauvaise référence.
- Un gap mal calculé.
- Des solutions irréalisables annoncées réalisables.
- Des paramètres CLI incohérents.
- Des fichiers de résultats incomplets.
- Un écart entre le Notebook et le code.

Corrige le problème à sa source.

Mets également à jour le Notebook et la documentation si tes corrections modifient la méthode ou les résultats.

Ne supprime pas les résultats historiques et conserve des sauvegardes.

## 12. Ce que je veux recevoir à la fin

Je veux un fichier **COMMANDES_TERMINAL.md** contenant les commandes PowerShell exactes et vérifiées pour :

1. Tester une instance.
2. Tester plusieurs instances.
3. Tester une famille.
4. Tester une taille.
5. Tester jusqu'à 1 000 clients.
6. Comparer plusieurs méthodes.
7. Afficher les tournées.
8. Réafficher une campagne enregistrée.
9. Afficher les gaps.
10. Lancer les tests unitaires.
11. Vérifier tout le livrable.
12. Préparer la démonstration de soutenance.

Je veux également un script PowerShell de démonstration, si pertinent, permettant de lancer automatiquement une petite instance et d'afficher son bilan.

**IMPORTANT : ne termine pas ton travail avec uniquement des commandes proposées. Tu dois vérifier que les commandes fonctionnent réellement sur le projet actuel.**

À la fin, montre-moi :

- Les commandes exactes à copier-coller.
- Les résultats réels des tests exécutés.
- Les erreurs corrigées.
- Les tests réussis.
- Les fichiers créés ou modifiés.
- Les éventuelles limites restantes.

Je veux pouvoir ouvrir VS Code, copier une commande, appuyer sur Entrée et voir immédiatement les résultats scientifiques importants de mon CVRPTW dans le terminal.