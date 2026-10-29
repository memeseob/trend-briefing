from publish import build_index, report_id


def test_report_id():
    assert report_id({"kind": "weekly", "date": "2026-11-02"}) == "weekly-2026-11-02"
    assert report_id({"date": "2026-10-30"}) == "daily-2026-10-30"


def test_build_index_newest_first_weekly_on_top():
    metas = [
        {"id": "daily-2026-10-29", "date": "2026-10-29", "kind": "daily"},
        {"id": "daily-2026-11-02", "date": "2026-11-02", "kind": "daily"},
        {"id": "weekly-2026-11-02", "date": "2026-11-02", "kind": "weekly"},
    ]
    assert [m["id"] for m in build_index(metas)] == ["weekly-2026-11-02", "daily-2026-11-02", "daily-2026-10-29"]
