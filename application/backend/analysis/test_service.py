from application.backend.analysis.service import AnalysisService, collect_insertion_requests


def test_collect_insertion_requests_keeps_latest_phase():
    frames = [
        {"insertion_requests": [{"request_id": "insert-0001", "accepted_step": 2, "phase": "queued"}]},
        {"insertion_requests": [{"request_id": "insert-0001", "accepted_step": 2, "phase": "completed"}]},
    ]
    records = collect_insertion_requests(frames)
    assert records == [{"request_id": "insert-0001", "accepted_step": 2, "phase": "completed"}]


def test_saved_run_contains_replayable_insertion_records(tmp_path):
    service = AnalysisService(tmp_path)
    payload = {
        "factory_id": "grid_factory_new",
        "algorithm": "pso+astar+nearest",
        "frames": [
            {"env_timeline": "T+2s", "jobs": [], "insertion_requests": [
                {"request_id": "insert-0001", "accepted_step": 2, "phase": "queued"},
            ]},
            {"env_timeline": "T+9s", "jobs": [], "insertion_requests": [
                {"request_id": "insert-0001", "accepted_step": 2, "phase": "completed"},
            ]},
        ],
        "metricsTimeline": [],
        "events": [{"type": "job_insertion_phase_changed", "step": 2}],
    }
    result = service.save_run(payload)
    saved = service.get_run(result["id"])
    assert saved["schema_version"] == "1.1"
    assert saved["insertionRequests"][0]["phase"] == "completed"
    assert saved["summary"]["insertion_count"] == 1
    assert saved["summary"]["insertion_completed"] == 1
