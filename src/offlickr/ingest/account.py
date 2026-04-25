"""Parser for account_profile.json. See spec §5.1."""

from __future__ import annotations

import json
from pathlib import Path

from offlickr.model import Account
from offlickr.render.sanitize import sanitize_html


def load_account(source_dir: Path) -> Account:
    data = json.loads((source_dir / "account_profile.json").read_text(encoding="utf-8"))
    account = Account.from_json(data)
    return account.model_copy(update={"description_html": sanitize_html(account.description_html)})
