"""
健康枚举定义模块 - 健康管理相关枚举
提供性别、运动水平、健康目标、饮食类型等枚举
"""
from enum import Enum
from typing import List


class Gender(str, Enum):
    """性别"""
    MALE = "男"
    FEMALE = "女"
    OTHER = "其他"


class ActivityLevel(str, Enum):
    """活动水平"""
    SEDENTARY = "久坐不动"
    LIGHT = "轻度活动"
    MODERATE = "中度活动"
    ACTIVE = "积极运动"
    VERY_ACTIVE = "高强度运动"


class HealthGoal(str, Enum):
    """健康目标"""
    LOSE_WEIGHT = "减脂瘦身"
    GAIN_MUSCLE = "增肌塑形"
    MAINTAIN = "保持健康"
    IMPROVE_ENDURANCE = "提升耐力"
    STRESS_RELIEF = "减压放松"
    DISEASE_PREVENTION = "疾病预防"


class DietType(str, Enum):
    """饮食类型"""
    BALANCED = "均衡饮食"
    VEGETARIAN = "素食"
    LOW_CARB = "低碳水"
    HIGH_PROTEIN = "高蛋白"
    MEDITERRANEAN = "地中海饮食"
    KETO = "生酮饮食"


class ExerciseType(str, Enum):
    """运动类型"""
    RUNNING = "跑步"
    SWIMMING = "游泳"
    CYCLING = "骑行"
    YOGA = "瑜伽"
    STRENGTH = "力量训练"
    WALKING = "步行"
    HIIT = "高强度间歇"
    BASKETBALL = "篮球"
    BADMINTON = "羽毛球"
    DANCING = "舞蹈"


class FitnessLevel(str, Enum):
    """运动水平"""
    BEGINNER = "初学者"
    INTERMEDIATE = "中级"
    ADVANCED = "高级"
    PROFESSIONAL = "专业"


# 获取枚举列表的辅助函数
def get_genders() -> List[str]:
    return [g.value for g in Gender]

def get_activity_levels() -> List[str]:
    return [a.value for a in ActivityLevel]

def get_health_goals() -> List[str]:
    return [h.value for h in HealthGoal]

def get_diet_types() -> List[str]:
    return [d.value for d in DietType]

def get_exercise_types() -> List[str]:
    return [e.value for e in ExerciseType]

def get_fitness_levels() -> List[str]:
    return [f.value for f in FitnessLevel]
