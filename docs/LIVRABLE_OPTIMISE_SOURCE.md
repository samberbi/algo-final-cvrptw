# Livrable final — Optimisation CVRPTW

**CESI — Algorithmique et optimisation — ILS optimisée et recuit décomposé**

Édition expérimentale du 11 novembre 2026.

## 1. Problème et démarche

Une tournée utile doit livrer tous ses clients à l'heure, transporter leurs demandes et revenir au dépôt. Notre objectif expérimental est la distance totale, sous capacités et fenêtres strictes. Les références DIMACS utilisent le même objectif et la même troncature par arc. Le nombre de véhicules est un maximum autorisé ; réduire la distance ne permet jamais de violer une contrainte.

Le sujet initial évoque une durée et du trafic variable. Notre périmètre retient des trajets fixes et symétriques. La distance de benchmark, la somme des durées avec services et attente, et le retour du dernier camion restent des indicateurs distincts. Cette édition optimise la distance ; elle ne revendique pas une optimisation du trafic ni de la somme des durées. Les distances abstraites ne sont pas converties en émissions réelles de CO₂.

La démarche relie modèle, code, vérification et mesures. L'édition initiale ILS/recuit a fourni 1 120 essais ; ses résultats sont conservés et identifiés comme **v1**. La révision **v2** teste ses modifications sur un lot de développement, fige les paramètres puis évalue un lot équilibré. Aucun résultat historique n'est réattribué au nouveau moteur.

{{V2_INTRO}}

<!-- EXEC:setup -->

## 2. Données, horaires et formulation

### 2.1. Une solution et son évaluation

Une solution est une liste de tournées : `[[1,3],[2,4]]` signifie dépôt → 1 → 3 → dépôt et dépôt → 2 → 4 → dépôt. Le dépôt est implicite dans les listes. Les données contiennent coordonnées, demandes, services, fenêtres, matrices de trajet et distance, capacité et flotte maximale.

<!-- EXEC:fig_representation -->

**Lecture.** Les données définissent les contraintes ; les listes proposent un ordre. Le contrôleur recalcule les horaires et la couverture. Une carte satisfaisante visuellement ne prouve pas la faisabilité.

Pour deux visites successives i puis j, avec départ fixé à zéro et service nul au dépôt :

$$a_j=t_i+s_i+c_{ij},\qquad t_j=\max(a_j,e_j),\qquad b_j=t_j+s_j.$$

L'arrivée est a, le début du service t et sa fin b. L'attente est $t_j-a_j$. La fenêtre borne le début : $e_j\le t_j\le l_j$, bornes comprises. Une arrivée anticipée permet d'attendre ; la fin du service peut dépasser $l_j$ si la suite et le retour restent réalisables.

<!-- EXEC:fig_schedule -->

**Lecture.** Le trajet, l'attente et le service occupent trois périodes distinctes. Les fenêtres strictes n'interdisent pas d'arriver avant l'ouverture.

Pour un véhicule k, soit $R_k$ son retour, nul s'il est inutilisé. La distance D somme les arcs parcourus ; la durée totale est $\sum_k R_k$ et le makespan est $\max_k R_k$. Deux solutions de même distance peuvent avoir des attentes différentes.

{{MODEL}}

**Pourquoi le grand M est valide.** Les bornes $0\le t_i,t_j\le H$ impliquent $t_i+s_i+c_{ij}-t_j\le H+s_{\max}+c_{\max}$. Cette valeur désactive donc la propagation d'un arc non utilisé. Des bornes par arc peuvent renforcer le solveur exact sans modifier les solutions autorisées. Le modèle contient de l'ordre de $Kn^2$ variables d'arcs/flots et contraintes : l'exact sert ici aux petits cas.

## 3. Complexité et contrôle exact

Pour une entrée rationnelle et un seuil B, la décision demande s'il existe une solution réalisable de distance au plus B. Un certificat donne les tournées ; couverture, charges, horaires et coût se vérifient en temps polynomial dans la taille binaire de l'entrée.

Un TSP symétrique à coûts positifs se réduit au problème : un véhicule, demandes unitaires, capacité n, services nuls, temps égaux aux coûts, horizon $H=(n+1)c_{\max}$ et fenêtres [0,H]. Les contraintes deviennent non bloquantes et les circuits de même coût se correspondent. La transformation est polynomiale : la décision générale est NP-complète et l'optimisation NP-difficile. Cela n'interdit pas de résoudre exactement certains petits cas.

Le module `controle/plne.py` traduit réellement C1–C8 dans SciPy/HiGHS. Une borne inférieure, une solution réalisable et une preuve d'optimalité ont des statuts distincts. Les dix petits cas de contrôle sont conservés ; ils valident le modèle et ne constituent pas des références pour les grandes instances.

{{EXACT}}

{{EXACT_TEXT}}

## 4. Méthodes et améliorations retenues

### 4.1. Construire un départ commun

Le constructeur essaie douze insertions par regret-2 : une sans bruit, puis onze avec un classement perturbé. Pour un client i, si les deux meilleurs surcoûts réalisables dans des tournées distinctes sont $\Delta_i^{(1)}\le\Delta_i^{(2)}$, son regret est $r_i=\Delta_i^{(2)}-\Delta_i^{(1)}$. Les clients avec peu d'alternatives sont prioritaires. Le meilleur départ complet est gardé ; un échec de construction ne prouve pas une impossibilité.

**Entrées :** instance, graine et nombre d'essais. **Sorties :** listes de tournées et coût/temps de construction. La recherche ne lit aucune BKS. Le même départ est donné aux méthodes comparées et son temps est publié séparément.

{{CODE_CONSTRUCT}}

**Lecture du code.** Chaque essai commence avec des tableaux vides. `repair_fast` est utilisé uniquement pour construire cette première solution ; le meilleur coût réalisable est copié. Les recherches suivantes utilisent des mouvements sur des tournées complètes, sans retirer des clients dans une réserve à réparer.

### 4.2. Recherche locale itérée et recuit directs

L'ILS copie la courante, cherche jusqu'à quatre perturbations réalisables puis applique une recherche locale bornée. Elle accepte la candidate si $D(S')\le1{,}005D(S^*)$, où $S^*$ est le record. Toute amélioration stricte met à jour une copie de l'archive. Après cent cycles sans record, elle repart de cette archive.

Le recuit propose relocate, swap, inversion 2-opt ou échange de fins 2-opt*. Après contrôle de faisabilité, avec $\Delta=D(S')-D(S)$ et $T>0$ :

$$P(\mathrm{acceptation})=1\text{ si }\Delta\le0,\qquad P=\exp(-\Delta/T)\text{ sinon.}$$

Une archive indépendante protège le record. Avec un budget local b et le temps consommé $\tau$, le refroidissement est $T(\tau)=T_0(0{,}005)^{\min(1,\tau/b)}$. Les modes de température et de voisinage ont été comparés, sans supposer qu'un refroidissement plus froid améliore toujours les résultats.

<!-- EXEC:fig_moves -->

**Lecture.** Les mouvements changent ordre ou affectation. Les tournées touchées sont réévaluées ; une baisse géométrique ne compense jamais une surcharge ou un retard.

**`walk` :** reçoit les tableaux et paramètres, propose les mouvements et renvoie le meilleur état ainsi que des compteurs. Le passage ci-dessous est extrait du vrai corps de fonction.

{{CODE_WALK}}

**Lecture.** Le coût marginal est calculé après les contrôles. Un gain est accepté ; une hausse est tirée selon Metropolis. Les compteurs distinguent les refus par capacité, horaires, structure et acceptation probabiliste. Ils concernent les propositions directes, pas tous les candidats internes de recherche locale.

### 4.3. Optimiser des groupes de tournées

Le diagnostic v1 montrait des mouvements rarement réalisables et une difficulté sur R1_10_1. La révision optimise des groupes de tournées géographiquement voisines. Elle conserve les demandes, capacités, services, fenêtres, distances et temps originaux. Les dépôts de chaque groupe représentent le même dépôt physique. La flotte disponible tient compte des tournées laissées à l'extérieur.

L'ILS adapte la taille cible aux longueurs des tournées : pour m tournées utilisées, $G=\max(120,\min(360,8\lceil n/m\rceil))$. Le groupe est une sélection de tournées entières, non une garantie de cardinalité exacte. Sur les petites instances, la recherche reste directe. Le recuit emploie la configuration sélectionnée sur le développement.

Un groupe contient au plus douze tournées. La sous-recherche dispose de 0,2 seconde par appel et peut utiliser jusqu'à trois véhicules supplémentaires, sous la flotte globale restante. Ces limites règlent le voisinage et le travail de recherche ; elles n'autorisent aucune violation du problème initial. La vérification globale contrôle à nouveau le nombre total de véhicules.

<!-- EXEC:fig_v2_groups -->

**Lecture.** Une sous-recherche modifie toutes les tournées choisies avec des solutions complètes. Les clients sont ensuite remappés vers leurs identifiants originaux. Le contrôleur vérifie la solution globale ; elle est remplacée seulement si la distance diminue. Aucun appel de réparation n'est utilisé pendant cette phase.

**`solve` :** reçoit instance, budget, graine et départ éventuel. Il garde une archive, lance les recherches de groupes sous le budget global puis retourne une solution vérifiée. L'extrait montre la réintégration et l'acceptation réelle.

{{CODE_SOLVE}}

### 4.4. Un mouvement complet sur un petit exemple

<!-- EXEC:example -->

<!-- EXEC:fig_v2_example -->

**Lecture.** Les deux solutions illustrées couvrent les mêmes clients avec la même capacité et les mêmes fenêtres. Le mouvement modifie leur affectation et raccourcit les trajets. C'est une démonstration du code sur un jouet, sans BKS ni prétention de performance générale.

### 4.5. Réglages testés et décisions

La calibration comprend six instances à 100 clients et une instance par famille à 1 000 clients, avec trois graines. Des groupes fixes, un voisinage temporel, SWAP*, deux échelles de température puis des groupes adaptatifs sont mesurés. Les essais supplémentaires ont leur protocole distinct. Les configurations sont figées avant la validation ; les résultats défavorables sont conservés.

{{DEVELOPMENT}}

<!-- EXEC:fig_v2_development -->

{{SELECTION_TEXT}}

## 5. Protocole équilibré et statistiques

### 5.1. Instances et budgets

{{PROTOCOL}}

Les douze grandes instances couvrent C1, C2, R1, R2, RC1 et RC2. Elles sont différentes de celles utilisées pour la calibration v2. Certaines géographies existaient déjà dans l'ancienne couverture ALNS : il ne s'agit pas d'une validation totalement aveugle. Les cas diagnostiqués C204 et R1_10_1 sont traités dans une comparaison séparée à vingt graines.

Les grands cas conservent leur résultat à 25 secondes puis reçoivent tous une continuation de 15 secondes depuis l'archive. Ces continuations prolongent les mêmes trajectoires : elles n'ajoutent pas des runs indépendants. Le budget total, le résultat à 25 secondes et les deux phases sont publiés. La construction et le préchauffage sont mesurés séparément.

{{ENVIRONMENT}}

### 5.2. Définition des indicateurs

Pour un essai réalisable e disposant d'une BKS compatible et positive :

$$g_e=100\left(\frac{D_e}{D_e^{\mathrm{BKS}}}-1\right).$$

Une BKS n'est pas nécessairement un optimum prouvé. Un échec reste dans les effectifs et ne reçoit pas de gap nul. Pour m gaps disponibles, $\bar g=m^{-1}\sum_e g_e$ et, si $m\ge2$, $s_g=\sqrt{\sum_e(g_e-\bar g)^2/(m-1)}$. Les écarts-types sont en points de pourcentage. Médiane, quartiles et pires cas complètent la moyenne. Les fréquences sous 5 %, 6 % et 7 % utilisent tous les essais prévus au dénominateur.

Le lot équilibré donne le même poids aux trois tailles, avec le même nombre d'instances et répétitions par taille. La moyenne globale est donc aussi la moyenne des trois moyennes par taille. Elle ne garantit pas le seuil pour chaque instance. Les différences de méthodes sont appariées par instance et graine ; les intervalles bootstrap par graines concernent ce benchmark fixé. Avec cinq blocs, l'incertitude reste exploratoire et la diversité géographique n'est pas remplacée par les répétitions.

Dans l'étude v1, 24 des 28 instances avaient 100 clients : elles pesaient 85,7 % de la moyenne globale, contre 7,1 % pour chacune des deux autres tailles. Dans la validation v2, chacune des trois tailles pèse 33,3 %. Les moyennes globales v1 et v2 ne mesurent donc pas la même population. Le gain algorithmique se juge dans une comparaison appariée à budget égal, et non en soustrayant ces deux moyennes de périmètres différents.

## 6. Résultats de la validation v2

{{SUMMARY}}

{{PAIRED}}

<!-- EXEC:fig_v2_distribution -->

**Lecture.** Chaque boîte mélange la variabilité des graines et celle des instances de sa taille. Elle affiche la médiane et les quartiles ; les points défavorables restent inclus. Il faut lire le tableau par instance pour localiser les difficultés.

{{SIZE_RESULTS}}

{{SIZE_INTERPRETATION}}

<!-- EXEC:fig_v2_large -->

**Lecture.** Chaque barre représente cinq répétitions d'une grande instance ; les traits indiquent un écart-type, pas un intervalle de confiance. Les seuils et les pires cas restent des indicateurs distincts. Le tableau complet comporte BKS, distances, gaps et temps, y compris pour les essais défavorables.

{{LARGE_RESULTS}}

### 6.1. Effet du temps et convergence

{{CONTINUATION}}

<!-- EXEC:fig_v2_convergence -->

**Lecture.** La courbe est la moyenne des meilleurs gaps enregistrés ; la bande décrit les quartiles. Les traces sont reconstruites en escalier, sans inventer d'amélioration entre deux points. Le départ est ancré à zéro. Le passage à la seconde phase est déclaré ; la courbe ne représente pas le déplacement des véhicules.

### 6.2. Comparaison avant/après à budget égal

{{REGRESSION}}

<!-- EXEC:fig_v2_regression -->

**Lecture.** Les lignes relient les mêmes graines depuis le même départ. La version initiale est exécutée à nouveau depuis ses sources figées, dans les mêmes conditions que la version optimisée. Ce lot diagnostique deux cas connus ; il ne se substitue pas à la validation des 36 instances.

### 6.3. Pourquoi certains mouvements échouent

{{DIAGNOSTICS}}

<!-- EXEC:fig_v2_diagnostics -->

**Lecture.** Les proportions concernent les propositions directes. Un rejet temporel signifie que la fenêtre ou le retour devient impossible ; un rejet de capacité révèle une surcharge ; certains tirages ne définissent pas de mouvement utile. Ces compteurs localisent les pertes de travail sans prouver la cause unique d'un mauvais gap.

## 7. Implémentation, vérification et reproduction

Le code actif est `algo/optimized.py`, la boucle directe est dans `algo/iterated.py`, les mouvements dans `algo/direct.py` et les configurations dans `algo/profiles.py`. Le constructeur reste limité au démarrage. `algo/verify.py` recalcule indépendamment couverture unique, charge, fenêtre inclusive, retour et flotte. Les données ne sont pas modifiées pour obtenir un meilleur gap.

La suite inclut les bornes temporelles, les capacités, les arcs nuls du PLNE, les mouvements directs, la protection du record, les insertions comparées à une énumération et l'absence de réparation pendant les groupes. Le notebook exécute ses démonstrations et reconstruit les tableaux depuis les données mesurées ; il ne relance pas les campagnes à chaque lecture.

{{TESTS}}

Les sources et protocoles sont figés dans `results/optimization_v2/`. Les anciens résultats demeurent dans leurs dossiers avec leurs propres versions. La validation actuelle est indiquée par `livraison/VALIDATION.json` et `validation_livraison_ils.json` ; le justificatif ALNS précédent a été déplacé dans son archive.

```powershell
.\.venv\Scripts\python.exe -m pytest tests
.\.venv\Scripts\python.exe cli.py C101 --method ils --seconds 5 --seed 1001
.\.venv\Scripts\python.exe -m streamlit run web/app.py
.\.venv\Scripts\python.exe scripts\analyze_optimization_v2.py --stage validation
.\.venv\Scripts\python.exe scripts\build_optimization_report.py
```

Les scripts de campagne reprennent les fichiers existants sans les remplacer. Une reproduction indépendante doit utiliser un autre dossier de campagne et un protocole distinct. Les exports CSV et JSON permettent de vérifier les moyennes et les solutions sans refaire toutes les recherches. L'interface permet aussi de lancer ses propres expériences et de simuler les horaires d'une solution contrôlée.

En CLI et dans l'interface, le budget d'un appel inclut sa construction si aucun départ n'est fourni. Les budgets du benchmark apparié portent sur l'amélioration depuis les départs communs sauvegardés. Une commande CLI de 25 secondes n'est donc pas une reproduction exacte d'un essai à 25 secondes d'amélioration plus construction.

<!-- EXEC:demo -->

## 8. Limites et conclusion

{{CONCLUSION}}

La capacité à traiter plusieurs milliers de clients n'est pas démontrée par ce lot arrêté à 1 000. Les matrices denses coûtent une mémoire quadratique et le choix des groupes reste heuristique. Les réglages sont évalués sur un lot limité ; ils ne sont pas universels. Le PLNE sert aux petits cas et ne certifie pas les grandes solutions.

Les prochains essais utiles portent sur le temps pour atteindre un seuil, la mémoire maximale, les cas dépassant encore la cible et la diversité des grandes instances. Une modification de paramètre doit être mesurée sur un protocole déclaré. La qualité d'un résultat tient à sa faisabilité, à la définition de sa référence et à la portée exacte de sa comparaison.

## Références

- Sujet CESI, *Algorithmique et optimisation*, pages projet et livrable final.
- Lourenço, Martin et Stützle, *Iterated Local Search*, https://arxiv.org/abs/math/0102188.
- Kirkpatrick, Gelatt et Vecchi, *Optimization by Simulated Annealing*, 1983, https://doi.org/10.1126/science.220.4598.671.
- PyVRP/Instances, convention DIMACS : https://github.com/PyVRP/Instances/blob/7474b068a8effa7f39448b241314b615c9271525/VRPTW/README.md.
- VRPLIB, lecture des instances : https://github.com/PyVRP/VRPLIB.
- SciPy, interface MILP/HiGHS : https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html.
