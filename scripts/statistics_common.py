"""Contrôles de pondération et de couverture sur des indicateurs relatifs."""
def summary(frame):
    """Do not turn failures into zero gaps or give repeated cases extra weight."""
    good=frame[frame.valid].copy()
    per=good.groupby('instance').gap_pct.mean()
    return dict(instances=int(frame.instance.nunique()),attempts=len(frame),valid=len(good),
        failures=int((~frame.valid).sum()),represented_instances=len(per),
        feasible_rate=float(frame.valid.mean()),mean_instance_gap=float(per.mean()) if len(per) else None,
        mean_run_gap=float(good.gap_pct.mean()) if len(good) else None,
        std_instance_gap=float(per.std(ddof=1)) if len(per)>1 else None,
        best_run_gap=float(good.gap_pct.min()) if len(good) else None,
        worst_run_gap=float(good.gap_pct.max()) if len(good) else None,
        runs_below_5=int((good.gap_pct<5).sum()),runs_below_6=int((good.gap_pct<6).sum()),
        instances_mean_below_6=int((per<6).sum()),
        mean_total_s=float(good.total_s.mean()) if len(good) else None)
