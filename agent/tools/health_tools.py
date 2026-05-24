"""
健康工具模块 - 提供健康数据管理、BMI计算、饮食分析、运动推荐等能力
"""
import json
from langchain_core.tools import tool
from project.logger_handler import logger
from rag.rag_service import RagSummarizeService
from agent.services.user_service import user_service
from agent.services.health_report_service import health_report_service
from agent.tools.health_enums import get_genders, get_activity_levels

rag = RagSummarizeService()

# 中国居民膳食营养素参考摄入量（部分）
NUTRIENT_DATABASE = {
    "米饭(一碗)": {"calories": 230, "protein": 4.3, "carbs": 50, "fat": 0.5, "fiber": 0.6},
    "面条(一碗)": {"calories": 280, "protein": 8.5, "carbs": 55, "fat": 1.5, "fiber": 1.5},
    "鸡胸肉(100g)": {"calories": 165, "protein": 31, "carbs": 0, "fat": 3.6, "fiber": 0},
    "鸡蛋(1个)": {"calories": 78, "protein": 6, "carbs": 0.6, "fat": 5.3, "fiber": 0},
    "牛奶(250ml)": {"calories": 160, "protein": 8, "carbs": 12, "fat": 8, "fiber": 0},
    "苹果(1个)": {"calories": 95, "protein": 0.5, "carbs": 25, "fat": 0.3, "fiber": 4.4},
    "香蕉(1根)": {"calories": 105, "protein": 1.3, "carbs": 27, "fat": 0.4, "fiber": 3.1},
    "西兰花(100g)": {"calories": 34, "protein": 2.8, "carbs": 7, "fat": 0.4, "fiber": 2.6},
    "豆腐(100g)": {"calories": 76, "protein": 8, "carbs": 1.9, "fat": 4.8, "fiber": 0.3},
    "三文鱼(100g)": {"calories": 208, "protein": 20, "carbs": 0, "fat": 13, "fiber": 0},
    "牛肉(100g)": {"calories": 250, "protein": 26, "carbs": 0, "fat": 15, "fiber": 0},
    "红薯(100g)": {"calories": 86, "protein": 1.6, "carbs": 20, "fat": 0.1, "fiber": 3},
    "燕麦(50g)": {"calories": 195, "protein": 6.5, "carbs": 34, "fat": 3.5, "fiber": 5},
    "酸奶(200ml)": {"calories": 120, "protein": 6, "carbs": 15, "fat": 3, "fiber": 0},
    "核桃(30g)": {"calories": 196, "protein": 4.6, "carbs": 6.4, "fat": 19.6, "fiber": 2},
    "菠菜(100g)": {"calories": 23, "protein": 2.9, "carbs": 3.6, "fat": 0.4, "fiber": 2.2},
    "番茄(1个)": {"calories": 22, "protein": 1.1, "carbs": 4.8, "fat": 0.2, "fiber": 1.5},
    "黄瓜(1根)": {"calories": 16, "protein": 0.7, "carbs": 3.6, "fat": 0.1, "fiber": 0.5},
    "全麦面包(2片)": {"calories": 180, "protein": 7, "carbs": 34, "fat": 2, "fiber": 4},
    "花生酱(2勺)": {"calories": 188, "protein": 7, "carbs": 6, "fat": 16, "fiber": 2},
    "虾(100g)": {"calories": 99, "protein": 24, "carbs": 0.2, "fat": 0.3, "fiber": 0},
    "猪肉(100g)": {"calories": 242, "protein": 20, "carbs": 1.5, "fat": 18, "fiber": 0},
}


# ==================== 核心计算函数（@tool 和 REST API 共用） ====================

def _compute_bmi_core(height: float, weight: float) -> dict:
    """BMI 核心计算，返回结构化字典"""
    if height <= 0 or weight <= 0:
        raise ValueError("身高和体重必须为正数")
    height_m = height / 100
    bmi = weight / (height_m ** 2)
    if bmi < 18.5:
        category = "偏瘦"
        advice = "建议适当增加营养摄入，多吃优质蛋白质和碳水化合物，配合适度力量训练增加肌肉量。"
        color = "blue"
    elif bmi < 24:
        category = "正常"
        advice = "体重健康，请继续保持均衡饮食和规律运动。"
        color = "green"
    elif bmi < 28:
        category = "偏胖"
        advice = "建议控制饮食热量摄入，增加有氧运动（如快走、慢跑），每周至少150分钟中等强度运动。"
        color = "orange"
    else:
        category = "肥胖"
        advice = "建议在医生指导下进行体重管理，控制饮食热量，循序渐进增加运动量，注意监测血压和血糖。"
        color = "red"
    ideal_min = 18.5 * height_m ** 2
    ideal_max = 24 * height_m ** 2
    return {
        "bmi": round(bmi, 1),
        "category": category,
        "advice": advice,
        "color": color,
        "ideal_weight_min": round(ideal_min, 1),
        "ideal_weight_max": round(ideal_max, 1),
    }


def _compute_calorie_core(gender: str, age: int, height: float, weight: float, activity_level: str = "轻度活动") -> dict:
    """每日热量核心计算（Mifflin-St Jeor），返回结构化字典"""
    if gender == "男":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    factors = {"久坐不动": 1.2, "轻度活动": 1.375, "中度活动": 1.55, "积极运动": 1.725, "高强度运动": 1.9}
    factor = factors.get(activity_level, 1.375)
    tdee = bmr * factor
    return {
        "bmr": round(bmr, 0),
        "tdee": round(tdee, 0),
        "factor": factor,
        "protein_g": round(tdee * 0.30 / 4, 0),
        "carb_g": round(tdee * 0.40 / 4, 0),
        "fat_g": round(tdee * 0.30 / 9, 0),
        "lose_weight": round(tdee - 500, 0),
        "maintain": round(tdee, 0),
        "gain_muscle": round(tdee + 300, 0),
    }


def calculate_bmi_structured(height: float, weight: float) -> dict:
    """计算 BMI，返回结构化字典（供 api_server 调用）"""
    core = _compute_bmi_core(height, weight)
    return {
        "bmi": core["bmi"],
        "category": core["category"],
        "ideal_weight_min": core["ideal_weight_min"],
        "ideal_weight_max": core["ideal_weight_max"],
    }


def calculate_daily_calorie_structured(gender: str, age: int, height: float, weight: float, activity_level: str = "轻度活动") -> dict:
    """计算每日热量需求，返回结构化字典（供 api_server 调用）"""
    core = _compute_calorie_core(gender, age, height, weight, activity_level)
    return {
        "bmr": core["bmr"],
        "tdee": core["tdee"],
        "lose_weight": core["lose_weight"],
        "maintain": core["maintain"],
        "gain_muscle": core["gain_muscle"],
    }


# ==================== 健康知识检索工具 ====================

@tool(description="从向量存储中检索健康、医疗、营养、运动等专业资料")
def rag_summarize(query: str) -> str:
    """从知识库检索专业资料"""
    return rag.rag_summarize(query)


# ==================== 健康分析工具 ====================

@tool(description="计算BMI指数并给出健康评估。参数height为身高(厘米)，weight为体重(公斤)")
def calculate_bmi(height: float, weight: float) -> str:
    """计算BMI指数"""
    if height <= 0 or weight <= 0:
        return "身高和体重必须为正数。"

    core = _compute_bmi_core(height, weight)

    result = f"""【BMI健康评估】

您的BMI指数：{core['bmi']}
健康分类：{core['category']}

BMI参考标准（中国标准）：
  - 偏瘦：BMI < 18.5
  - 正常：18.5 ≤ BMI < 24
  - 偏胖：24 ≤ BMI < 28
  - 肥胖：BMI ≥ 28

基于您的身高 {height:.0f}cm，理想体重范围：
  - 下限：{core['ideal_weight_min']} kg
  - 上限：{core['ideal_weight_max']} kg

健康建议：
{core['advice']}

注意：BMI仅供参考，不能完全反映身体成分（如肌肉量、体脂率等）。如有疑虑，请咨询专业医生。"""

    return result


@tool(description="计算每日推荐摄入热量。参数gender为性别(男/女)，age为年龄，height为身高(cm)，weight为体重(kg)，activity_level为活动水平(久坐不动/轻度活动/中度活动/积极运动/高强度运动)")
def calculate_daily_calorie(
    gender: str,
    age: int,
    height: float,
    weight: float,
    activity_level: str = "轻度活动"
) -> str:
    """计算每日推荐摄入热量（基于Mifflin-St Jeor公式）"""
    core = _compute_calorie_core(gender, age, height, weight, activity_level)

    protein_cal = core["tdee"] * 0.30
    carb_cal = core["tdee"] * 0.40
    fat_cal = core["tdee"] * 0.30

    result = f"""【每日热量需求分析】

基本信息：
  - 性别：{gender}
  - 年龄：{age}岁
  - 身高：{height:.0f}cm
  - 体重：{weight:.0f}kg
  - 活动水平：{activity_level}

计算结果：
  - 基础代谢率(BMR)：{core['bmr']:.0f} kcal/天
  - 每日总消耗(TDEE)：{core['tdee']:.0f} kcal/天

每日推荐营养素摄入：
  - 蛋白质：{core['protein_g']:.0f}g（{protein_cal:.0f} kcal，占30%）
  - 碳水化合物：{core['carb_g']:.0f}g（{carb_cal:.0f} kcal，占40%）
  - 脂肪：{core['fat_g']:.0f}g（{fat_cal:.0f} kcal，占30%）

不同目标的推荐摄入：
  - 减脂（-500kcal）：{core['lose_weight']:.0f} kcal/天
  - 保持体重：{core['maintain']:.0f} kcal/天
  - 增肌（+300kcal）：{core['gain_muscle']:.0f} kcal/天

注意：以上为参考值，实际需求因个人体质而异。建议咨询营养师获取个性化方案。"""

    return result


@tool(description=(
    "分析食物的营养成分和饮食结构。提供食物名称列表，返回每项营养数据和整体膳食评估。"
    "参数foods为食物名称列表，如 [\"米饭(一碗)\", \"鸡胸肉(100g)\", \"鸡蛋(1个)\"]"
))
def analyze_nutrition(foods: list) -> str:
    """分析食物营养：优先查知识图谱，无结果回退内置食物库"""
    from agent.tools.kg_tools import _kg_food_nutrients

    total_calories = 0
    total_protein = 0
    total_carbs = 0
    total_fat = 0
    total_fiber = 0
    details = []

    for item in foods:
        if isinstance(item, list):
            food_name = str(item[0])
            quantity = float(item[1]) if len(item) > 1 else 1
        else:
            food_name = str(item)
            quantity = 1

        # 优先从知识图谱查营养数据（返回结构化 dict）
        kg_result = _kg_food_nutrients(food_name)
        if kg_result:
            # 计入宏观营养统计
            total_calories += kg_result.get("calories", 0) * quantity
            total_protein += kg_result.get("protein", 0) * quantity
            total_carbs += kg_result.get("carbs", 0) * quantity
            total_fat += kg_result.get("fat", 0) * quantity
            total_fiber += kg_result.get("fiber", 0) * quantity

            # 构建显示文本
            desc_parts = []
            if kg_result.get("nutrients"):
                desc_parts.append(f"含有营养素：{', '.join(kg_result['nutrients'])}")
            for k in ("calories", "protein", "carbs", "fat"):
                if k in kg_result:
                    desc_parts.append(f"{k}: {kg_result[k]}")
            details.append(f"  {food_name} x{quantity}（图谱数据）: {'; '.join(desc_parts)}")
            continue

        # 回退到内置食物库
        food_data = NUTRIENT_DATABASE.get(food_name)
        if food_data:
            cal = food_data["calories"] * quantity
            pro = food_data["protein"] * quantity
            carb = food_data["carbs"] * quantity
            fat = food_data["fat"] * quantity
            fib = food_data["fiber"] * quantity

            total_calories += cal
            total_protein += pro
            total_carbs += carb
            total_fat += fat
            total_fiber += fib

            details.append(f"  {food_name} x{quantity}: {cal:.0f}kcal, 蛋白质{pro:.1f}g, 碳水{carb:.1f}g, 脂肪{fat:.1f}g")
        else:
            details.append(f"  {food_name} x{quantity}: 暂无营养数据")

    if total_calories == 0:
        if details:
            return "【饮食营养分析】\n\n摄入明细：\n" + "\n".join(details)
        return "未找到任何食物营养数据。支持的食物：" + "、".join(list(NUTRIENT_DATABASE.keys())[:10]) + "等。"

    protein_ratio = (total_protein * 4 / total_calories * 100) if total_calories > 0 else 0
    carb_ratio = (total_carbs * 4 / total_calories * 100) if total_calories > 0 else 0
    fat_ratio = (total_fat * 9 / total_calories * 100) if total_calories > 0 else 0

    assessment = []
    if protein_ratio < 15:
        assessment.append("蛋白质摄入偏低，建议增加优质蛋白（如鸡蛋、鸡胸肉、豆腐等）")
    elif protein_ratio > 35:
        assessment.append("蛋白质摄入偏高，注意适量即可")
    else:
        assessment.append("蛋白质摄入比例合理")

    if carb_ratio < 40:
        assessment.append("碳水化合物摄入偏低，适量碳水是身体能量来源")
    elif carb_ratio > 65:
        assessment.append("碳水化合物摄入偏高，建议减少精制碳水，增加全谷物")
    else:
        assessment.append("碳水化合物摄入比例合理")

    if fat_ratio < 20:
        assessment.append("脂肪摄入偏低，适量健康脂肪有助于营养吸收")
    elif fat_ratio > 35:
        assessment.append("脂肪摄入偏高，建议减少油炸食品和高脂食物")
    else:
        assessment.append("脂肪摄入比例合理")

    if total_fiber < 25:
        assessment.append("膳食纤维不足（建议25-30g/天），多吃蔬菜水果和全谷物")

    result = f"""【饮食营养分析】

摄入明细：
{chr(10).join(details)}

营养总量：
  - 总热量：{total_calories:.0f} kcal
  - 蛋白质：{total_protein:.1f}g（占{protein_ratio:.1f}%）
  - 碳水化合物：{total_carbs:.1f}g（占{carb_ratio:.1f}%）
  - 脂肪：{total_fat:.1f}g（占{fat_ratio:.1f}%）
  - 膳食纤维：{total_fiber:.1f}g

评估建议：
{chr(10).join(f'  {i+1}. {a}' for i, a in enumerate(assessment))}

参考：成人每日推荐摄入约2000kcal，蛋白质60-75g，膳食纤维25-30g。"""

    return result


@tool(description="推荐个性化运动方案。参数goal为运动目标(减脂瘦身/增肌塑形/保持健康/提升耐力/减压放松)，fitness_level为运动水平(初学者/中级/高级)，duration_minutes为每次运动时长(分钟)")
def recommend_exercise(
    goal: str = "保持健康",
    fitness_level: str = "初学者",
    duration_minutes: int = 60
) -> str:
    """推荐运动方案：优先查知识图谱，无结果回退内置方案"""
    from agent.tools.kg_tools import _kg_exercise_for_goal

    # 先从知识图谱查询适合的运动
    kg_result = _kg_exercise_for_goal(goal)
    if kg_result:
        kg_result += "\n\n以下为基于运动水平的详细方案：\n"

    # 内置运动方案矩阵（回退数据源）
    exercise_plans = {
        "减脂瘦身": {
            "初学者": [
                ("快走", 20, "中等"),
                ("开合跳", 5, "高"),
                ("深蹲", 10, "中"),
                ("平板支撑", 5, "中"),
                ("拉伸放松", 10, "低"),
            ],
            "中级": [
                ("慢跑", 15, "中高"),
                ("波比跳", 8, "高"),
                ("弓步蹲", 10, "中"),
                ("登山者", 8, "高"),
                ("卷腹", 8, "中"),
                ("拉伸放松", 10, "低"),
            ],
            "高级": [
                ("HIIT间歇跑", 20, "高"),
                ("跳绳", 10, "高"),
                ("壶铃摆荡", 10, "高"),
                ("引体向上", 8, "中高"),
                ("核心训练", 10, "中高"),
                ("拉伸放松", 5, "低"),
            ],
        },
        "增肌塑形": {
            "初学者": [
                ("俯卧撑", 10, "中"),
                ("深蹲", 10, "中"),
                ("哑铃划船", 10, "中"),
                ("平板支撑", 8, "中"),
                ("拉伸放松", 10, "低"),
            ],
            "中级": [
                ("卧推", 10, "中高"),
                ("硬拉", 10, "高"),
                ("肩推", 10, "中高"),
                ("引体向上", 8, "高"),
                ("腿举", 10, "高"),
                ("拉伸放松", 10, "低"),
            ],
            "高级": [
                ("复合训练A（深蹲+卧推）", 20, "高"),
                ("复合训练B（硬拉+划船）", 20, "高"),
                ("孤立训练（二头+三头）", 15, "中高"),
                ("核心训练", 10, "中"),
                ("拉伸放松", 5, "低"),
            ],
        },
        "保持健康": {
            "初学者": [
                ("快走", 20, "低"),
                ("太极拳/八段锦", 15, "低"),
                ("拉伸", 10, "低"),
                ("深蹲", 8, "中"),
                ("呼吸练习", 5, "低"),
            ],
            "中级": [
                ("慢跑", 15, "中"),
                ("游泳", 15, "中"),
                ("瑜伽", 15, "中"),
                ("力量训练", 10, "中"),
                ("拉伸放松", 5, "低"),
            ],
            "高级": [
                ("跑步", 20, "中高"),
                ("游泳", 15, "中高"),
                ("力量训练", 15, "高"),
                ("HIIT", 10, "高"),
                ("拉伸放松", 5, "低"),
            ],
        },
        "减压放松": {
            "初学者": [
                ("冥想", 15, "低"),
                ("瑜伽（哈他）", 20, "低"),
                ("散步", 15, "低"),
                ("呼吸练习", 5, "低"),
            ],
            "中级": [
                ("瑜伽（流瑜伽）", 20, "中"),
                ("游泳", 15, "中"),
                ("冥想", 10, "低"),
                ("拉伸放松", 15, "低"),
            ],
            "高级": [
                ("瑜伽（阿斯汤加）", 25, "中高"),
                ("跑步", 15, "中"),
                ("冥想", 10, "低"),
                ("拉伸放松", 10, "低"),
            ],
        },
    }

    # 获取方案
    goal_plans = exercise_plans.get(goal, exercise_plans["保持健康"])
    plan = goal_plans.get(fitness_level, goal_plans["初学者"])

    # 按时长调整
    total_planned = sum(d for _, d, _ in plan)
    scale = duration_minutes / total_planned if total_planned > 0 else 1

    # 预估消耗热量
    calories_per_minute = {
        "低": 4, "中": 6, "中高": 8, "高": 10
    }
    total_calories = sum(d * scale * calories_per_minute.get(i, 5) for _, d, i in plan)

    result = f"""【个性化运动方案】

目标：{goal}
运动水平：{fitness_level}
建议时长：{duration_minutes} 分钟
预估消耗：{total_calories:.0f} kcal

{kg_result or ''}训练计划：
"""
    for i, (name, dur, intensity) in enumerate(plan, 1):
        adjusted_dur = int(dur * scale)
        result += f"  {i}. {name} - {adjusted_dur}分钟（强度：{intensity}）\n"

    result += f"""
运动建议：
  - 运动前：5-10分钟热身
  - 运动中：注意补充水分，量力而行
  - 运动后：5-10分钟拉伸放松
  - 频率：每周3-5次
  - 注意：如有身体不适，请立即停止并咨询医生

注意事项：
  - 循序渐进，不要突然增加运动强度
  - 运动前后各2小时内避免大量进食
  - 保持规律运动习惯比偶尔高强度运动更有效"""

    return result


@tool(description="评估睡眠质量。参数sleep_hours为睡眠时长(小时)，sleep_quality为睡眠质量评分(1-10)")
def assess_sleep(sleep_hours: float, sleep_quality: int) -> str:
    """评估睡眠质量"""
    if sleep_hours <= 0:
        return "睡眠时长必须为正数。"
    if not 1 <= sleep_quality <= 10:
        return "睡眠质量评分范围为1-10。"

    # 时长评估
    if sleep_hours < 6:
        duration_assess = "严重不足"
        duration_advice = "严重睡眠不足！长期睡眠不足会增加心血管疾病、糖尿病、肥胖等风险。建议尽快调整作息，保证7-9小时睡眠。"
    elif sleep_hours < 7:
        duration_assess = "轻度不足"
        duration_advice = "睡眠时间略短，建议提前30分钟上床，逐步调整到7-8小时。"
    elif sleep_hours <= 9:
        duration_assess = "充足"
        duration_advice = "睡眠时长在推荐范围内，继续保持规律作息。"
    elif sleep_hours <= 10:
        duration_assess = "偏多"
        duration_advice = "睡眠时间略长，如果没有特殊原因，建议适当减少卧床时间，提高睡眠效率。"
    else:
        duration_assess = "过多"
        duration_advice = "睡眠时间过长，可能与身体某些状况有关，建议关注并适当调整。"

    # 质量评估
    if sleep_quality >= 8:
        quality_assess = "优秀"
    elif sleep_quality >= 6:
        quality_assess = "良好"
    elif sleep_quality >= 4:
        quality_assess = "一般"
    else:
        quality_assess = "较差"

    # 综合评分
    score = (min(sleep_hours / 8, 1) * 50) + (sleep_quality / 10 * 50)
    if score >= 80:
        grade = "A"
    elif score >= 60:
        grade = "B"
    elif score >= 40:
        grade = "C"
    else:
        grade = "D"

    result = f"""【睡眠质量评估】

睡眠数据：
  - 睡眠时长：{sleep_hours}小时
  - 睡眠质量：{sleep_quality}/10

评估结果：
  - 时长评估：{duration_assess}
  - 质量评估：{quality_assess}
  - 综合评分：{score:.0f}/100（等级{grade}）

改善建议：
  {duration_advice}

提高睡眠质量的建议：
  1. 保持规律的作息时间，每天同一时间入睡和起床
  2. 睡前1小时避免使用电子设备
  3. 卧室保持安静、黑暗、凉爽（18-22°C最佳）
  4. 睡前可以做一些放松活动（冥想、阅读、温水泡脚）
  5. 避免睡前摄入咖啡因和酒精
  6. 白天适度运动，但睡前3小时避免剧烈运动

注意：长期睡眠问题建议咨询专业医生。"""

    return result


# ==================== 用户管理工具（合并原 create_user + get_user_info + get_user_health_data + list_all_users） ====================

@tool(description=(
    "管理用户档案。通过 action 参数选择操作：\n"
    '- action="list": 列出所有用户，无需额外参数\n'
    '- action="get": 获取指定用户信息，需提供 user_id（如 "U001"）\n'
    '- action="health_data": 获取用户健康数据，需提供 user_id，可选 data_type（weight/blood_pressure/heart_rate/sleep/all，默认 all）\n'
    '- action="create": 创建新用户，需提供 name，可选 gender(男/女), age, height(cm), weight(kg), activity_level, health_goal\n'
    '示例：查询用户U001的血压数据 → action="health_data", user_id="U001", data_type="blood_pressure"'
))
def manage_user(
    action: str,
    user_id: str = "",
    name: str = "",
    gender: str = "男",
    age: int = 25,
    height: float = 170,
    weight: float = 65,
    activity_level: str = "轻度活动",
    health_goal: str = "保持健康",
    data_type: str = "all"
) -> str:
    """管理用户档案"""
    if action == "list":
        users = user_service.list_users()
        if not users:
            return "【用户列表】\n\n暂无用户数据，请先创建用户档案。"
        result = f"【用户列表】共 {len(users)} 个用户\n\n"
        for uid, user in users.items():
            basic = user.get("basic_info", {})
            records = user.get("health_records", {})
            latest_date = sorted(records.keys())[-1] if records else "无记录"
            result += (
                f"用户ID: {uid}\n"
                f"  姓名: {basic.get('name', '未命名')}\n"
                f"  性别: {basic.get('gender', '未知')}\n"
                f"  年龄: {basic.get('age', '未知')}岁\n"
                f"  身高: {basic.get('height', 0):.0f}cm\n"
                f"  体重: {basic.get('weight', 0):.0f}kg\n"
                f"  活动水平: {basic.get('activity_level', '未知')}\n"
                f"  健康目标: {basic.get('health_goal', '未知')}\n"
                f"  最新记录: {latest_date}\n\n"
            )
        return result

    elif action == "get":
        return user_service.get_user_summary(user_id)

    elif action == "health_data":
        user = user_service.get_user(user_id)
        if not user:
            users = user_service.list_users()
            if users:
                available_ids = ', '.join(users.keys())
                return f"未找到用户ID {user_id}。可用用户ID: {available_ids}"
            return f"未找到用户ID {user_id}。当前没有用户数据。"

        basic = user.get("basic_info", {})
        health_records = user.get("health_records", {})

        if not health_records:
            return (
                f"用户：{basic.get('name', user_id)}\n"
                f"性别：{basic.get('gender', '未知')}\n"
                f"年龄：{basic.get('age', '未知')}岁\n"
                f"身高：{basic.get('height', 0):.0f}cm\n"
                f"体重：{basic.get('weight', 0):.0f}kg\n\n"
                f"暂无健康记录数据，请先添加健康记录。"
            )

        result = (
            f"用户：{basic.get('name', user_id)}\n"
            f"性别：{basic.get('gender', '未知')}\n"
            f"年龄：{basic.get('age', '未知')}岁\n"
            f"身高：{basic.get('height', 0):.0f}cm\n"
            f"体重：{basic.get('weight', 0):.0f}kg\n\n"
            f"健康记录：\n"
        )
        for date, record in sorted(health_records.items()):
            result += f"\n{date}:\n"
            if data_type in ("all", "weight") and "weight" in record:
                result += f"  - 体重: {record['weight']:.1f} kg\n"
            if data_type in ("all", "blood_pressure") and "blood_pressure_systolic" in record:
                result += f"  - 血压: {record['blood_pressure_systolic']}/{record['blood_pressure_diastolic']} mmHg\n"
            if data_type in ("all", "heart_rate") and "heart_rate" in record:
                result += f"  - 心率: {record['heart_rate']} bpm\n"
            if data_type in ("all", "sleep") and "sleep_hours" in record:
                result += f"  - 睡眠: {record['sleep_hours']}小时 (质量{record.get('sleep_quality', '未知')}/10)\n"
            if data_type in ("all", "steps") and "steps" in record:
                result += f"  - 步数: {record['steps']:,} 步\n"
            if data_type in ("all", "calories_intake") and "calories_intake" in record:
                result += f"  - 热量摄入: {record['calories_intake']:.0f} kcal\n"
        return result

    elif action == "create":
        valid_genders = get_genders()
        if gender not in valid_genders:
            return f"无效的性别: {gender}。有效值: {', '.join(valid_genders)}"
        valid_levels = get_activity_levels()
        if activity_level not in valid_levels:
            return f"无效的活动水平: {activity_level}。有效值: {', '.join(valid_levels)}"
        try:
            result = user_service.create_user(
                name=name, gender=gender, age=age, height=height,
                weight=weight, activity_level=activity_level, health_goal=health_goal
            )
            user_id = result["user_id"]
            return (
                f"用户创建成功！\n\n"
                f"用户ID: {user_id}\n"
                f"姓名: {name}\n"
                f"性别: {gender}\n"
                f"年龄: {age}岁\n"
                f"身高: {height:.0f}cm\n"
                f"体重: {weight:.0f}kg\n"
                f"活动水平: {activity_level}\n"
                f"健康目标: {health_goal}\n\n"
                f"您可以使用用户ID {user_id} 来管理健康数据。"
            )
        except Exception as e:
            logger.error(f"创建用户失败: {e}")
            return f"创建用户失败: {str(e)}"

    else:
        return f"不支持的操作: {action}。支持的操作：list, get, health_data, create"


# ==================== 健康记录工具 ====================

@tool(description="添加用户健康记录。参数user_id为用户ID，date为日期(YYYY-MM-DD)，weight为体重(kg)，blood_pressure_systolic为收缩压，blood_pressure_diastolic为舒张压，heart_rate为心率(bpm)，sleep_hours为睡眠时长(小时)，sleep_quality为睡眠质量(1-10)，steps为步数，calories_intake为热量摄入(kcal)")
def add_health_record(
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
) -> str:
    """添加健康记录"""
    if len(date) != 10 or date[4] != '-' or date[7] != '-':
        return "日期格式错误，请使用YYYY-MM-DD格式（如2024-03-15）"

    user = user_service.get_user(user_id)
    if not user:
        return f"用户不存在: {user_id}"

    success = user_service.add_health_record(
        user_id=user_id,
        date=date,
        weight=weight,
        blood_pressure_systolic=blood_pressure_systolic,
        blood_pressure_diastolic=blood_pressure_diastolic,
        heart_rate=heart_rate,
        sleep_hours=sleep_hours,
        sleep_quality=sleep_quality,
        steps=steps,
        calories_intake=calories_intake
    )

    if success:
        record_items = []
        if weight is not None:
            record_items.append(f"  - 体重: {weight:.1f} kg")
        if blood_pressure_systolic is not None:
            record_items.append(f"  - 血压: {blood_pressure_systolic}/{blood_pressure_diastolic} mmHg")
        if heart_rate is not None:
            record_items.append(f"  - 心率: {heart_rate} bpm")
        if sleep_hours is not None:
            record_items.append(f"  - 睡眠: {sleep_hours}小时 (质量{sleep_quality}/10)")
        if steps is not None:
            record_items.append(f"  - 步数: {steps:,} 步")
        if calories_intake is not None:
            record_items.append(f"  - 热量摄入: {calories_intake:.0f} kcal")

        return (
            f"健康记录添加成功！\n\n"
            f"用户ID: {user_id}\n"
            f"用户姓名: {user.get('basic_info', {}).get('name', '未命名')}\n"
            f"日期: {date}\n\n"
            f"记录数据：\n"
            + "\n".join(record_items)
        )
    return f"添加健康记录失败: {user_id}"


# ==================== 健康报告查询工具（合并原 list + get + search） ====================

@tool(description=(
    "查询健康知识报告。通过 action 参数选择操作：\n"
    '- action="list": 列出所有报告，无需额外参数\n'
    '- action="get": 获取指定报告详情，需提供 report_id（如 R001）\n'
    '- action="search": 按关键词搜索报告，需提供 keyword\n'
    '示例：搜索高血压相关报告 → action="search", keyword="高血压"'
))
def query_health_reports(action: str, report_id: str = "", keyword: str = "") -> str:
    """查询健康知识报告"""
    if action == "list":
        return health_report_service.list_reports()
    elif action == "get":
        return health_report_service.get_report(report_id)
    elif action == "search":
        return health_report_service.search_reports(keyword)
    else:
        return f"不支持的操作: {action}。支持的操作：list, get, search"
