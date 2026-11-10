# Livrable final — CVRPTW par recherche locale itérée

**Projet CESI — Algorithmique et optimisation**

**ILS et recuit simulé sur mouvements directs, contraintes strictes**

## 1. Contexte, objectif et démarche

Une entreprise de livraison doit affecter ses clients à des camions et choisir leur ordre de visite. Réduire les déplacements n'a de sens que si chaque livraison reste réalisable : quantité transportable, créneau du client et retour au dépôt. Ce travail s'inscrit dans le contexte CesiCDP et de la mobilité durable porté par le sujet ADEME. Les données utilisées sont des benchmarks abstraits ; aucune conversion de leurs distances en émissions réelles de CO₂ n'est revendiquée.

Nous étudions le **CVRPTW**, problème de tournées avec capacité et fenêtres temporelles. La démarche relie une modélisation explicite, une implémentation Python, un vérificateur indépendant et un protocole expérimental. La méthode principale est la **recherche locale itérée (ILS)**. Un **recuit simulé sur mouvements directs** sert de comparaison. Le PLNE précise les contraintes et fournit des références exactes sur de petits cas.

Les résultats de cette édition proviennent de nouvelles expériences. La campagne principale comporte **28 instances et 1 120 essais appariés**, avec 20 graines par instance et par méthode. Les anciennes sorties ALNS sont conservées dans l'historique du dépôt et ne sont pas attribuées à l'ILS. Les cas déjà observés restent des instances connues : l'étude n'est pas une validation aveugle.

<!-- EXEC:setup -->

## 2. Formalisation du problème et contraintes

### 2.1. Données, représentation et hypothèses

Soit $n\in\mathbb N^*$ le nombre de clients, et soit $C=\{1,\ldots,n\}$ leur ensemble. Soit $K\in\mathbb N$ le nombre maximal de véhicules disponibles, et soit $\mathcal K=\{1,\ldots,K\}$ leur ensemble d'indices. Le dépôt physique est noté 0 dans le programme. Pour tout client $i\in C$, soient $q_i\ge0$ sa demande, $s_i\ge0$ la durée de service et $[e_i,l_i]$ sa fenêtre de début de service. Soient $Q>0$ la capacité commune des véhicules et $H>0$ la fermeture du dépôt.

Pour tous points distincts i et j, soient $d_{ij}\ge0$ la distance et $c_{ij}\ge0$ le temps de trajet. Les matrices sont fixes et symétriques dans le périmètre du projet. Les fenêtres satisfont $0\le e_i\le l_i\le H$, pour tout $i\in C$. Les départs sont au temps zéro. Chaque demande est indivisible et chaque véhicule réalise au plus une tournée.

Une solution est une liste de tournées ordonnées. Par exemple, `[[1,3],[2,4]]` représente les circuits dépôt → 1 → 3 → dépôt et dépôt → 2 → 4 → dépôt. Les dépôts sont implicites dans le code. Une liste décrit un ordre de passage ; ses horaires sont recalculés.

<!-- EXEC:fig_representation -->

**Lecture du schéma.** Les données définissent les possibilités et les contraintes. Une solution propose les ordres de visite. L'évaluation recalcule ensuite couverture, charges, horaires et coût. Une apparence géographiquement satisfaisante ne suffit pas à établir la faisabilité.

### 2.2. Arrivée, attente, service et deux objectifs

Fixons un véhicule $k\in\mathcal K$ et deux visites successives i puis j de sa tournée, où $j\in C$. Soient $a_j$ l'arrivée, $t_j$ le début du service et $b_j$ sa fin. Avec $t_0=s_0=0$ au départ du dépôt, les horaires au plus tôt sont :

$$a_j=t_i+s_i+c_{ij},\qquad t_j=\max(a_j,e_j),\qquad b_j=t_j+s_j.$$

Ces égalités s'appliquent aux visites successives de chaque tournée, et non simultanément à tous les arcs du graphe. Pour tout client j visité, l'attente est $w_j=t_j-a_j\ge0$. Le service respecte la fenêtre si $e_j\le t_j\le l_j$. Une arrivée anticipée est autorisée ; commencer exactement à la fermeture l'est aussi. La fin du service peut dépasser $l_j$, sous réserve de respecter la suite et le retour au dépôt.

<!-- EXEC:fig_schedule -->

**Lecture du schéma.** Dans l'exemple, le trajet finit à 8, le camion attend jusqu'à 15 puis sert jusqu'à 20. La fenêtre [15 ; 25] borne le début du service. La zone orange explique pourquoi distance parcourue et durée complète ne sont pas des indicateurs interchangeables.

<!-- EXEC:toy -->

Dans l'exemple à deux clients, les deux ordres parcourent 18 unités. L'ordre [1,2] dure 34 unités et l'ordre [2,1] en dure 28 : la différence vient de l'attente. Les services totalisent 9 unités dans les deux cas.

Pour tout véhicule $k\in\mathcal K$, soit $E_k$ l'ensemble des arcs effectivement parcourus dans sa tournée, retour compris, et soit $R_k$ son heure de retour ; posons $R_k=0$ si le véhicule est inutilisé. Les deux objectifs sont :

$$D=\sum_{k\in\mathcal K}\sum_{(i,j)\in E_k}d_{ij},\qquad F_{\mathrm{durée}}=\sum_{k\in\mathcal K}R_k.$$

Le benchmark minimise D, sans priorité au nombre de camions. La somme des durées comprend trajets, services et attentes. Elle diffère également du makespan, qui est le maximum des retours des véhicules utilisés. Cette édition compare les deux méthodes sur la distance ; aucune BKS en durée n'est utilisée pour les classer.

{{MODEL}}

## 3. Complexité et rôle de l'approche exacte

### 3.1. Version de décision et appartenance à NP

Soit une instance rationnelle du problème et soit $B\in\mathbb Q_{\ge0}$ un seuil. La question décisionnelle est : existe-t-il une solution réalisable de distance totale au plus B ? Une solution fournit les listes ordonnées des clients. Le vérificateur contrôle les identifiants, l'unicité, les charges, les horaires et le coût en temps polynomial dans la taille de l'entrée. L'encodage des nombres est supposé binaire.

### 3.2. Réduction depuis le voyageur de commerce

Considérons un TSP symétrique à coûts strictement positifs sur un dépôt et n clients, avec seuil B. Construisons une instance CVRPTW avec un véhicule, $q_i=1$ et $s_i=0$ pour tout $i\in C$, et une capacité $Q=n$. Pour tous les arcs, prenons temps et distances égaux aux coûts TSP. Soit $c_{\max}$ le plus grand de ces coûts ; fixons $H=(n+1)c_{\max}$ et toutes les fenêtres à [0,H]. Tout circuit hamiltonien respecte alors capacités et horaires.

Un tour TSP de coût au plus B correspond exactement à une tournée CVRPTW de coût au plus B, et réciproquement. La transformation est polynomiale. La décision générale est NP-complète et l'optimisation NP-difficile. Ce résultat ne signifie pas que tout petit cas est difficile ni qu'une métaheuristique garantit un optimum.

### 3.3. Pourquoi résoudre aussi de petits cas exactement ?

Le module `controle/plne.py` implémente réellement les variables et contraintes du modèle par SciPy/HiGHS. Il restitue une solution réalisable éventuelle, une borne, un statut et le temps réel. Le statut « optimal » est réservé à une preuve du solveur. Une limite de temps avec incumbent ne devient pas une preuve d'optimalité. L'ancien oracle `controle/exact.py` reste un contrôle indépendant par énumération et programmation dynamique sur de très petits cas.

<!-- EXEC:fig_validation -->

**Lecture du schéma.** La formalisation définit les solutions autorisées. Les petites résolutions exactes servent à vérifier le modèle et à mesurer un écart à un optimum certifié. Les campagnes réalistes évaluent les métaheuristiques par répétitions et références publiées. Ces trois rôles sont complémentaires.

<!-- EXEC:toy_exact -->

## 4. Méthodes retenues et justification

### 4.1. Solutions réalisables et constructeur commun

Soit $\mathcal S$ l'ensemble des listes de tournées satisfaisant C1–C8. Pour toute solution $S\in\mathcal S$, soit $D(S)$ sa distance totale. Les deux moteurs explorent des solutions complètes de $\mathcal S$ et conservent une archive du meilleur coût trouvé. Ils ne lisent aucune BKS.

La construction utilise regret-2. Pour tout client non affecté i, soient $c_{i,1}\le c_{i,2}$ les surcoûts de ses deux meilleures insertions réalisables dans des tournées distinctes. Lorsque ces alternatives existent, son regret est $r_i=c_{i,2}-c_{i,1}$. Les clients avec trop peu d'alternatives sont prioritaires ; parmi les autres, le constructeur favorise le plus grand regret. Ainsi, des coûts 4 et 20 donnent un regret 16, contre 2 pour des coûts 5 et 7.

La capacité, le début de service et la possibilité de poursuivre la tournée sont contrôlés pour chaque insertion. Douze constructions sont essayées, la première sans bruit, les suivantes avec perturbation des classements. Le meilleur départ réalisable est conservé. Cette insertion est uniquement un constructeur : les recherches ILS et recuit n'utilisent pas la destruction/réparation ALNS.

Dans le benchmark apparié, une construction commune est calculée une fois pour chaque couple instance/graine. Les mêmes tournées sont fournies aux deux méthodes ; son temps est enregistré séparément. Un échec du constructeur est conservé, sans être assimilé à une impossibilité mathématique.

### 4.2. Voisinages directs et contrôles

Pour toute solution $S\in\mathcal S$, nous considérons des voisins obtenus par déplacement, échange, inversion de segment ou échange de fins de tournées. Les modifications retenues conservent la couverture des clients et sont vérifiées sur les tournées affectées. Une faible probabilité permet de déplacer un client vers un véhicule encore inutilisé, sous la limite de flotte ; ouvrir un véhicule ne porte aucun coût fixe.

<!-- EXEC:fig_moves -->

**Lecture du schéma.** Relocate modifie l'affectation d'un client, swap échange deux clients et 2-opt* échange des fins de tournées. L'inversion 2-opt est également implémentée. Une réduction géométrique ne suffit pas : capacité et horaires sont recalculés avant acceptation.

Pour limiter le coût, les propositions privilégient les 24 voisins géographiques d'un client, avec une part de tirages globaux. La recherche locale ILS applique des améliorations strictes, avec un plafond de dix mouvements par appel et de petites chaînes de déplacement. Elle n'est donc pas présentée comme une preuve d'optimalité locale sur tous les voisins possibles.

### 4.3. ILS : perturber puis améliorer

L'ILS effectue une succession de perturbations et d'améliorations locales. La perturbation cherche jusqu'à quatre mouvements directs réalisables, avec un nombre d'essais borné pour chacun. Ces mouvements peuvent augmenter la distance afin de changer l'organisation explorée. La recherche locale cherche ensuite des gains. Les voisinages restent fixes ; il n'y a ni apprentissage de poids de retraits, ni mécanisme tabou, ni procédure VNS.

Pour tout indice de cycle $t\in\mathbb N$, soient $S_t\in\mathcal S$ la solution courante à la fin du cycle t, $S^*\in\mathcal S$ l'archive et $S'\in\mathcal S$ la candidate après amélioration. Soit $\varepsilon=0{,}005$. La règle de poursuite est :

$$S_{t+1}=\begin{cases}S'&\text{si }D(S')\le(1+\varepsilon)D(S^*),\\S_t&\text{sinon.}\end{cases}$$

Pour tout cycle t, l'archive est remplacée si $D(S')<D(S^*)$. La tolérance au record autorise une exploration limitée au voisinage du meilleur coût. Après cent cycles sans nouveau meilleur, la recherche repart de l'archive. Ces réglages sont des choix empiriques fixés pour la campagne, puis examinés dans l'étude séparée de sensibilité.

<!-- EXEC:fig_ils -->

**Lecture du schéma.** Le constructeur fournit un départ ; les cycles modifient ensuite des tournées complètes. La perturbation fournit de la diversité, la recherche locale affine, la règle de poursuite choisit le prochain départ et l'archive protège le meilleur résultat. Seules les trois dernières étapes sont répétées pendant la recherche.

Nous retenons l'ILS pour sa structure explicable et son adaptation aux mouvements déjà contrôlables du projet. Sa limite attendue est la difficulté de perturber utilement des tournées à fenêtres serrées. Cette justification motive l'expérience ; les résultats doivent déterminer sa qualité réelle.

### 4.4. Recuit simulé sur mouvements directs

Le recuit propose les mêmes types de mouvements sur des solutions complètes. Soient $S\in\mathcal S$ la courante, $S'\in\mathcal S$ une candidate réalisable et $\Delta=D(S')-D(S)$. Pour une température réelle $T>0$, la probabilité d'acceptation est :

$$P(\mathrm{acceptation}\mid\Delta,T)=\begin{cases}1&\text{si }\Delta\le0,\\\exp(-\Delta/T)&\text{si }\Delta>0.\end{cases}$$

Une température élevée rend les hausses de coût plus souvent acceptées. Les solutions violant une contrainte ne sont pas soumises à ce tirage : elles sont rejetées auparavant. Une archive indépendante conserve le meilleur coût, même lorsque la courante se dégrade.

Soit $b>0$ le budget de recherche et soit $\tau\ge0$ le temps déjà consommé. Posons $p(\tau)=\min(1,\tau/b)$. Pour les coûts strictement positifs des benchmarks, la température commence à $T_0=\rho D_0$, avec $\rho=0{,}02$ et $D_0$ le coût de construction, puis suit :

$$T(\tau)=T_0(0{,}005)^{p(\tau)}.$$

Le code protège numériquement les températures nulles et travaille à l'échelle dix, ce qui laisse le rapport $\Delta/T$ inchangé. Le refroidissement dépend du temps, pas du nombre d'améliorations. Au début, il facilite l'exploration ; à la fin, il réduit les détours acceptés.

<!-- EXEC:fig_temperature -->

**Lecture du graphique théorique.** À gauche, pour une même dégradation, la courbe de température élevée donne la plus forte probabilité. Pour une même température, une forte dégradation est moins souvent acceptée. À droite, la température passe de sa valeur initiale à 0,5 % de celle-ci lorsque le budget est consommé. Le refroidissement fait progressivement passer de l'exploration à une acceptation plus sélective. Ces courbes expliquent une règle ; l'étude expérimentale évalue son efficacité.

<!-- EXEC:fig_sa -->

**Lecture du schéma.** Le recuit traite les propositions une à une et décide selon leur différence de coût et la température. L'ILS alterne une perturbation et une amélioration locale bornée. Les deux moteurs partagent le départ et les contraintes, mais leurs unités d'itération n'ont pas le même sens.

## 5. Implémentation, vérification et arrêt

`algo/model.py` définit les données et invariants ; `algo/data.py` applique la convention DIMACS et charge les références dans une fonction séparée. `algo/iterated.py` orchestre ILS et recuit. `algo/direct.py` compile les quatre types de propositions avec Numba ; `algo/kernels.py` fournit la construction et la recherche locale. L'API publique est `algo/solver.py`. `algo/verify.py` recalcule les clients, charges, horaires, retours et coûts sans reprendre les caches de recherche.

L'arrêt dépend du temps réel de recherche, avec une borne de propositions supplémentaire. Dans les expériences appariées, la construction est commune et hors du budget d'amélioration ; elle reste mesurée. Dans la CLI, le budget commence à l'entrée du solveur et inclut la construction si aucun départ n'est fourni. Un calcul atomique commencé avant la fin du budget peut terminer après : le temps effectivement consommé est publié.

Pour une tournée de longueur L, son évaluation complète coûte un temps linéaire en L. Les matrices denses demandent une mémoire quadratique en n. Limiter les voisins réduit les essais mais ne garantit pas une croissance linéaire du temps total. Le constructeur peut être coûteux sur les grands cas ; Numba accélère les boucles sans modifier leur complexité asymptotique.

Les tests contrôlent couverture, capacité, flotte, attente, bornes temporelles, retour, protection de l'archive et concordance entre évaluations. Des tests spécifiques vérifient que la recherche ILS/recuit n'appelle pas le réparateur après initialisation, que les mouvements directs conservent une solution complète, et que le PLNE coïncide avec l'énumération sur de petits cas, y compris avec des arcs nuls.

{{TESTS}}

### 5.1. Lecture du code et déroulement d'un appel

`Settings` regroupe les réglages et refuse les budgets non positifs ou les méthodes inconnues. `construct` crée des tableaux de tournées vides, appelle l'insertion regret-2, calcule le coût de chaque construction complète et garde la meilleure. `encode` traduit les listes Python en tableaux entiers pour Numba ; `decode` restitue les listes à sauvegarder. Les cases vides des tableaux ne sont pas des clients supplémentaires.

Dans `solve`, un départ fourni est vérifié ; sinon le constructeur est appelé. Les matrices de voisinage sont préparées et une copie devient l'archive. Les propositions modifient les tableaux courants ou une copie candidate. Le meilleur résultat est copié avant de poursuivre : cette copie évite qu'une modification ultérieure détruise le record.

```text
ILS :
  construire ou vérifier le départ ; initialiser courant et archive
  jusqu'au budget :
    copier le courant ; chercher jusqu'à quatre perturbations réalisables
    appliquer la recherche locale bornée sur cette copie
    si son coût est dans la tolérance au record : elle devient courante
    si elle améliore le record : copier vers l'archive
    après cent cycles sans record : repartir de l'archive
  vérifier et retourner l'archive

Recuit :
  utiliser le même départ ; initialiser courant et archive
  jusqu'au budget, par lots bornés de propositions :
    calculer la température selon le temps consommé
    proposer un mouvement et contrôler les tournées touchées
    accepter tout gain ; tirer l'acceptation des hausses selon exp(-delta/T)
    conserver une copie de tout nouveau record
  vérifier et retourner l'archive
```

Dans `direct.walk`, le type de mouvement est tiré au hasard. La plupart des partenaires sont des voisins géographiques ; les autres sont tirés globalement. `route_eval` recalcule les horaires au plus tôt et rejette surcharge, retard ou retour tardif. Le mode perturbation s'arrête au premier mouvement réalisable ; le mode recuit enchaîne ses propositions avec la règle d'acceptation. La recherche locale utilise les routines compilées existantes, sans appeler le retrait/réparation pendant les cycles.

Le résultat JSON contient notamment `routes`, `cost`, `runtime_s`, `settings`, `trace`, `accepted` et `metrics`. `iterations` compte des propositions de perturbation ou de recuit ; il ne compte pas tous les candidats évalués à l'intérieur de la recherche locale. Les compteurs ILS et recuit ne servent donc pas de mesure comparable d'effort. `metrics` provient du vérificateur final indépendant.

## 6. Plan d'expérience et définition des statistiques

### 6.1. Instances, répétitions et budgets

Les 24 cas à 100 clients sont les quatre premiers identifiants de chacune des six familles Solomon C1, C2, R1, R2, RC1 et RC2. Les quatre autres sont C1_2_1, R1_2_1, C1_10_1 et R1_10_1. Chaque instance reçoit les vingt graines 101 à 120 et les deux méthodes, soit $28\times20\times2=1120$ essais. Ce lot dépasse les vingt instances variées demandées par le sujet ; celui-ci ne prescrit pas un nombre de répétitions.

Les budgets d'amélioration sont identiques entre méthodes : 5 secondes à 100 clients, 6 à 200 et 25 à 1 000. L'ordre des couples et l'ordre des méthodes dans un couple sont randomisés de façon reproductible. Quatre processus exécutent les couples sur des processeurs logiques distincts ; leurs ressources physiques restent partagées. Les études supplémentaires utilisent un autre processeur logique. La construction, le préchauffage, le chargement et les limites de cette organisation sont explicités, sans comparaison de vitesse intrinsèque avec les anciennes campagnes ou d'autres ordinateurs.

{{ENVIRONMENT}}

### 6.2. Qualité, dispersion et comparaison appariée

Soit E l'ensemble des essais prévus et soit $E_F\subseteq E$ celui des essais réalisables disposant d'une référence de distance strictement positive. Pour tout essai $e\in E_F$, soient $D_e$ sa distance et $D_e^{\mathrm{BKS}}$ la référence. Son gap est :

$$g_e=100\left(\frac{D_e}{D_e^{\mathrm{BKS}}}-1\right)\qquad\forall e\in E_F.$$

Une BKS est une meilleure solution publiée, pas nécessairement un optimum prouvé. Un échec ne reçoit pas un gap nul. Soit $m=|E_F|$. Pour $m\ge1$, la moyenne est $\bar g=m^{-1}\sum_{e\in E_F}g_e$ ; pour $m\ge2$, l'écart-type échantillonnal est :

$$s_g=\sqrt{\frac{1}{m-1}\sum_{e\in E_F}(g_e-\bar g)^2}.$$

La médiane et les quartiles décrivent la distribution ; l'écart interquartile est $IQR=Q_3-Q_1$. L'écart-type est exprimé en points de pourcentage. Pour un seuil h, la fréquence de succès est $|\{e\in E_F:g_e<h\}|/|E|$, avec dénominateur explicite. Les seuils sont stricts.

Pour chaque instance i et chaque graine s du protocole, soit $\delta_{i,s}=g_{i,s}^{\mathrm{ILS}}-g_{i,s}^{\mathrm{recuit}}$ lorsque les deux résultats sont réalisables. Une valeur négative favorise l'ILS. Les différences sont appariées ; plusieurs graines d'une instance ne représentent pas plusieurs géographies.

L'incertitude de la différence moyenne est décrite par un bootstrap de 10 000 rééchantillonnages des vingt blocs de graines, en préservant les couples et l'ensemble fixe d'instances. Cette description concerne la variabilité algorithmique sur le benchmark connu ; elle ne constitue pas un intervalle de généralisation à toutes les nouvelles instances. Aucun classement universel n'est déduit d'une seule moyenne.

### 6.3. Pourquoi ces analyses ?

La moyenne mesure le niveau global ; la médiane complète sa lecture en présence de valeurs extrêmes. Les quartiles et l'écart-type décrivent la robustesse entre répétitions. Le pire gap et les fréquences sous les seuils empêchent qu'une bonne moyenne masque des cas défavorables. Les courbes de convergence montrent quand les gains apparaissent et si le budget supplémentaire est encore utile. Les compteurs de propositions sont interprétés selon la méthode, car un cycle ILS et une proposition du recuit ne sont pas équivalents.

## 7. Résultats mesurés du benchmark principal

{{SUMMARY}}

{{PAIRED_TEXT}}

{{SIZES}}

{{SIZE_TEXT}}

<!-- EXEC:fig_dispersion -->

**Lecture et portée.** Chaque boîte résume les gaps d'une méthode pour une taille donnée. Le trait central est la médiane, le symbole supplémentaire la moyenne, et la boîte couvre Q1 à Q3. Les points éloignés restent dans les statistiques. La dispersion mélange ici différences entre instances et entre graines ; le détail par instance complète cette vue.

<!-- EXEC:fig_paired -->

**Lecture et portée.** Chaque point compare les deux méthodes sur une même instance et une même graine. Sous la diagonale, le gap ILS est plus faible ; au-dessus, le recuit est meilleur. Les égalités restent visibles sur la diagonale. Cette figure montre les différences appariées sans transformer les graines en problèmes indépendants.

### 7.1. Détail par instance

{{INSTANCES100}}

{{FAMILIES}}

Le regroupement par famille ci-dessus concerne uniquement les cas à 100 clients, pour ne pas y mélanger les deux grandes tailles. Il décrit quatre instances par famille et vingt graines par instance. Les préfixes distinguent des structures géographiques et temporelles ; une moyenne de famille ne supprime pas les différences entre instances. Lire ensemble moyenne, dispersion et pire essai évite de masquer un cas difficile derrière les cas faciles.

<!-- EXEC:fig_gaps100 -->

**Lecture et portée.** Les barres indiquent les moyennes des vingt graines ; les traits représentent un écart-type de part et d'autre, et non un intervalle de confiance. Une barre faible et peu dispersée indique de bons résultats observés sur cette instance. Les moyennes ne remplacent ni les pires essais ni les taux de faisabilité publiés.

{{LARGE}}

<!-- EXEC:fig_gaps1000 -->

**Lecture et portée.** Ces deux grands problèmes disposent chacun de vingt graines par méthode. Leurs résultats renseignent ces structures précises ; ils ne suffisent pas à garantir un seuil sur toutes les instances de mille clients. Les temps réels et le budget de 25 secondes doivent être lus avec les gaps.

### 7.2. Convergence de l'algorithme au cours du calcul

{{CONVERGENCE}}

Le tableau compare les départs communs aux archives finales. Le gain des derniers 20 % est la baisse moyenne de gap entre 80 % du budget et le résultat final, y compris la dernière opération. « Records tardifs » compte les essais dont le coût final est strictement meilleur que l'archive observée à 80 % du budget. Ces chiffres permettent de distinguer une amélioration encore active d'une courbe devenue presque plate ; ils ne donnent pas une garantie pour un budget supérieur.

Les figures suivantes reconstruisent le meilleur coût en fonction du temps réel par interpolation en escalier des traces enregistrées. Pour chaque taille et méthode, la ligne est la **moyenne des gaps** et la bande l'intervalle interquartile. La valeur initiale est ancrée au temps zéro. Après la fin d'un run, son archive reste constante. Les dernières opérations atomiques sont présentes avec leur temps réel.

<!-- EXEC:fig_convergence100 -->

**Interprétation à 100 clients.** Une descente rapide indique des gains précoces ; un plateau signifie qu'aucun meilleur résultat n'est enregistré pendant cet intervalle. La bande décrit la variabilité, sans constituer une preuve d'optimalité ou une garantie pour un prochain run. Les méthodes sont comparées sur le temps, et non sur des compteurs d'itérations de sens différent.

<!-- EXEC:fig_convergence200 -->

**Interprétation à 200 clients.** Le même traitement porte sur les deux instances et vingt graines chacune. La courbe met en évidence les améliorations disponibles pendant les six secondes et la dispersion entre les trajectoires. La taille et la structure diffèrent des cas à 100 clients : ce n'est pas une expérience où seule la taille varie.

<!-- EXEC:fig_convergence1000 -->

**Interprétation à 1 000 clients.** Une diminution encore présente près de l'échéance suggère qu'un budget plus long mérite une expérience dédiée ; un plateau peut venir d'un manque de mouvements utiles ou du réglage de la recherche. La figure seule ne permet pas de distinguer ces causes. Les deux cas ne représentent pas l'intégralité des grandes instances publiques.

<!-- EXEC:fig_times -->

**Lecture et portée.** Les temps sont proches des budgets par construction. Le nuage ne prouve donc pas une loi de complexité empirique en fonction de n. Le second panneau met qualité et durée en regard ; les dépassements atomiques et les conditions de calcul restent explicités.

### 7.3. Temps de calcul avec un effort de propositions fixé

Une expérience supplémentaire impose 50 000 propositions à chaque appel, avec une limite de sécurité de trente secondes, jamais atteinte. Les cas C101, R101, C1_2_1, R1_2_1, C1_10_1 et R1_10_1 reçoivent les graines 101 à 103 et les deux méthodes, soit 36 essais. Les départs sauvegardés de la campagne principale sont réutilisés, la construction et le préchauffage restant hors temps. Les appels sont exécutés séquentiellement sur un processeur logique fixé.

{{SCALING}}

<!-- EXEC:fig_scaling -->

**Lecture et portée.** Le graphique montre le temps nécessaire au nombre fixé de propositions, avec les six observations de chaque taille et méthode. Il complète les budgets imposés de la campagne principale. Une proposition ILS peut déclencher une recherche locale dont les évaluations internes ne sont pas comptées dans ce nombre ; les unités de travail des deux méthodes restent différentes. Le recuit s'arrête ici au compteur avant de parcourir son refroidissement de trente secondes : cette expérience mesure le temps d'appel, pas sa qualité finale. La variation observée dépend à la fois de n, des tournées et des contraintes ; trois tailles et deux familles ne démontrent pas un ordre asymptotique universel.

## 8. Validation exacte, paramètres et changements des contraintes

### 8.1. Confrontation au PLNE sur de petits cas

Dix cas synthétiques reproductibles couvrent 4, 6, 8, 10 et 12 clients, avec deux graines de génération par taille. Leurs fenêtres sont construites autour de tournées réalisables et leur capacité est connue ; ce lot ne représente pas toutes les difficultés possibles. HiGHS reçoit huit secondes par cas. Les deux métaheuristiques reçoivent chacune cinq graines et 0,2 seconde d'amélioration depuis des départs communs.

{{EXACT}}

{{EXACT_INTERPRETATION}}

Les gaps aux optimums ne sont calculés que pour les cas où l'optimalité est certifiée. En présence d'une limite de temps, borne et incumbent restent distincts. Une sous-instance n'hérite pas du coût optimal d'un problème plus grand. Ces résultats valident un lien modèle/code et une qualité sur petits cas ; ils ne remplacent pas le benchmark principal.

### 8.2. Sensibilité des réglages des méthodes

Cette étude séparée utilise C105, C205, R105, R205, RC105 et RC205, trois graines et deux secondes par essai. Les variantes modifient un réglage à la fois : intensité de perturbation ILS, tolérance au record, présence de la recherche locale, ou température initiale du recuit. La configuration principale est conservée ; ces diagnostics ne servent pas à sélectionner rétroactivement ses meilleurs résultats.

{{SENS}}

<!-- EXEC:fig_sensitivity -->

**Lecture et portée.** Une moyenne plus faible indique un meilleur écart observé sur ces dix-huit essais d'une variante. Une perturbation trop faible peut revenir vers la même organisation ; une perturbation plus forte peut rendre les améliorations coûteuses. L'absence de recherche locale teste son rôle dans l'ILS. Une température modifiée agit sur les acceptations du recuit. Ces interprétations sont des mécanismes plausibles ; les chiffres déterminent les observations effectives.

{{SENS_TEXT}}

### 8.3. Réaction aux capacités, à la flotte et aux fenêtres

Pour les mêmes six instances et trois graines, sept scénarios font varier un seul facteur à la fois : original ; capacité multipliée par 0,8 ou 1,2 ; largeur des fenêtres clients multipliée par 0,7 ou 1,3 autour de leur centre, avec bornes dans l'horizon ; flotte multipliée par 0,8 ou 1,2 puis arrondie par excès. Les deux méthodes disposent de deux secondes. Une nouvelle construction commune est calculée pour chaque scénario.

La demande totale, les coordonnées et les services restent fixes. Les variantes peuvent être mathématiquement impossibles ou difficiles à construire. Une impossibilité n'est annoncée que lorsqu'une condition nécessaire la prouve ; les autres absences de solution restent des échecs de construction. **Les variantes modifiées n'ont pas de BKS validée : aucun gap à la référence originale n'est annoncé.**

{{SCENARIOS}}

<!-- EXEC:fig_constraints -->

**Lecture et portée.** Les barres indiquent la proportion de solutions réalisables parmi les dix-huit tentatives prévues de chaque scénario et méthode. La faisabilité est évaluée avant les moyennes de distance ou d'attente. Un taux plus faible sous une contrainte renforcée peut révéler une limite du modèle disponible ou du constructeur ; il ne prouve pas à lui seul l'inexistence de solutions.

{{SCENARIOS_TEXT}}

Une fenêtre plus large augmente l'ensemble des possibilités mathématiques, mais une métaheuristique sous budget peut malgré tout produire un résultat moins bon sur un essai. Une charge plus proche de Q ou une marge horaire faible dans une solution dépend également de l'algorithme : ces indicateurs ne doivent pas être confondus avec les caractéristiques d'entrée de l'instance.

## 9. Simulation et vérification des solutions

L'interface locale permet de choisir méthode, instance et graine, lancer des expériences, puis rejouer une solution vérifiée. La simulation propose lecture/pause, vitesse et curseur temporel. Elle distingue trajets, attentes et services ; une livraison est terminée à la fin du service. L'inspecteur montre charge initiale/restante, fenêtre, arrivée, début, fin et retour face à la fermeture du dépôt. Les tableaux de contrôle couvrent tous les clients, pas seulement ceux visibles sur la carte.

<!-- EXEC:fig_routes -->

{{EXAMPLE}}

**Lecture de la carte.** Le carré représente le dépôt et les lignes les tournées du run ILS le plus défavorable à 100 clients du lot principal. Choisir ce cas évite de montrer uniquement une réussite favorable. Les segments sont des trajets entre coordonnées de benchmark. Croisements et détours apparents ne prouvent pas un défaut, car les horaires et charges contraignent les affectations.

<!-- EXEC:fig_windows -->

**Lecture du contrôle temporel.** Pour les premiers clients d'une tournée de ce même run, les points bleus sont les débuts de service, à comparer aux fenêtres grises. L'orange représente l'attente et le vert le service. Seul le début doit être dans la fenêtre. L'image illustre quelques clients ; le vérificateur contrôle la solution complète.

La convergence de l'algorithme décrit le calcul qui produit une solution. L'animation des camions rejoue ensuite ses horaires : ce sont deux chronologies distinctes. La simulation n'introduit ni trafic dynamique ni validation routière réelle.

## 10. Limites et améliorations justifiées

Les contraintes strictes rendent beaucoup de propositions irréalisables. L'ILS dépend du nombre de perturbations et de la recherche locale bornée ; le recuit dépend du refroidissement et des types de mouvements accessibles. Les listes de voisins réduisent le travail mais peuvent masquer un échange éloigné. Une bonne performance moyenne ne garantit pas le pire gap d'un futur essai.

Les vingt graines décrivent mieux la variabilité que quelques essais, sans garantir la détection d'événements rares. Les instances partagent des familles et parfois des structures : le bootstrap conditionnel au benchmark ne démontre pas une généralisation à toutes les géographies. Les dix cas exacts restent petits et construits ; les échecs de preuve sous limite de temps font partie du bilan.

Les budgets varient selon la taille. Une véritable étude de montée en charge doit compléter ces mesures par un effort identique, un coût par mouvement ou un temps pour atteindre une qualité fixée. Les processus partagent caches, mémoire, refroidissement et charge système ; aucun rapport de vitesse universel n'est déduit de ce poste.

Les axes suivants sont à tester sur des lots déclarés : mesurer les échecs de perturbation sous fenêtres serrées, enrichir les échanges de petites chaînes, comparer plusieurs tailles de listes de voisins, étudier le temps pour atteindre un seuil et prolonger les grands cas en conservant les résultats initiaux. Les réglages ne doivent pas être ajustés sur le lot final puis présentés comme une validation indépendante.

## 11. Reproduction, traçabilité et démonstration

Le protocole et les sources figées sont dans `results/revision_ils/protocol.json` et `source/`. Chaque run possède son JSON, ses tournées, paramètres, trace, temps et validation. Les départs communs sont dans `initials/`. Les études supplémentaires ont leur propre protocole. Les tableaux complets et empreintes permettent de reconstruire l'analyse. Le notebook exécute ses lectures, figures et petits contrôles ; il ne relance pas les 1 120 recherches à chaque ouverture.

```powershell
.\.venv\Scripts\python.exe -m pytest tests
.\.venv\Scripts\python.exe cli.py C101 --method ils --seconds 2 --seed 101
.\.venv\Scripts\python.exe cli.py C101 --method sa --seconds 2 --seed 101
.\.venv\Scripts\python.exe scripts\run_ils_benchmark.py --workers 4
.\.venv\Scripts\python.exe scripts\run_ils_studies.py
.\.venv\Scripts\python.exe scripts\run_ils_scaling.py
.\.venv\Scripts\python.exe scripts\validate_ils_artifacts.py
.\.venv\Scripts\python.exe scripts\build_ils_report.py
.\.venv\Scripts\python.exe -m streamlit run web/app.py
```

Les reprises conservent les fichiers existants et vérifient le protocole ; elles n'annoncent pas de nouvelles mesures lorsqu'elles relisent des runs terminés. Une reproduction indépendante exige un nouveau dossier de résultats et un protocole explicitement distinct. Pour la soutenance, une petite démonstration suffit : rappeler le contexte et l'objectif, montrer un calcul court, vérifier les contraintes, puis commenter les résultats agrégés et leurs limites.

<!-- EXEC:demo -->

## 12. Conclusion

Le bilan d'avancement distingue les réalisations et les pistes restant à évaluer :

| Étape | État dans cette livraison | Suite justifiée |
|---|---|---|
| Modèle et vérificateur | Contraintes formalisées, PLNE implémenté, tests et contrôles indépendants | Étendre les cas limites si de nouvelles contraintes sont ajoutées |
| ILS et recuit | Deux moteurs exécutables, sans ALNS dans la recherche active | Tester d'autres intensités et listes de voisins sur un lot déclaré |
| Étude principale | 28 instances, vingt graines, mesures et convergence sauvegardées | Valider sur de nouvelles instances et prolonger les cas difficiles |
| Études complémentaires | Petits cas exacts, paramètres et contraintes modifiées | Répéter plus largement les sensibilités avant de changer les réglages |
| Restitution | Notebook, rapport, schémas expliqués et simulation contrôlable | Préparer la démonstration sur le poste de soutenance |

{{CONCLUSION}}

La valeur du travail vient de l'accord entre la définition du problème, le comportement du code, les contrôles indépendants et les expériences traçables. L'ILS constitue une alternative réellement implémentée à l'ancienne ALNS ; le recuit fournit une comparaison sous les mêmes règles. Les résultats doivent être défendus dans leur périmètre et leurs budgets, sans transformer une moyenne favorable en garantie universelle.

## Références

- CESI, sujet « Algorithmique et optimisation » et consignes du livrable final communiquées par l'utilisateur.
- Lourenço, Martin et Stützle, *Iterated Local Search*, [texte des auteurs](https://arxiv.org/abs/math/0102188).
- Kirkpatrick, Gelatt et Vecchi, *Optimization by Simulated Annealing*, 1983, [publication](https://doi.org/10.1126/science.220.4598.671).
- [PyVRP/Instances — convention VRPTW DIMACS](https://github.com/PyVRP/Instances/blob/7474b068a8effa7f39448b241314b615c9271525/VRPTW/README.md), révision figée dans le manifeste.
- [VRPLIB — lecture des instances et solutions](https://github.com/PyVRP/VRPLIB).
- [SciPy — interface `milp` et statuts de résolution](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html).
- [Numba — compilation des fonctions numériques](https://numba.readthedocs.io/en/stable/user/jit.html).
