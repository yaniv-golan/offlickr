"""Fixtures: run ingest + derive + render on the mini-export."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from offlickr.derive.pipeline import run_derive
from offlickr.ingest.pipeline import run_ingest
from offlickr.model import OfflickrArchive
from offlickr.render.pages import render_site
from tests.conftest import MINI_EXPORT


@pytest.fixture(scope="session")
def built_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("site")
    run_ingest(
        source=MINI_EXPORT,
        output_dir=out,
        include_private=False,
        include_private_photos=False,
    )
    run_derive(output_dir=out, jobs=1)
    archive = OfflickrArchive.model_validate(json.loads((out / "data" / "model.json").read_text()))
    render_site(archive=archive, output_dir=out)
    return out
