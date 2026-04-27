"""
健康知识报告查询服务
"""
import json
from pathlib import Path
from typing import Dict, List, Optional

from project.logger_handler import logger


class HealthReportService:
    """健康知识报告查询服务"""

    def __init__(self, reports_dir: str = None):
        if reports_dir is None:
            project_root = Path(__file__).parent.parent.parent
            reports_dir = project_root / "data" / "health_reports"

        self.reports_dir = Path(reports_dir)
        self._reports_cache = None

    def _load_all_reports(self) -> Dict:
        if self._reports_cache is not None:
            return self._reports_cache

        self._reports_cache = {}

        if not self.reports_dir.exists():
            logger.warning(f"报告目录不存在: {self.reports_dir}")
            return self._reports_cache

        for report_file in self.reports_dir.glob("*.json"):
            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    report = json.load(f)
                    report_id = report.get("report_id", report_file.stem)
                    self._reports_cache[report_id] = report
            except Exception as e:
                logger.error(f"加载报告失败 {report_file}: {e}")

        return self._reports_cache

    def list_reports(self) -> List[Dict]:
        reports = self._load_all_reports()
        if not reports:
            return [{"report_id": "无", "title": "暂无健康知识报告", "summary": "请将健康知识JSON报告放入data/health_reports/目录"}]
        return [
            {
                "report_id": rid,
                "title": r.get("title", "未命名"),
                "date": r.get("date", "未知"),
                "summary": r.get("summary", "")[:100] + "..."
            }
            for rid, r in reports.items()
        ]

    def get_report(self, report_id: str) -> Optional[Dict]:
        reports = self._load_all_reports()
        return reports.get(report_id)

    def search_reports(self, query: str) -> List[Dict]:
        reports = self._load_all_reports()
        query_lower = query.lower()

        results = []
        for rid, report in reports.items():
            title = report.get("title", "").lower()
            summary = report.get("summary", "").lower()
            keywords = " ".join(report.get("keywords", [])).lower()

            if query_lower in title or query_lower in summary or query_lower in keywords:
                results.append({
                    "report_id": rid,
                    "title": report.get("title", "未命名"),
                    "summary": report.get("summary", ""),
                    "relevance": "high" if query_lower in title else "medium"
                })

        return results if results else [{"report_id": "无", "title": f"未找到与'{query}'相关的报告", "summary": ""}]


health_report_service = HealthReportService()
