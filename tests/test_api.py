import json
from pathlib import Path
import tempfile

from fastapi.testclient import TestClient
import pytest

from gridmind.api import MAX_BYTES, create_app, infer_bytes, load_model
from gridmind import stage1
from test_diagnosis_context import trace

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client():
    with TestClient(create_app(dist=ROOT / 'missing-dist')) as c:
        yield c


def test_api_matches_direct_inference_and_cleans_temporary_files(client):
    before = set(Path(tempfile.gettempdir()).glob('gridmind-upload-*'))
    # Explicit synthetic software fixture, never a measured effectiveness example.
    payload = trace(jump=True).to_csv(index=False).encode()
    bundle = load_model(ROOT / 'models/stage1')
    response = client.post('/api/diagnosis',files={'file':('fixture.csv',payload,'text/csv')},data={'angle_unit':'radian'})
    assert response.status_code == 200, response.text
    result = response.json()
    assert len(result['trace']) == 1800 and result['prediction']['ground_truth'] is None
    expected = infer_bytes(bundle,payload,'radian')['prediction']
    assert result['prediction']['category'] == expected['category']
    assert result['prediction']['detection'] == expected['detection']
    assert before == set(Path(tempfile.gettempdir()).glob('gridmind-upload-*'))


@pytest.mark.parametrize('change',['missing','gap','reconstructed','unit','duplicate_header','nan','short','oversize'])
def test_api_invalid_uploads(client,change):
    frame = trace()
    unit = 'radian'
    if change=='missing': frame=frame.drop(columns='frequency')
    elif change=='gap': frame.loc[500:,'elapsed_seconds']+=1
    elif change=='reconstructed': frame.loc[30,'reconstructed']=1
    elif change=='unit': unit='unknown'
    elif change=='nan': frame.loc[3,'frequency']=float('nan')
    elif change=='short': frame=frame.iloc[:89]
    payload=frame.to_csv(index=False).encode()
    if change=='duplicate_header': payload=payload.replace(b'current_angle',b'angle',1)
    if change=='oversize': payload=b'x'*(MAX_BYTES+1)
    response=client.post('/api/diagnosis',files={'file':('test.csv',payload,'text/csv')},data={'angle_unit':unit})
    assert response.status_code == (413 if change=='oversize' else 422),response.text


def test_missing_model_is_unavailable_and_api_paths_do_not_fall_back_to_html(tmp_path):
    with TestClient(create_app(model_directory=tmp_path,dist=tmp_path/'none')) as client:
        assert client.get('/api/health').status_code==503
        response=client.post('/api/diagnosis',files={'file':('test.csv',b'x','text/csv')})
        assert response.status_code==503
        assert client.get('/api/not-a-route').status_code==404


def test_packaged_checksum_detects_corruption(tmp_path):
    source=ROOT/'models/stage1/deployment_manifest.json'
    (tmp_path/'deployment_manifest.json').write_bytes(source.read_bytes())
    (tmp_path/'model.joblib').write_bytes(b'not a trusted model')
    with pytest.raises(ValueError,match='checksum'):
        load_model(tmp_path)
