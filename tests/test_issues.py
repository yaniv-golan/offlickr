from offlickr.issues import Issue, IssueCollector


def test_empty_collector_has_no_issues() -> None:
    c = IssueCollector()
    assert not c.has_issues()


def test_add_accumulates_issues() -> None:
    c = IssueCollector()
    c.add("cat.a", "id1", "reason1")
    c.add("cat.a", "id2", "reason2")
    c.add("cat.b", "id3", "reason3")
    assert c.has_issues()
    assert len(c._issues) == 3


def test_by_category_groups_by_key() -> None:
    c = IssueCollector()
    c.add("cat.a", "id1", "r1")
    c.add("cat.b", "id2", "r2")
    c.add("cat.a", "id3", "r3")
    grouped = c.by_category()
    assert set(grouped.keys()) == {"cat.a", "cat.b"}
    assert len(grouped["cat.a"]) == 2
    assert len(grouped["cat.b"]) == 1
    assert grouped["cat.a"][0].item_id == "id1"
    assert grouped["cat.a"][1].item_id == "id3"


def test_issue_fields_are_preserved() -> None:
    c = IssueCollector()
    c.add("fetch.avatar", "nsid123", "user not found")
    issue = c._issues[0]
    assert issue.category == "fetch.avatar"
    assert issue.item_id == "nsid123"
    assert issue.reason == "user not found"
