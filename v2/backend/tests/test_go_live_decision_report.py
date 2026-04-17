from pathlib import Path
import sys


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import go_live_decision_report  # noqa: E402


def sample_payload(*, phase: str = "ready_for_pilot", ready: bool = False) -> dict:
    return {
        "frontend": {
            "status": "ok",
            "releaseLabel": "front123",
        },
        "backend": {
            "status": "ok",
            "release_label": "back123",
            "decision": {
                "title": "Bugun pilotu acabiliriz",
                "detail": "Pilot smoke ve login kontrolu ile devam edebiliriz.",
            },
            "cutover": {
                "phase": phase,
                "ready": ready,
                "summary": "Hazirlik ilerliyor",
            },
        },
    }


def test_go_live_report_marks_ready_for_pilot_when_only_cutover_is_blocked():
    report = go_live_decision_report.build_report(
        base_url="https://pilot.example.com",
        api_url="https://pilot-api.example.com",
        payload=sample_payload(),
        database_url="postgresql://pilot:secret@db.example.com/catkapinda?sslmode=require",
        default_auth_password="GucluPilotSifre!2026",
        guard_builder=lambda **kwargs: (
            {
                "passed": True,
                "summary": "Pilot deploy acilabilir.",
                "blocking_items": [],
                "future_cutover_blocking_items": ["Aktif restoran kartlarinda bos marka/sube alanlari var."],
                "recommended_next_step": "Pilotu ac.",
            }
            if kwargs["mode"] == "pilot"
            else {
                "passed": False,
                "summary": "Cutover deploy bloklu.",
                "blocking_items": ["Aktif restoran kartlarinda bos marka/sube alanlari var."],
                "recommended_next_step": "Canli domaine gecmeden once veri kalitesini temizle.",
            }
        ),
    )

    assert report["phase"] == "ready_for_pilot"
    assert report["pilot_passed"] is True
    assert report["cutover_passed"] is False
    assert report["future_cutover_blocking_items"] == [
        "Aktif restoran kartlarinda bos marka/sube alanlari var."
    ]
    assert "veri kalitesini temizle" in report["recommended_next_step"]


def test_go_live_report_marks_blocked_when_pilot_is_blocked():
    report = go_live_decision_report.build_report(
        base_url="https://pilot.example.com",
        api_url="https://pilot-api.example.com",
        payload=sample_payload(),
        database_url="postgresql://pilot:secret@db.example.com/catkapinda?sslmode=require",
        default_auth_password="GucluPilotSifre!2026",
        guard_builder=lambda **kwargs: (
            {
                "passed": False,
                "summary": "Pilot deploy bloklu.",
                "blocking_items": ["`daily_entries` tablosu eksik."],
                "future_cutover_blocking_items": [],
                "recommended_next_step": "Dogru PostgreSQL baglantisini gir.",
            }
            if kwargs["mode"] == "pilot"
            else {
                "passed": False,
                "summary": "Cutover deploy bloklu.",
                "blocking_items": ["`daily_entries` tablosu eksik."],
                "recommended_next_step": "Dogru PostgreSQL baglantisini gir.",
            }
        ),
    )

    assert report["phase"] == "blocked"
    assert report["pilot_passed"] is False
    assert report["pilot_blocking_items"] == ["`daily_entries` tablosu eksik."]


def test_go_live_report_marks_ready_for_cutover_when_both_guards_pass():
    report = go_live_decision_report.build_report(
        base_url="https://pilot.example.com",
        api_url="https://pilot-api.example.com",
        payload=sample_payload(phase="ready_for_cutover", ready=True),
        database_url="postgresql://pilot:secret@db.example.com/catkapinda?sslmode=require",
        default_auth_password="GucluPilotSifre!2026",
        guard_builder=lambda **kwargs: {
            "passed": True,
            "summary": "Deploy acilabilir.",
            "blocking_items": [],
            "future_cutover_blocking_items": [],
            "recommended_next_step": "Canli domaine gecis planini uygula.",
        },
    )

    assert report["phase"] == "ready_for_cutover"
    assert report["pilot_passed"] is True
    assert report["cutover_passed"] is True
    assert report["future_cutover_blocking_items"] == []


def test_go_live_report_markdown_includes_future_cutover_section():
    report = {
        "generated_at": "2026-04-17T10:00:00+00:00",
        "base_url": "https://pilot.example.com",
        "api_url": "https://pilot-api.example.com",
        "phase": "ready_for_pilot",
        "summary": "Pilot acilabilir, ancak cutover icin kalan blokajlar var.",
        "recommended_next_step": "Canli domaine gecmeden once veri kalitesini temizle.",
        "pilot_passed": True,
        "cutover_passed": False,
        "pilot_blocking_items": [],
        "future_cutover_blocking_items": ["Aktif restoran kartlarinda bos marka/sube alanlari var."],
        "pilot_result": {"summary": "Pilot deploy acilabilir."},
        "cutover_result": {"summary": "Cutover deploy bloklu."},
    }

    markdown = go_live_decision_report.render_markdown(report)

    assert "# Cat Kapinda CRM v2 Go-Live Decision Report" in markdown
    assert "## Cutover Karari" in markdown
    assert "### Future Cutover Blocking Items" in markdown
    assert "Aktif restoran kartlarinda bos marka/sube alanlari var." in markdown
