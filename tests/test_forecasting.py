from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from gridmind.forecasting import features, load_sample, partition, validate, predict_next

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def sample():
    return load_sample(ROOT/'data/raw/ercot_2021_2024_hourly.csv')


@pytest.mark.parametrize('kind', ['demand', 'solar', 'wind'])
def test_target_and_future_measurements_do_not_enter_features(sample, kind):
    history = sample.iloc[:200].copy()
    original = features(history, kind).iloc[100].to_numpy()
    history.iloc[100:, :] = history.iloc[100:, :] * 3 + 7
    np.testing.assert_array_equal(features(history, kind).iloc[100].to_numpy(), original)


def test_split_order_and_sample(sample):
    assert len(sample) == 17544
    split = partition(sample.index[168:])
    assert split.value_counts().to_dict() == {'train': 13900, 'test': 1738, 'validation': 1738}
    assert split[split == 'train'].index.max() < split[split == 'validation'].index.min()
    assert split[split == 'validation'].index.max() < split[split == 'test'].index.min()


def test_gap_and_bad_proxy_rejected(sample):
    with pytest.raises(ValueError, match='gaps'):
        validate(sample.iloc[:200].drop(sample.index[50]))
    bad = sample.iloc[:200].copy()
    bad.iloc[0, bad.columns.get_loc('clear_sky_proxy')] = .8
    with pytest.raises(ValueError, match='Proxy'):
        validate(bad)


def test_insufficient_history_rejected(sample):
    with pytest.raises(ValueError, match='72'):
        predict_next(sample.iloc[:30], ROOT/'artifacts/nonexistent')


def test_solar_residual_anchor(sample):
    from gridmind.forecasting import postprocess
    zero_residual = np.zeros(len(sample))
    expected = (sample.solar_generation/sample.solar_installed).shift(24).clip(0,1.05)*sample.solar_installed.shift(1)
    np.testing.assert_allclose(postprocess(zero_residual, sample, 'solar')[24:], expected.iloc[24:])
