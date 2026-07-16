"""
AnalysisService — Run 仓库的纯逻辑层（无 FastAPI 依赖）。

职责：
- list_runs:   扫描 archive_dir，返回轻量元信息列表
- get_run:     读完整 Run JSON
- save_run:    校验 + 补字段 + 重算 summary + 原子写入
- delete_run:  删除文件

设计要点：
- 工厂无关，StaticFactory / 容器化通路共用
- 文件名即 id，扁平结构（见 0701日志详细设计.md §1）
- 容错优先：单个坏文件不能炸整个列表 / 单次保存
- 路径安全：禁止 .. / 绝对路径
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "1.1"


def collect_insertion_requests(
    frames: list | None,
    explicit: list | None = None,
) -> list:
    records: dict[str, dict] = {}
    for record in explicit or []:
        if isinstance(record, dict) and record.get("request_id"):
            records[str(record["request_id"])] = record
    for frame in frames or []:
        if not isinstance(frame, dict):
            continue
        for record in frame.get("insertion_requests") or []:
            if isinstance(record, dict) and record.get("request_id"):
                records[str(record["request_id"])] = record
    return sorted(
        records.values(),
        key=lambda record: float(record.get("accepted_step") or 0),
    )
DEFAULT_ARCHIVE_DIR = Path("./dataset/run")

# 文件名规范字符集（factory_id / algorithm / stem 都要满足）
_SAFE_NAME_RE = re.compile(r"[^a-z0-9_-]+")


def _safe_component(raw: str, fallback: str = "unknown") -> str:
    """规范化命名段：lowercase + 非法字符替为 _ + 折叠连续 _ + 去首尾 _。"""
    if not raw:
        return fallback
    s = str(raw).strip().lower()
    s = _SAFE_NAME_RE.sub("_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or fallback


def _normalize_filename(
    factory_id: str,
    algorithm: str,
    source: str = "archive",
    original_stem: str | None = None,
) -> str:
    """生成规范化文件名 stem（不含 .json 后缀）。

    archive:  <factory_id>__<algorithm>__<ts>
    imported: imported__<stem>__<ts>
    时间戳由调用方在 save_run 时拼接（这里不含 ts，仅返回前缀）。
    """
    if source == "imported":
        stem = _safe_component(original_stem or "imported")[:40]
        return f"imported__{stem}"
    fac = _safe_component(factory_id, "unknown")
    algo = _safe_component(algorithm, "none") if algorithm else "none"
    return f"{fac}__{algo}"


def _timestamp_str() -> str:
    """本地时间 YYYYMMDD_HHMMSS（文件名友好）。"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def compute_summary(
    frames: list | None,
    metrics_timeline: list | None,
    events: list | None,
    insertion_requests: list | None = None,
) -> dict:
    """从三流派生 summary。对外部 JSON 容错：缺失返回 0/null，不抛异常。"""
    frames = frames or []
    metrics_timeline = metrics_timeline or []
    events = events or []

    last_frame = frames[-1] if frames else {}
    jobs = (last_frame or {}).get("jobs") or []
    completed_jobs = sum(1 for j in jobs if j and j.get("is_completed"))
    total_jobs = len(jobs)

    utils = [
        p.get("metrics", {}).get("machine_utilization")
        for p in metrics_timeline
        if isinstance(p, dict)
        and isinstance(p.get("metrics"), dict)
        and isinstance(p["metrics"].get("machine_utilization"), (int, float))
    ]
    avg_utilization = sum(utils) / len(utils) if utils else None

    event_counts: dict[str, int] = {}
    for e in events:
        if not isinstance(e, dict):
            continue
        t = e.get("type") or "unknown"
        event_counts[t] = event_counts.get(t, 0) + 1
    insertion_requests = collect_insertion_requests(frames, insertion_requests)

    return {
        "total_steps": len(frames),
        "completed_jobs": completed_jobs,
        "total_jobs": total_jobs,
        "avg_utilization": avg_utilization,
        "event_total": len(events),
        "event_counts": event_counts,
        "insertion_count": len(insertion_requests),
        "insertion_completed": sum(
            1 for record in insertion_requests if record.get("phase") == "completed"
        ),
        "insertion_failed": sum(
            1 for record in insertion_requests if record.get("phase") == "failed"
        ),
    }


class AnalysisService:
    """Run 仓库服务（线程安全适合单进程 FastAPI 用）。"""

    def __init__(self, archive_dir: Path | str | None = None):
        self.archive_dir = Path(archive_dir) if archive_dir else DEFAULT_ARCHIVE_DIR
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    # ============ 列表（轻）============

    def list_runs(self) -> list[dict]:
        """扫描目录，返回所有 Run 的轻量元信息。

        每条 dict 含：id, source, factory_id, algorithm, created_at,
                       total_steps, summary, original_filename
        不含 frames/metricsTimeline/events（重数据按需 get_run 拉）。

        容错：损坏 / 半截 JSON 跳过 + warning，不影响整体列表。
        排序：created_at 倒序（新的在前）。
        """
        items: list[dict] = []
        for entry in sorted(self.archive_dir.glob("*.json")):
            try:
                with entry.open("r", encoding="utf-8") as f:
                    # 只读到能拿元信息的程度——但 JSON 没法只读头部，
                    # 全量解析后剥轻字段。50 个文件 1 秒内可接受。
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("not a json object")
                items.append(self._meta_from_run(data, entry.stem))
            except Exception as e:
                logger.warning("[analysis] 跳过损坏文件 %s: %s", entry.name, e)
                continue
        items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return items

    @staticmethod
    def _meta_from_run(data: dict, fallback_id: str) -> dict:
        """从完整 Run 剥轻量元信息。"""
        return {
            "id": data.get("id") or fallback_id,
            "source": data.get("source") or "archive",
            "factory_id": data.get("factory_id"),
            "algorithm": data.get("algorithm"),
            "created_at": data.get("created_at"),
            "original_filename": data.get("original_filename"),
            "total_steps": data.get("total_steps")
                or (len(data.get("frames") or [])),
            "summary": data.get("summary") or {},
        }

    # ============ 详情（重）============

    def get_run(self, run_id: str) -> dict | None:
        """读完整 Run JSON。run_id 即文件名 stem。

        路径安全：run_id 只允许 [a-z0-9_-]，禁止 . / \\ 等穿越字符。
        """
        safe_id = self._validate_run_id(run_id)
        if safe_id is None:
            return None
        path = self.archive_dir / f"{safe_id}.json"
        if not path.is_file():
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("[analysis] 读取失败 %s: %s", path.name, e)
            return None

    # ============ 落盘 ============

    def save_run(self, payload: dict, source: str = "archive") -> dict:
        """校验 + 补字段 + 重算 summary + 原子写入。

        Args:
            payload: 前端发来的 Run JSON（可能含部分字段）
            source: "archive" (本地产出) | "imported" (用户上传)

        Returns:
            {id, filename, path, created}

        Raises:
            ValueError: 必要字段缺失（frames/metricsTimeline/events）
        """
        if not isinstance(payload, dict):
            raise ValueError("payload must be a json object")

        frames = payload.get("frames")
        metrics_timeline = payload.get("metricsTimeline")
        events = payload.get("events")
        insertion_requests = payload.get("insertionRequests", [])
        # 三流必备校验（允许空数组，但不允许缺失）
        if frames is None or metrics_timeline is None or events is None:
            raise ValueError(
                "missing required field: frames / metricsTimeline / events"
            )
        if not isinstance(frames, list) or not isinstance(metrics_timeline, list) \
                or not isinstance(events, list):
            raise ValueError("frames / metricsTimeline / events must be arrays")
        if not isinstance(insertion_requests, list):
            raise ValueError("insertionRequests must be an array")
        insertion_requests = collect_insertion_requests(frames, insertion_requests)

        factory_id = payload.get("factory_id") or "unknown"
        algorithm = payload.get("algorithm") or ""
        created_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        ts = _timestamp_str()

        # 文件名前缀（不含时间戳）
        if source == "imported":
            original_stem = Path(payload.get("original_filename") or "imported").stem
            prefix = _normalize_filename(factory_id, algorithm, "imported", original_stem)
        else:
            prefix = _normalize_filename(factory_id, algorithm, "archive")
        filename_stem = f"{prefix}__{ts}"

        # 撞名追加短 hash
        final_stem = self._resolve_collision(filename_stem, payload)

        # id = 文件名 stem（去掉 .json 后缀）
        run_id = final_stem

        # 重算 summary（永远派生，忽略外部 summary 字段）
        summary = compute_summary(frames, metrics_timeline, events, insertion_requests)

        # started_at / finished_at
        started_at = (frames[0].get("env_timeline") if frames else None) \
            or (frames[0].get("timestamp") if frames else None)
        finished_at = (frames[-1].get("env_timeline") if frames else None) \
            or (frames[-1].get("timestamp") if frames else None)

        run_doc = {
            "schema_version": SCHEMA_VERSION,
            "id": run_id,
            "source": source,
            "original_filename":
                payload.get("original_filename") if source == "imported" else None,
            "factory_id": factory_id,
            "algorithm": algorithm or None,
            "created_at": created_at,
            "started_at": started_at,
            "finished_at": finished_at,
            "total_steps": len(frames),
            "config_snapshot": payload.get("config_snapshot") or None,
            "frames": frames,
            "metricsTimeline": metrics_timeline,
            "events": events,
            "insertionRequests": insertion_requests,
            "summary": summary,
        }

        # 原子写入：tmp 文件 + os.replace
        final_path = self.archive_dir / f"{final_stem}.json"
        tmp_fd, tmp_path = tempfile.mkstemp(
            prefix=f".{final_stem}.", suffix=".tmp", dir=str(self.archive_dir)
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(run_doc, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, final_path)
        except Exception:
            # 清理 tmp 文件
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        logger.info(
            "[analysis] saved run id=%s source=%s factory=%s file=%s",
            run_id, source, factory_id, final_path.name,
        )
        return {
            "id": run_id,
            "filename": final_path.name,
            "path": str(final_path),
            "created_at": created_at,
        }

    def _resolve_collision(self, stem: str, payload: dict) -> str:
        """若 archive_dir/<stem>.json 已存在，追加 4 位内容 hash 后缀。"""
        candidate = stem
        if (self.archive_dir / f"{candidate}.json").exists():
            content_hash = hashlib.sha256(
                json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()[:4]
            candidate = f"{stem}__{content_hash}"
        return candidate

    # ============ 删除 ============

    def delete_run(self, run_id: str) -> bool:
        """删除 Run 文件。返回是否删除成功（文件不存在返回 False）。"""
        safe_id = self._validate_run_id(run_id)
        if safe_id is None:
            return False
        path = self.archive_dir / f"{safe_id}.json"
        if not path.is_file():
            return False
        try:
            path.unlink()
            logger.info("[analysis] deleted run id=%s", run_id)
            return True
        except Exception as e:
            logger.warning("[analysis] 删除失败 %s: %s", path.name, e)
            return False

    # ============ 路径安全 ============

    @staticmethod
    def _validate_run_id(run_id: str) -> str | None:
        """run_id 只允许 [a-z0-9_-]，长度 ≤ 200，禁止穿越。"""
        if not run_id or not isinstance(run_id, str):
            return None
        if len(run_id) > 200:
            return None
        if not re.fullmatch(r"[a-z0-9_-]+", run_id):
            return None
        return run_id
