"""Reprendre la fabrication du livrable sans relancer les benchmarks."""
from pathlib import Path
from contextlib import redirect_stdout
import argparse
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true',help='Exécuter les 16 cellules de code du notebook')
    parser.add_argument('--validate',action='store_true',help='Valider les preuves et le XML de tests existant')
    args=parser.parse_args()
    from scripts.report_final_static import report
    for name in ['pilote25','couverture_progressive','confirmation_ils_v2']:
        folder=ROOT/'results/final_static'/name
        with (folder/'CONSOLE_RAPPORT.txt').open('w',encoding='utf-8') as out,redirect_stdout(out):
            report(folder)
    scripts=['figures_final_static.py','recenter_final_static.py','complete_final_static_report.py']
    if (ROOT/'results/presentation_status/AUDIT.json').exists():
        # Reclasser les comparaisons après génération, avant exécution du notebook.
        scripts.append('present_gap_status.py')
    if args.execute:scripts.append('execute_final_notebook.py')
    if args.validate:
        scripts.append('validate_final_static.py')
        if (ROOT/'results/presentation_status/AUDIT.json').exists():
            scripts.append('validate_gap_presentation.py')
    for name in scripts:
        print('Étape : '+name,flush=True)
        subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts'/name)],cwd=ROOT,check=True)


if __name__=='__main__':main()
