# Synthèse de soutenance — version statique

Nous organisons des livraisons CVRPTW : chaque client est servi une fois,
la capacité et les fenêtres strictes sont respectées, et chaque véhicule revient
avant la fermeture du dépôt. Les trajets sont fixes et symétriques. Le graphe
des décisions reste orienté, avec deux copies du même dépôt. Tous les départs
sont fixés à zéro. L'objectif est la somme des retours, donc trajets, attentes
et services ; le temps CPU est un indicateur de calcul distinct.

Notre contribution comprend les constructions, l'ILS et ses mouvements, le
recuit, l'archive, l'orchestration et le modèle de partitionnement. PyVRP fournit
la recherche locale native et le HGS des profils hybrides ; HiGHS résout le
partitionnement ; OR-Tools fournit un comparateur indépendant. Ces moteurs
sont attribués à leurs auteurs. Un résultat hybride n'est pas un résultat ILS
autonome. L'optimum sur un réservoir de tournées ne vaut pas optimum global.

Les 646 essais historiques sur 356 instances restent conservés. La nouvelle
validation progressive compte 119 résolutions sur les tailles 25 à 1000 :
117 solutions réalisables, deux recherches PyVRP seul sans solution à trois
secondes. Cinq recherches supplémentaires vérifient les références publiées.
Les vingt graines historiques sur trois cas et les deux graines du nouveau
lot de confirmation répondent à des protocoles distincts.

Une amélioration testée consiste à utiliser en ILS le temps inutilisé du profil
renforcé. Réserver la moitié du budget provoquait des régressions à grande
taille ; la correction conserve d'abord tout le planning initial. Sur
R202/4101, elle passe de 2913,1 à 2779,9 unités de durée, soit +6,63 % à +1,76 %
au comparateur OR-Tools de ce lot. Elle n'améliore pas les quatre cas à grande
taille de la confirmation : le coût reste identique, avec davantage de CPU.
La variante reste donc expérimentale.

Nos références OR-Tools sont des solutions réalisables indépendantes, pas des
optima certifiés. Les valeurs Phonin ne sont pas utilisées comme optima
directement compatibles tant que leurs conventions ne sont pas totalement
établies. Un écart nul ou négatif reste possible ; il est conservé. Nous ne
garantissons pas un gap à l'optimum temporel inférieur à 6 % sur tout le jeu.
Les dix petits cas exacts sont recertifiés par une énumération indépendante.
La tentative MILP C101/25 à dix secondes reste au statut limite de temps.

Le notebook a été réexécuté : seize cellules de code, aucune erreur. La suite
actuelle compte 222 tests réussis et deux modules TD optionnels ignorés dans
l'environnement statique. Le reçu est `livraison/VALIDATION_FINALE_STATIQUE.json`.
Les CSV conservent coûts, décomposition, faisabilité, temps, graines, sources et
références. Les figures PNG/SVG sont dans `livraison/figures_final_static/`.

La commande de démonstration et celle de reprise sont dans le README et dans
`PROGRESSION.md`. La première installation/précompilation est séparée du temps
des recherches. Les plans et graphiques déjà enregistrés servent de secours
pendant la présentation ; ils ne sont pas présentés comme une nouvelle exécution.


Configuration actuelle des commandes de test : size_based choisit la construction seule jusqu’à 100 clients, puis le renforcé au-delà. Les campagnes historiques gardent leurs méthodes d’origine. Six essais du sélecteur sont réalisables ; C101/25 conserve un écart de +8,4925 % au comparateur. Le seuil académique reste un objectif non garanti. Les détails sont dans SELECTION_PAR_TAILLE.md.
