"""Shared paths, seeds and small helpers for the v2 pipeline.

Every stage script imports this first. Thread counts are pinned *before* numpy/sklearn import
so that results are bit-reproducible on the same machine + environment.
"""
import os

for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ.setdefault(_v, os.environ.get('SUPERR_THREADS', '4'))

import random
import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RR = os.path.join(ROOT, '02_data')                 # confidential RR data pack (read only)
PUB = os.path.join(ROOT, 'data_public')            # Cricsheet downloads
WORK = os.path.join(ROOT, 'v2_work')               # intermediate artefacts (git-ignored)
RES = os.path.join(ROOT, 'v2_results')             # deliverables
for _d in (WORK, RES):
    os.makedirs(_d, exist_ok=True)

SEED = 20261115


def seed_all(seed: int = SEED):
    random.seed(seed)
    np.random.seed(seed)
    return np.random.default_rng(seed)


def rr(name: str, **kw) -> pd.DataFrame:
    """Read a file from the RR data pack."""
    return pd.read_csv(os.path.join(RR, name), low_memory=False, **kw)


def w(path: str) -> str:
    """Path inside v2_work."""
    p = os.path.join(WORK, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def res(path: str) -> str:
    """Path inside v2_results."""
    p = os.path.join(RES, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


IPL_TEAMS = {'Chennai Super Kings', 'Mumbai Indians', 'Rajasthan Royals', 'Punjab Kings',
             'Royal Challengers Bengaluru', 'Delhi Capitals', 'Kolkata Knight Riders',
             'Sunrisers Hyderabad', 'Gujarat Titans', 'Lucknow Super Giants'}


def phase_of(over):
    """over is 1-based (RR `overid`)."""
    return np.select([over <= 6, over <= 15], ['PP', 'Middle'], 'Death')
