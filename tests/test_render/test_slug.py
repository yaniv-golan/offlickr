from offlickr.render.slug import slugify_tags


def test_ascii_tag() -> None:
    result = slugify_tags(["sunset"])
    assert result == {"sunset": "sunset"}


def test_unicode_tag_preserved() -> None:
    result = slugify_tags(["שקיעה"])
    assert result == {"שקיעה": "שקיעה"}


def test_spaces_become_hyphens() -> None:
    result = slugify_tags(["blue sky"])
    assert result == {"blue sky": "blue-sky"}


def test_collision_gets_numeric_suffix() -> None:
    result = slugify_tags(["Blue Sky", "blue sky"])
    slugs = list(result.values())
    assert len(set(slugs)) == 2
    assert "blue-sky" in slugs
    assert "blue-sky-2" in slugs


def test_empty_list() -> None:
    assert slugify_tags([]) == {}
