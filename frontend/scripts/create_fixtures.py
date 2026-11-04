"""Author deterministic illustrative values. No electrical or learned validation."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'public/data/scenarios'
OUT.mkdir(parents=True, exist_ok=True)
points = [(85, 135), (205, 85), (345, 85), (485, 135), (610, 85), (735, 135), (805, 250), (660, 300), (510, 255), (370, 300), (240, 250), (95, 300), (245, 415), (520, 415)]
buses = [dict(id=f'illustrative14:bus:{i+1:02}', label=f'{i+1:02}', x=x, y=y, type='bus', in_service=True) for i, (x,y) in enumerate(points)]
pairs = [(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,8),(8,9),(9,10),(10,11),(11,12),(12,1),(11,13),(13,14),(14,9),(2,11),(3,10),(4,9),(6,9),(10,13)]
lines = [dict(id=f'illustrative14:line:{i+1:02}', label=f'L{i+1:02}', source=f'illustrative14:bus:{a:02}', target=f'illustrative14:bus:{b:02}', type='line', in_service=True) for i,(a,b) in enumerate(pairs)]
network = dict(id='illustrative14-v1', version='1', provenance_kind='simulated', origin='authored_illustration', review_status='Awaiting model-owner review', buses=buses, lines=lines, resources=[dict(id='illustrative14:generator:01', bus_id=buses[0]['id'], type='generator'),dict(id='illustrative14:generator:02', bus_id=buses[5]['id'], type='generator'),dict(id='illustrative14:load:01', bus_id=buses[12]['id'], type='load')])
(OUT/'network.json').write_text(json.dumps(network, indent=2), encoding='utf-8')
traces = [dict(step=i, reference=round(1.01 + ((i%8)-4)*0.002, 3)) for i in range(24)]
combinations = []
for contingency in [lines[3]['id'], lines[8]['id']]:
    for stress in ['moderate', 'elevated']:
        affected = [lines[contingency == lines[3]['id'] and 8 or 3]['id'], lines[16]['id'], lines[18]['id']]
        rounds = [dict(round=0, affected=[], severity='Initiating outage only', dns_fraction=0),dict(round=1, affected=affected[:1], severity='Moderate illustration', dns_fraction=0.03),dict(round=2, affected=affected[:2] if stress=='moderate' else affected, severity='Elevated illustration', dns_fraction=0.08 if stress=='moderate' else 0.15)]
        combinations.append(dict(contingency_id=contingency, stress=stress, rounds=rounds, baseline_loading_pct=108 if stress=='moderate' else 122, baseline_voltage_pu=0.94 if stress=='moderate' else 0.91))
lab = dict(id='illustrative14-v1', version='1', provenance_kind='simulated', review_status='Awaiting model-owner review', assumptions=['Authored illustration; no power flow or physical validation.', 'The chosen outage is hypothetical, not inferred from diagnosis.', 'Source forecasts are not allocated to this network.'], defaults=dict(contingency_id=lines[3]['id'], stress='moderate', mask='short-gap'), traces=traces, missingness_presets=[dict(id='short-gap', title='Short gap · 4 samples', steps=[7,8,9,10]),dict(id='long-gap', title='Long gap · 8 samples', steps=list(range(6,14)))], combinations=combinations, actions=[
dict(id='no-change', title='No change', changes=[], loading_delta_pct=0, voltage_delta_pu=0, outcome='Unsuccessful illustration: stress remains'),
dict(id='redispatch', title='Generator redispatch', changes=[dict(component_id='illustrative14:generator:01', delta_mw=-5),dict(component_id='illustrative14:generator:02', delta_mw=5)], loading_delta_pct=-14, voltage_delta_pu=0.025, outcome='Scripted improvement; not physically validated'),
dict(id='curtailment', title='Renewable curtailment', changes=[dict(component_id='illustrative14:generator:02', delta_mw=-3)], loading_delta_pct=-6, voltage_delta_pu=0.01, outcome='Scripted partial improvement; replacement supply unspecified')])
(OUT/'laboratory.json').write_text(json.dumps(lab, indent=2), encoding='utf-8')
print('Authored versioned 14-bus fixtures; review pending, no physics validation.')
