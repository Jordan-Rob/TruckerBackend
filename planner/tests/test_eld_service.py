from planner.services.eld_service import generate_eld_logs


def test_generate_eld_logs_single_day_under_11h():
    logs = generate_eld_logs(total_drive_seconds=10 * 3600)
    assert len(logs) == 1
    segments = logs[0]["segments"]
    assert any(s["status"] == 3 for s in segments)  # has driving


def test_generate_eld_logs_multiple_days():
    logs = generate_eld_logs(total_drive_seconds=23 * 3600)
    assert len(logs) == 3  # 11h + 11h + 1h
    assert all("segments" in d for d in logs)


