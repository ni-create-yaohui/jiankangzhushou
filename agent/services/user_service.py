"""
用户服务模块 - 提供用户档案CRUD操作和健康记录管理
（SQLAlchemy 2.0 后端）
"""
from typing import Dict, List, Optional, Any

from sqlalchemy import func, cast, Integer, select
from sqlalchemy.orm import Session

from agent.database.db_config import SessionLocal, with_session
from agent.database.models import User, HealthRecord
from project.logger_handler import logger


class UserService:
    """用户服务类 - 管理用户数据和健康记录"""

    def __init__(self):
        pass  # 不再需要初始化 JSON 文件

    # ── 内部辅助 ──────────────────────────────────────────

    def _generate_user_id(self, session: Session) -> str:
        result = session.scalar(
            select(func.max(cast(func.substr(User.user_id, 2), Integer)))
        )
        max_num = result or 0
        return f"U{max_num + 1:03d}"

    @staticmethod
    def _user_to_dict(user: User) -> Dict[str, Any]:
        """ORM User → 嵌套 dict（保持原 JSON 格式）"""
        records = {}
        for hr in user.health_records:
            rec = {}
            if hr.weight is not None:
                rec["weight"] = hr.weight
            if hr.bp_systolic is not None:
                rec["blood_pressure_systolic"] = hr.bp_systolic
            if hr.bp_diastolic is not None:
                rec["blood_pressure_diastolic"] = hr.bp_diastolic
            if hr.heart_rate is not None:
                rec["heart_rate"] = hr.heart_rate
            if hr.sleep_hours is not None:
                rec["sleep_hours"] = hr.sleep_hours
            if hr.sleep_quality is not None:
                rec["sleep_quality"] = hr.sleep_quality
            if hr.steps is not None:
                rec["steps"] = hr.steps
            if hr.calories_intake is not None:
                rec["calories_intake"] = hr.calories_intake
            records[hr.date] = rec

        return {
            "basic_info": {
                "name": user.name,
                "gender": user.gender,
                "age": user.age,
                "height": user.height,
                "weight": user.weight,
                "activity_level": user.activity_level,
                "health_goal": user.health_goal,
                "created_at": user.created_at,
            },
            "health_records": records,
        }

    # ── CRUD ──────────────────────────────────────────────

    @with_session
    def create_user(
        self,
        name: str,
        gender: str = "男",
        age: int = 25,
        height: float = 170,
        weight: float = 65,
        activity_level: str = "轻度活动",
        health_goal: str = "保持健康",
        session: Session = None,
    ) -> Dict[str, Any]:
        user_id = self._generate_user_id(session)
        user = User(
            user_id=user_id,
            name=name,
            gender=gender,
            age=age,
            height=height,
            weight=weight,
            activity_level=activity_level,
            health_goal=health_goal,
        )
        session.add(user)
        result = self._user_to_dict(user)
        logger.info(f"创建用户成功: {user_id} - {name}")
        return {"user_id": user_id, "user": result}

    @with_session
    def get_user(self, user_id: str, session: Session = None) -> Optional[Dict[str, Any]]:
        user = session.query(User).filter_by(user_id=user_id).first()
        if user is None:
            return None
        return self._user_to_dict(user)

    @with_session
    def list_users(self, session: Session = None) -> Dict[str, Dict]:
        users = session.query(User).all()
        return {u.user_id: self._user_to_dict(u) for u in users}

    @with_session
    def update_user(self, user_id: str, session: Session = None, **kwargs) -> Optional[Dict[str, Any]]:
        user = session.query(User).filter_by(user_id=user_id).first()
        if user is None:
            return None
        valid_fields = ["name", "gender", "age", "height", "weight", "activity_level", "health_goal"]
        for field in valid_fields:
            if field in kwargs:
                setattr(user, field, kwargs[field])
        return self._user_to_dict(user)

    @with_session
    def delete_user(self, user_id: str, session: Session = None) -> bool:
        user = session.query(User).filter_by(user_id=user_id).first()
        if user is None:
            return False
        session.delete(user)
        return True

    @with_session
    def add_health_record(
        self,
        user_id: str,
        date: str,
        weight: float = None,
        blood_pressure_systolic: int = None,
        blood_pressure_diastolic: int = None,
        heart_rate: int = None,
        sleep_hours: float = None,
        sleep_quality: int = None,
        steps: int = None,
        calories_intake: float = None,
        session: Session = None,
    ) -> bool:
        user = session.query(User).filter_by(user_id=user_id).first()
        if user is None:
            return False

        record = HealthRecord(
            user_id=user_id,
            date=date,
            weight=weight,
            bp_systolic=blood_pressure_systolic,
            bp_diastolic=blood_pressure_diastolic,
            heart_rate=heart_rate,
            sleep_hours=sleep_hours,
            sleep_quality=sleep_quality,
            steps=steps,
            calories_intake=calories_intake,
        )
        session.add(record)
        return True

    def get_user_summary(self, user_id: str, session: Session = None) -> str:
        user = self.get_user(user_id, session=session)
        if not user:
            return f"未找到用户ID: {user_id}"

        basic = user.get("basic_info", {})
        records = user.get("health_records", {})

        height = basic.get("height", 170)
        weight = basic.get("weight", 65)
        bmi = weight / (height / 100) ** 2

        if bmi < 18.5:
            bmi_category = "偏瘦"
        elif bmi < 24:
            bmi_category = "正常"
        elif bmi < 28:
            bmi_category = "偏胖"
        else:
            bmi_category = "肥胖"

        return f"""【用户档案】
用户ID: {user_id}
姓名: {basic.get('name', '未命名')}
性别: {basic.get('gender', '未知')}
年龄: {basic.get('age', '未知')}岁
身高: {basic.get('height', 0):.0f}cm
体重: {basic.get('weight', 0):.0f}kg
BMI: {bmi:.1f}（{bmi_category}）
活动水平: {basic.get('activity_level', '未知')}
健康目标: {basic.get('health_goal', '未知')}
创建时间: {basic.get('created_at', '未知')}
健康记录数: {len(records)} 条
"""


# 全局单例
user_service = UserService()
