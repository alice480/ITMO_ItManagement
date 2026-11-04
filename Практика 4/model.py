"""Reproducible scenario calculations. No synthetic operational observations.
Run: python model.py --out results.json
Money is in rubles. Timeboxes are proposed budget caps, not measured durations.
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path


def calculate() -> dict:
    rates = {'engineer': 3000.0, 'analyst': 2700.0, 'lead': 3200.0}
    phase0 = [
        ('mapping', 7*4, rates['analyst']),
        ('connectors', 3*2*8, rates['engineer']),
        ('historical_exports', 7*2*1, rates['analyst']),
        ('independent_reconciliation', 7*1, rates['engineer']),
        ('decision_sessions', 3*2*1, rates['lead']),
    ]
    n = math.ceil(math.log(0.05) / math.log(0.95))
    case_n = n+2 # two known regressions, never counted as independent trials
    token_cap = (10*2000 + 5*400)/1000 * 1.2
    phase1 = [
        ('dashboard', 3*8, rates['analyst']),
        ('metric_passports', 13*1, rates['analyst']),
        ('model_checks', 2*8, rates['engineer']),
        ('paired_case_review', case_n*2*0.5, rates['engineer']),
        ('finops_pilot_engineering', 4*2, rates['engineer']),
        ('finops_pilot_review_engineer', 4*1, rates['engineer']),
        ('finops_pilot_review_analyst', 4*1, rates['analyst']),
        ('handover', 4*2, rates['analyst']),
        ('model_calls', case_n+4, token_cap),
    ]
    b0 = sum(q*p for _,q,p in phase0)
    b1 = sum(q*p for _,q,p in phase1)
    fixed_month = 8*rates['engineer']+8*rates['analyst']+4*rates['engineer']+4*token_cap
    change_cost = rates['engineer']+rates['analyst']+2*rates['engineer']+token_cap
    changes_month = 4
    changes_month_cost = changes_month*change_cost
    full_cap = b0+b1
    c0 = 150_000_000*100/(40-25) # integer percentage-point difference avoids cancellation
    annual_cloud = c0*140/100
    scenarios=[]
    for name,s,d,k,ops,acts in [
        ('without_changes',0.0,12,0.0,0,0),
        ('expected_conditional',0.05,3,full_cap,12,9),
        ('pessimistic_stop_at_gate0',0.0,12,b0,0,0),
    ]:
        gross = annual_cloud*s*(12-d)/12
        recurring = ops*fixed_month+acts*changes_month_cost
        net = gross-k-recurring
        monthly = annual_cloud*s/12-fixed_month-changes_month_cost
        payback = None if monthly <= 0 or name!='expected_conditional' else d+(k+d*fixed_month)/monthly
        scenarios.append(dict(name=name,s=s,delay_months=d,gross=gross,oneoff=k,recurring=recurring,net=net,
                              net_pct_cloud=100*net/annual_cloud,gross_pct_cloud=100*gross/annual_cloud,
                              uncovered_delta=150_000_000-net,payback_months=payback,
                              cloud_bill=annual_cloud-gross))
    r2024=107_236_015_000
    r2025=117_587_001_000
    pred=r2024 # naive retrospective baseline; not a prediction recorded in 2024
    history=dict(train_year=2024,holdout_year=2025,train_revenue=r2024,forecast_revenue=pred,actual_revenue=r2025,
                 signed_error=pred-r2025,ape_pct=100*abs(pred-r2025)/r2025,
                 hourly_pred_2025=pred/(365*24),hourly_actual_2025=r2025/(365*24))
    break_even_s=(full_cap+12*fixed_month+9*changes_month_cost)/(annual_cloud*9/12)
    return dict(rates=rates,phase0=phase0,phase1=phase1,phase0_total=b0,phase1_total=b1,oneoff_total=full_cap,
                independent_cases=n,regression_cases=2,case_count=case_n,upper_error_bound=1-0.05**(1/n),
                token_cost_cap=token_cap,fixed_month=fixed_month,change_cost=change_cost,changes_month_cost=changes_month_cost,
                scenarios=scenarios,history=history,break_even_s_pct=100*break_even_s,
                annual_base=c0,annual_transition=annual_cloud,annual_alt=c0*125/100,
                target_savings=annual_cloud*0.05,savings_for_surcharge_pct=100*150_000_000/annual_cloud,
                hourly_revenue_reference=117_600_000_000/(365*24),exposure_20h=117_600_000_000/(365*24)*20,
                historical_export_wait={'mean_min':30,'p50_min':30,'p95_min':57,'max_min':60},
                current_agent_errors=2,current_agent_drafts_checked=None,observed_review_minutes=None,
                operational_history_validated=False,
                new_product_revenue=dict(recognized_revenue_rub=None, contribution_margin_rate=None,
                                         attributable_cost_rub=None, net_contribution_rub=None,
                                         status='ledger_and_product_scope_not_provided'))


def verify(r: dict) -> None:
    assert r['independent_cases']==59
    assert r['upper_error_bound']<0.05
    assert math.isclose(r['annual_transition'],1_400_000_000,abs_tol=0.01)
    assert math.isclose(r['target_savings'],70_000_000,abs_tol=0.01)
    assert r['current_agent_drafts_checked'] is None
    assert r['operational_history_validated'] is False
    assert r['new_product_revenue']['recognized_revenue_rub'] is None
    for s in r['scenarios']:
        assert math.isclose(s['gross']-s['oneoff']-s['recurring'],s['net'])
        assert math.isclose(150_000_000-s['net'],s['uncovered_delta'])
    assert r['scenarios'][2]['payback_months'] is None
    assert r['history']['train_year'] < r['history']['holdout_year']


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path)
    args=p.parse_args()
    r=calculate(); verify(r)
    payload=json.dumps(r,ensure_ascii=False,indent=2)
    if args.out: args.out.write_text(payload+'\n',encoding='utf-8')
    print(payload)

if __name__=='__main__': main()
