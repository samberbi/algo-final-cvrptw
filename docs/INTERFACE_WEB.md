# Interface web du laboratoire CVRPTW

L'interface utilise notre moteur Python, sans changer le code des campagnes
publiées. Elle fonctionne localement dans le navigateur ; GitHub héberge le code,
pas le serveur de calcul.

## Installer et lancer

Depuis le dossier cloné, avec Python 3.12 :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-web.txt
.\.venv\Scripts\python.exe -m streamlit run web/app.py
```

Ouvrir **http://127.0.0.1:8501**. Le raccourci `lancer_web.bat` démarre
également l'application avec l'environnement du projet ou celui du dossier parent.

## Créer une expérience

1. Ouvrir **Nouvelle expérience**.
2. Filtrer les tailles et familles, puis choisir une ou plusieurs instances,
   ou toutes les instances du filtre.
3. Choisir le budget ALNS par run, le nombre de répétitions et la première graine.
   Les graines automatiques sont consécutives. Une liste manuelle remplace ce choix.
4. Choisir une ou plusieurs configurations : ALNS complet, sans adaptation,
   sans recherche locale ou sans recuit.
5. Facultativement ajouter un budget de décomposition par run. Cette phase
   utilise son propre ALNS complet ; les ablations désactivent les mécanismes
   uniquement dans la première phase.
6. Cliquer sur **Lancer la campagne**, puis aller dans **Mes campagnes**.

Exemple : deux instances, vingt graines et deux configurations produisent
80 résolutions. Les configurations partagent les mêmes instances, graines et
budgets. Les runs sont séquentiels ; une campagne active bloque un nouveau
lancement depuis l'interface pour limiter la concurrence entre calculs.

Le budget nominal ne comprend pas le chargement, le préchauffage Numba ni
l'affichage. Une opération atomique peut dépasser légèrement le budget.
Le préchauffage initial peut être long sur un nouvel ordinateur.

## Suivre et comprendre

L'avancement s'actualise toutes les trois secondes. Les résultats et graphiques
sont disponibles après chaque run terminé ; la courbe d'un run en cours n'est
pas diffusée en direct. Fermer le navigateur ou le serveur Streamlit ne termine
pas le processus de campagne. Éteindre l'ordinateur l'interrompt ; les runs
déjà terminés restent disponibles. La reprise d'un run interrompu n'est pas
automatique : créer une nouvelle campagne pour les essais manquants.

Le bouton d'arrêt laisse finir le run en cours, puis arrête la campagne.
Les erreurs sont conservées avec leur cause et ne reçoivent pas de gap fictif.

Pour chaque run réalisable, un vérificateur indépendant contrôle les clients,
la capacité, les fenêtres, le retour au dépôt et la flotte maximale. La BKS
n'est utilisée qu'après la résolution pour calculer le gap de distance DIMACS.

Les écrans affichent les gaps moyens, médians, extrêmes et écarts-types,
les nombres de solutions réalisables et sous les seuils, les boîtes à
moustaches et les temps de calcul. Un run peut être exploré avec sa carte,
sa convergence et son Gantt. Les unités temporelles et de distance internes
sont divisées par dix pour l'affichage. Les axes cartographiques sont des
coordonnées de benchmark, pas une carte routière.

La moyenne des gaps concerne les runs réalisables avec référence, et le
dénominateur est toujours indiqué. Un seul run ne définit pas d'écart-type.
La moyenne pondérée par run peut différer d'une moyenne donnant le même poids
à chaque instance quand leurs nombres de répétitions diffèrent.

## Conserver et exporter

- Les nouvelles campagnes sont dans `results/local/web/<identifiant>/`.
- `protocol.json` contient les paramètres, graines et empreintes des sources.
- `runs/*.json` conserve les solutions, contrôles, traces et erreurs.
- `progress.json` contient l'état et `worker.log` le journal du processus.
- Les boutons permettent d'exporter les runs et statistiques en CSV et un run
  complet en JSON. Les graphiques Plotly offrent leur téléchargement en image.

Les campagnes historiques de 1 000 et 80 runs restent séparées, disponibles
dans **Résultats historiques**. Les filtres indiquent le périmètre affiché.
Les nouveaux calculs locaux sont ignorés par Git : pour les transférer sur un
autre ordinateur, copier leur dossier ou conserver les exports. Un `git push`
du code ne transfère pas automatiquement ces expériences locales.

## Vérifier l'application

```powershell
.\.venv\Scripts\python.exe -m pytest tests
```

Les tests web nécessitent `requirements-web.txt` ; ils couvrent des résolutions
réelles via le processus détaché, la validation des paramètres, l'arrêt,
l'enregistrement d'erreurs et la navigation Streamlit.

L'application écoute uniquement sur la boucle locale et n'a pas de système
de comptes. Une publication multi-utilisateur nécessiterait une authentification,
une file de travaux et des limites de ressources adaptées.
