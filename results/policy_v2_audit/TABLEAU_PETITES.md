# Comparaisons en durée — 72 essais réellement exécutés

Graine 4101, budget souple de cinq secondes. Les références sont des plans réalisables heuristiques, sans preuve d’optimalité temporelle. Les statuts ne sont pas des pourcentages.

| instance   |   n |   seed |   initial_duration |   duration |   reference | comparison                                          |   wall_s |   cpu_s |
|:-----------|----:|-------:|-------------------:|-----------:|------------:|:----------------------------------------------------|---------:|--------:|
| C101       | 100 |   4101 |         10327.0000 |  9827.3000 |   9827.3000 | Référence égalée — optimalité non démontrée         |   5.0013 |  4.9375 |
| C101       |  25 |   4101 |          2846.3000 |  2623.5000 |   2623.5000 | Référence égalée — optimalité non démontrée         |   5.0006 |  4.9219 |
| C101       |  50 |   4101 |          5013.7000 |  4955.1000 |   4955.1000 | Référence égalée — optimalité non démontrée         |   5.0011 |  4.9531 |
| C102       | 100 |   4101 |         10052.0000 |  9827.3000 |   9827.3000 | Référence égalée — optimalité non démontrée         |   5.0013 |  4.9219 |
| C103       | 100 |   4101 |         10387.4000 |  9845.0000 |   9895.8000 | Référence dépassée — solution améliorante validée   |   5.0014 |  4.8750 |
| C104       | 100 |   4101 |         10536.6000 |  9925.6000 |  10013.3000 | Référence dépassée — solution améliorante validée   |   5.0013 |  4.9375 |
| C105       | 100 |   4101 |         10420.4000 |  9827.3000 |   9827.3000 | Référence égalée — optimalité non démontrée         |   5.0014 |  4.9062 |
| C105       |  25 |   4101 |          2576.4000 |  2530.2000 |    nan      | Référence insuffisante — comparaison non concluante |   5.0008 |  4.7969 |
| C105       |  50 |   4101 |          4981.7000 |  4906.8000 |    nan      | Référence insuffisante — comparaison non concluante |   5.0007 |  4.9688 |
| C106       | 100 |   4101 |         10266.4000 |  9827.3000 |   9827.3000 | Référence égalée — optimalité non démontrée         |   5.0014 |  4.9531 |
| C106       |  25 |   4101 |          2889.1000 |  2629.5000 |    nan      | Référence insuffisante — comparaison non concluante |   5.0006 |  4.7188 |
| C106       |  50 |   4101 |          4929.7000 |  4887.9000 |    nan      | Référence insuffisante — comparaison non concluante |   5.0008 |  4.9688 |
| C107       | 100 |   4101 |         10088.4000 |  9827.3000 |   9827.3000 | Référence égalée — optimalité non démontrée         |   5.0015 |  4.8906 |
| C108       | 100 |   4101 |         10267.7000 |  9827.6000 |   9827.3000 | 0.0031 %                                            |   5.0014 |  4.9375 |
| C109       | 100 |   4101 |         10343.3000 |  9860.6000 |   9827.3000 | 0.3389 %                                            |   5.0013 |  4.9375 |
| C201       | 100 |   4101 |          9589.1000 |  9589.1000 |   9589.1000 | Référence égalée — optimalité non démontrée         |   5.0013 |  4.9219 |
| C201       |  25 |   4101 |          4461.3000 |  3194.7000 |    nan      | Référence insuffisante — comparaison non concluante |   5.0005 |  4.8594 |
| C201       |  50 |   4101 |          7497.6000 |  6041.3000 |    nan      | Référence insuffisante — comparaison non concluante |   5.0007 |  4.8906 |
| C202       | 100 |   4101 |          9622.6000 |  9589.1000 |   9589.1000 | Référence égalée — optimalité non démontrée         |   5.0014 |  4.9219 |
| C203       | 100 |   4101 |          9684.1000 |  9624.2000 |   9599.9000 | 0.2531 %                                            |   5.0013 |  4.9219 |
| C204       | 100 |   4101 |         10655.2000 |  9738.3000 |   9588.1000 | 1.5665 %                                            |   5.0013 |  4.9688 |
| C205       | 100 |   4101 |          9691.5000 |  9586.4000 |   9586.4000 | Référence égalée — optimalité non démontrée         |   5.0013 |  4.9375 |
| C206       | 100 |   4101 |          9770.0000 |  9596.9000 |   9586.0000 | 0.1137 %                                            |   5.0013 |  4.8906 |
| C207       | 100 |   4101 |          9791.3000 |  9585.8000 |   9658.4000 | Référence dépassée — solution améliorante validée   |   5.0013 |  4.8750 |
| C208       | 100 |   4101 |          9641.2000 |  9602.0000 |   9742.2000 | Référence dépassée — solution améliorante validée   |   5.0013 |  4.9219 |
| R101       | 100 |   4101 |          3509.8000 |  3399.2000 |   3715.8000 | Référence dépassée — solution améliorante validée   |   5.0014 |  4.9375 |
| R101       |  25 |   4101 |          1331.4000 |  1294.7000 |   1294.7000 | Référence égalée — optimalité non démontrée         |   5.0007 |  4.9062 |
| R101       |  50 |   4101 |          2122.3000 |  2007.1000 |    nan      | Référence insuffisante — comparaison non concluante |   5.0010 |  4.9531 |
| R102       | 100 |   4101 |          3414.5000 |  3089.8000 |   3406.6000 | Référence dépassée — solution améliorante validée   |   5.0014 |  4.9219 |
| R103       | 100 |   4101 |          2745.4000 |  2487.3000 |   2817.0000 | Référence dépassée — solution améliorante validée   |   5.0014 |  4.9375 |
| R104       | 100 |   4101 |          2264.3000 |  2063.7000 |   2298.6000 | Référence dépassée — solution améliorante validée   |   5.0013 |  4.8906 |
| R105       | 100 |   4101 |          2838.1000 |  2662.5000 |   2770.6000 | Référence dépassée — solution améliorante validée   |   5.0014 |  4.9219 |
| R106       | 100 |   4101 |          2547.3000 |  2408.7000 |   2531.7000 | Référence dépassée — solution améliorante validée   |   5.0017 |  4.9531 |
| R107       | 100 |   4101 |          2429.3000 |  2160.3000 |   2271.3000 | Référence dépassée — solution améliorante validée   |   5.0014 |  4.9531 |
| R108       | 100 |   4101 |          2248.8000 |  2026.7000 |   2088.2000 | Référence dépassée — solution améliorante validée   |   5.0013 |  4.8750 |
| R109       | 100 |   4101 |          2573.5000 |  2419.3000 |   2417.7000 | 0.0662 %                                            |   5.0014 |  4.9062 |
| R110       | 100 |   4101 |          2392.2000 |  2206.6000 |   2360.9000 | Référence dépassée — solution améliorante validée   |   5.0014 |  4.9375 |
| R111       | 100 |   4101 |          2533.0000 |  2226.3000 |   2420.9000 | Référence dépassée — solution améliorante validée   |   5.0014 |  4.9688 |
| R112       | 100 |   4101 |          2312.1000 |  2026.1000 |   2113.7000 | Référence dépassée — solution améliorante validée   |   5.0015 |  4.9219 |
| R201       | 100 |   4101 |          3985.2000 |  2902.2000 |   6296.6000 | Référence dépassée — solution améliorante validée   |   5.0013 |  4.9219 |
| R201       |  25 |   4101 |          2403.7000 |  1345.9000 |    nan      | Référence insuffisante — comparaison non concluante |   5.0007 |  4.9531 |
| R201       |  50 |   4101 |          3064.8000 |  1684.9000 |    nan      | Référence insuffisante — comparaison non concluante |   5.0008 |  4.9375 |
| R202       | 100 |   4101 |          3449.5000 |  2684.4000 |   6267.1000 | Référence dépassée — solution améliorante validée   |   5.0012 |  4.8906 |
| R203       | 100 |   4101 |          3236.3000 |  2260.8000 |   5131.5000 | Référence dépassée — solution améliorante validée   |   5.0012 |  4.9375 |
| R204       | 100 |   4101 |          2928.1000 |  1916.9000 |   3684.6000 | Référence dépassée — solution améliorante validée   |   5.0013 |  4.8906 |
| R205       | 100 |   4101 |          2659.2000 |  2291.3000 |   3784.4000 | Référence dépassée — solution améliorante validée   |   5.0013 |  4.9688 |
| R206       | 100 |   4101 |          2689.8000 |  2370.8000 |   3733.2000 | Référence dépassée — solution améliorante validée   |   5.0013 |  4.9219 |
| R207       | 100 |   4101 |          2486.3000 |  2093.3000 |   2960.0000 | Référence dépassée — solution améliorante validée   |   5.0013 |  4.9688 |
| R208       | 100 |   4101 |          2447.4000 |  1945.2000 |   2905.7000 | Référence dépassée — solution améliorante validée   |   5.0013 |  4.8281 |
| R209       | 100 |   4101 |          2994.5000 |  2199.4000 |   3480.7000 | Référence dépassée — solution améliorante validée   |   5.0014 |  4.8906 |
| R210       | 100 |   4101 |          3085.5000 |  2274.7000 |   4682.2000 | Référence dépassée — solution améliorante validée   |   5.0013 |  4.9688 |
| R211       | 100 |   4101 |          2344.3000 |  2058.7000 |   2737.2000 | Référence dépassée — solution améliorante validée   |   5.0012 |  4.9531 |
| RC101      | 100 |   4101 |          3335.2000 |  2921.1000 |   2991.6000 | Référence dépassée — solution améliorante validée   |   5.0015 |  4.9844 |
| RC101      |  25 |   4101 |           876.8000 |   796.9000 |    nan      | Référence insuffisante — comparaison non concluante |   5.0006 |  4.8750 |
| RC101      |  50 |   4101 |          1603.4000 |  1581.3000 |    nan      | Référence insuffisante — comparaison non concluante |   5.0008 |  4.9219 |
| RC102      | 100 |   4101 |          2888.5000 |  2687.5000 |   2892.0000 | Référence dépassée — solution améliorante validée   |   5.0015 |  4.9375 |
| RC103      | 100 |   4101 |          2648.8000 |  2395.5000 |   2471.0000 | Référence dépassée — solution améliorante validée   |   5.0021 |  4.9688 |
| RC104      | 100 |   4101 |          2478.0000 |  2215.2000 |   2268.7000 | Référence dépassée — solution améliorante validée   |   5.0014 |  4.9688 |
| RC105      | 100 |   4101 |          2987.5000 |  2835.0000 |   3051.8000 | Référence dépassée — solution améliorante validée   |   5.0015 |  4.9688 |
| RC106      | 100 |   4101 |          2849.6000 |  2603.7000 |   2591.2000 | 0.4824 %                                            |   5.0015 |  4.9219 |
| RC107      | 100 |   4101 |          2562.5000 |  2349.2000 |   2430.2000 | Référence dépassée — solution améliorante validée   |   5.0014 |  4.9688 |
| RC108      | 100 |   4101 |          2489.3000 |  2249.5000 |   2275.5000 | Référence dépassée — solution améliorante validée   |   5.0015 |  4.8906 |
| RC201      | 100 |   4101 |          3945.1000 |  3061.1000 |   6505.3000 | Référence dépassée — solution améliorante validée   |   5.0013 |  4.9219 |
| RC201      |  25 |   4101 |          2209.2000 |  1295.3000 |   1295.3000 | Référence égalée — optimalité non démontrée         |   5.0006 |  4.8438 |
| RC201      |  50 |   4101 |          2952.9000 |  2004.8000 |    nan      | Référence insuffisante — comparaison non concluante |   5.0008 |  4.8594 |
| RC202      | 100 |   4101 |          4002.2000 |  2803.3000 |   5693.6000 | Référence dépassée — solution améliorante validée   |   5.0013 |  4.9062 |
| RC203      | 100 |   4101 |          3797.9000 |  2479.6000 |   4041.2000 | Référence dépassée — solution améliorante validée   |   5.0013 |  4.9531 |
| RC204      | 100 |   4101 |          2565.7000 |  2159.5000 |   2757.6000 | Référence dépassée — solution améliorante validée   |   5.0013 |  4.8906 |
| RC205      | 100 |   4101 |          4324.2000 |  3063.4000 |   5689.9000 | Référence dépassée — solution améliorante validée   |   5.0013 |  4.9062 |
| RC206      | 100 |   4101 |          3059.7000 |  2515.3000 |   4721.5000 | Référence dépassée — solution améliorante validée   |   5.0014 |  4.8750 |
| RC207      | 100 |   4101 |          3035.3000 |  2482.9000 |   3972.7000 | Référence dépassée — solution améliorante validée   |   5.0013 |  4.8281 |
| RC208      | 100 |   4101 |          2352.1000 |  2105.4000 |   2721.6000 | Référence dépassée — solution améliorante validée   |   5.0021 |  4.8281 |
