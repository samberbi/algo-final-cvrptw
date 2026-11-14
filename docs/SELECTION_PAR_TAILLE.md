### 6.14. Nouvelle configuration : sélection explicite selon la taille

Les nouvelles commandes de test utilisent le profil `size_based` par défaut :

| Taille | Moteur choisi |
|---|---|
| Au plus 100 clients | Construction regret-2 seule, douze tentatives |
| Plus de 100 clients | Profil renforcé existant : constructions propres, recherche locale PyVRP et partitionnement HiGHS |

Le seuil de 100 est une règle déclarée avant les mesures, alignée sur la
séparation des petites tailles Solomon et des grandes tailles testées. Ce
sélecteur n'est pas une nouvelle métaheuristique : il choisit un moteur existant.
Il ne consulte ni référence, ni coût cible, ni gap. Aucune solution n'est rejetée
ou détériorée pour forcer son écart dans un intervalle.

Pour les petits cas, cette configuration privilégie une construction rapide.
Elle peut être moins bonne que notre ILS ou le renforcé : cette perte de qualité
est mesurée, pas masquée. La variante ne garantit pas le seuil académique. Les
ILS et recuit autonomes restent disponibles, ainsi que les anciens hybrides.
Le code des deux moteurs sélectionnés reste inchangé ; ils minimisent toujours
la durée complète avec les mêmes contraintes. L'API et les campagnes historiques
conservent leurs configurations pour la reproductibilité. Les résultats déjà
enregistrés ne sont pas réétiquetés comme résultats de cette nouvelle sélection.

**Vérification réellement exécutée.** Six instances, une graine (4101), budget
demandé cinq secondes. Les choix, les tournées et les coûts ont été revérifiés
indépendamment. Sur les petits cas, la construction s'arrête après douze
tentatives ; sur les grands cas, le renforcé utilise un budget total souple.
Les limites de temps et dépassements éventuels sont ceux mesurés, pas des valeurs
artificiellement plafonnées. Le garde-fou par processus reste 120 secondes.

| Instance   |   Clients | Moteur       |       Duree | Comparaison                                       |   CPU_s |   Reel_s |
|:-----------|----------:|:-------------|------------:|:--------------------------------------------------|--------:|---------:|
| C101       |        25 | construction |   2846.3000 | 8.4925 %                                          |  0.0000 |   0.0045 |
| C101       |        50 | construction |   5013.7000 | 1.1826 %                                          |  0.0156 |   0.0100 |
| C101       |       100 | construction |  10327.0000 | 5.0848 %                                          |  0.0312 |   0.0309 |
| C1_2_1     |       200 | refined      |  20760.7000 | Référence dépassée — solution améliorante validée |  0.8125 |   1.0026 |
| C1_10_6    |      1000 | refined      | 140502.9000 | 5.0452 %                                          |  4.7031 |   5.0072 |
| R2_10_8    |      1000 | refined      |  86097.4000 | Référence dépassée — solution améliorante validée |  4.7344 |   5.0475 |

Les références sont OR-Tools enregistré pour C101/25 et C101/50, puis les plans
publics optimisés en distance et réévalués en durée. Ce ne sont pas des optima
temporels démontrés ; les statuts de comparaison gardent donc cette qualification.
Le dépassement de six pour cent observé sur C101/25 est conservé. Ce petit pilote
ne démontre pas la performance du sélecteur sur tous les scénarios.

```powershell
python scripts/test_instances.py --instances C101:25 C101:50 C101:100 C1_2_1:200 C1_10_6:1000 R2_10_8:1000 --seconds 5 --label selection_par_taille_validation
python scripts/test_instances.py --instances C101 --method refined --seconds 5
```

La première commande explicite la sélection (également active sans `--method`).
La seconde force le profil renforcé, y compris sur une petite instance. Les
sorties affichent `size_based` et **Moteur exécuté**, conservés aussi dans les
CSV/JSON. Les résultats et sources de ce pilote sont dans
`results/size_policy/selection_par_taille_validation/`.

**Tests après ajout du sélecteur : 222 réussites**, deux modules optionnels ignorés. Les bornes 100/101 et le transfert des paramètres aux moteurs sont contrôlés.
