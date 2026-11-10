"""Finish publication only after all actual runs and stages are complete."""
from pathlib import Path
import sys,json,subprocess,time,psutil
ROOT=Path(__file__).resolve().parents[1]


def run(script,*args):
    print('RUN',script,*args,flush=True)
    subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts'/script),*args],cwd=ROOT,check=True)


def main():
    if 8 in psutil.Process().cpu_affinity():psutil.Process().cpu_affinity([8])
    while True:
        try:
            a=json.loads((ROOT/'results/campaign/progress.json').read_text())
            b=json.loads((ROOT/'results/final/progress.json').read_text())
            if a['complete'] and b['complete'] and a['completed']==b['completed']==1000:break
        except (FileNotFoundError,json.JSONDecodeError):pass
        time.sleep(5)
    run('build_report.py')
    run('export_report.py')
    run('export_pdf.py')
    run('export_pdf.py','--stem','ANNEXE_INSTANCES')
    run('validate_delivery.py')
    run('package.py')


if __name__=='__main__':main()
