from offlickr.render.pagination import paginate


def test_paginate_empty_returns_one_empty_page() -> None:
    pages: list[list[int]] = paginate([], 60)
    assert pages == [[]]


def test_paginate_exact_one_page() -> None:
    items = list(range(60))
    pages = paginate(items, 60)
    assert len(pages) == 1
    assert pages[0] == items


def test_paginate_splits_correctly() -> None:
    items = list(range(130))
    pages = paginate(items, 60)
    assert len(pages) == 3
    assert len(pages[0]) == 60
    assert len(pages[1]) == 60
    assert len(pages[2]) == 10


def test_paginate_preserves_order() -> None:
    items = ["a", "b", "c", "d", "e"]
    pages = paginate(items, 2)
    flat = [x for page in pages for x in page]
    assert flat == items
