from pathlib import Path

from offlickr.ingest.testimonials import load_testimonials

FIXTURE = Path(__file__).parent.parent / "fixtures" / "mini-export"

def test_load_testimonials_received() -> None:
    t = load_testimonials(FIXTURE)
    assert len(t.received) >= 1
    assert t.received[0].author_or_subject_screen_name == "frienduser"

def test_load_testimonials_given() -> None:
    t = load_testimonials(FIXTURE)
    assert len(t.given) >= 1
    assert t.given[0].author_or_subject_screen_name == "anotherfriend"

def test_testimonial_body_is_sanitized() -> None:
    t = load_testimonials(FIXTURE)
    # script tags must be stripped by nh3
    assert "<script>" not in t.received[0].body_html
    assert "Great photos" in t.received[0].body_html
