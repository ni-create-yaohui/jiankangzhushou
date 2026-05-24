"""
健康知识报告查询服务
（SQLAlchemy 2.0 后端）
"""
from typing import Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from agent.database.db_config import with_session
from agent.database.models import HealthReport
from project.logger_handler import logger


class HealthReportService:
    """健康知识报告查询服务"""

    def __init__(self):
        pass  # 不再需要文件扫描和缓存

    @with_session
    def list_reports(self, session: Session = None) -> List[Dict]:
        reports = session.query(HealthReport).all()
        if not reports:
            return [{"report_id": "无", "title": "暂无健康知识报告", "summary": "请将健康知识JSON报告放入data/health_reports/目录"}]
        return [
            {
                "report_id": r.report_id,
                "title": r.title,
                "date": r.date or "未知",
                "summary": (r.summary or "")[:100] + "..." if len(r.summary or "") > 100 else (r.summary or ""),
            }
            for r in reports
        ]

    @with_session
    def get_report(self, report_id: str, session: Session = None) -> Optional[Dict]:
        report = session.query(HealthReport).filter_by(report_id=report_id).first()
        if report is None:
            return None
        return {
            "report_id": report.report_id,
            "title": report.title,
            "date": report.date,
            "summary": report.summary,
            "keywords": report.keywords or [],
        }

    @with_session
    def search_reports(self, query: str, session: Session = None) -> List[Dict]:
        query_lower = f"%{query.lower()}%"
        reports = session.query(HealthReport).filter(
            or_(
                HealthReport.title.ilike(query_lower),
                HealthReport.summary.ilike(query_lower),
            )
        ).all()

        results = []
        for r in reports:
            results.append({
                "report_id": r.report_id,
                "title": r.title,
                "summary": r.summary or "",
                "relevance": "high" if query.lower() in (r.title or "").lower() else "medium",
            })

        # 也检查 keywords（JSON 数组）
        if not results:
            all_reports = session.query(HealthReport).all()
            for r in all_reports:
                keywords_str = " ".join(r.keywords or []).lower()
                if query.lower() in keywords_str:
                    results.append({
                        "report_id": r.report_id,
                        "title": r.title,
                        "summary": r.summary or "",
                        "relevance": "medium",
                    })

        return results if results else [{"report_id": "无", "title": f"未找到与'{query}'相关的报告", "summary": " "}]


health_report_service = HealthReportService()
