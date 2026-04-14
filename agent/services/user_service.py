"""
用户服务模块 - 提供用户档案CRUD操作和健康记录管理
"""
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from project.logger_handler import logger


class UserService:
    """用户服务类 - 管理用户数据和健康记录"""

    def __init__(self, data_file: str = None):
        if data_file is None:
            project_root = Path(__file__).parent.parent.parent
            data_file = project_root / "data" / "health_data" / "users.json"

        self.data_file = Path(data_file)
        self._ensure_data_file()

    def _ensure_data_file(self):
        if not self.data_file.exists():
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            initial_data = {
                "metadata": {
                    "version": "1.0",
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
                "users": {}
            }
            self._save_data(initial_data)
            logger.info(f"创建用户数据文件: {self.data_file}")

    def _load_data(self) -> Dict:
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载用户数据失败: {e}")
            return {"metadata": {}, "users": {}}

    def _save_data(self, data: Dict):
        data["metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"用户数据已保存")

    def _generate_user_id(self) -> str:
        data = self._load_data()
        existing_ids = list(data.get("users", {}).keys())
        max_num = 0
        for uid in existing_ids:
            if uid.startswith("U"):
                try:
                    num = int(uid[1:])
                    max_num = max(max_num, num)
                except ValueError:
                    continue
        return f"U{max_num + 1:03d}"

    def create_user(
        self,
        name: str,
        gender: str = "男",
        age: int = 25,
        height: float = 170,
        weight: float = 65,
        activity_level: str = "轻度活动",
        health_goal: str = "保持健康"
    ) -> Dict[str, Any]:
        data = self._load_data()
        user_id = self._generate_user_id()

        user = {
            "basic_info": {
                "name": name,
                "gender": gender,
                "age": age,
                "height": height,
                "weight": weight,
                "activity_level": activity_level,
                "health_goal": health_goal,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            "health_records": {}
        }

        data["users"][user_id] = user
        self._save_data(data)

        logger.info(f"创建用户成功: {user_id} - {name}")
        return {"user_id": user_id, "user": user}

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        data = self._load_data()
        return data.get("users", {}).get(user_id)

    def list_users(self) -> Dict[str, Dict]:
        data = self._load_data()
        return data.get("users", {})

    def update_user(self, user_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        data = self._load_data()
        users = data.get("users", {})

        if user_id not in users:
            return None

        user = users[user_id]
        valid_fields = ["name", "gender", "age", "height", "weight", "activity_level", "health_goal"]
        for field in valid_fields:
            if field in kwargs:
                user["basic_info"][field] = kwargs[field]

        data["users"][user_id] = user
        self._save_data(data)
        return user

    def delete_user(self, user_id: str) -> bool:
        data = self._load_data()
        users = data.get("users", {})

        if user_id not in users:
            return False

        del data["users"][user_id]
        self._save_data(data)
        return True

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
        calories_intake: float = None
    ) -> bool:
        data = self._load_data()
        users = data.get("users", {})

        if user_id not in users:
            return False

        record = {}
        if weight is not None:
            record["weight"] = weight
        if blood_pressure_systolic is not None:
            record["blood_pressure_systolic"] = blood_pressure_systolic
        if blood_pressure_diastolic is not None:
            record["blood_pressure_diastolic"] = blood_pressure_diastolic
        if heart_rate is not None:
            record["heart_rate"] = heart_rate
        if sleep_hours is not None:
            record["sleep_hours"] = sleep_hours
        if sleep_quality is not None:
            record["sleep_quality"] = sleep_quality
        if steps is not None:
            record["steps"] = steps
        if calories_intake is not None:
            record["calories_intake"] = calories_intake

        if record:
            users[user_id]["health_records"][date] = record
            self._save_data(data)

        return True

    def get_user_summary(self, user_id: str) -> str:
        user = self.get_user(user_id)
        if not user:
            return f"未找到用户ID: {user_id}"

        basic = user.get("basic_info", {})
        records = user.get("health_records", {})

        # 计算BMI
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

        summary = f"""【用户档案】
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
        return summary


user_service = UserService()
