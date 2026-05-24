"""
知识图谱工具模块 - 提供图谱问答、实体关联查询、NER 等能力
"""
from typing import Optional
from langchain_core.tools import tool
from project.logger_handler import logger

from agent.knowledge.health_kg import health_kg
from agent.knowledge.kg_qa import kg_qa
from agent.knowledge.ner import health_ner


# ==================== 内部辅助函数（不暴露给 LLM） ====================

def _get_kg_schema() -> str:
    """获取知识图谱架构统计（供内部调用）"""
    schema = health_kg.get_schema()
    entity_types = ', '.join(f'{k}: {v}个' for k, v in schema['entity_types'].items())
    relation_types = ', '.join(f'{k}: {v}条' for k, v in schema['relation_types'].items())
    return (
        f"健康知识图谱统计：节点总数 {schema['nodes']}，关系总数 {schema['edges']}\n"
        f"实体类型：{entity_types}\n关系类型：{relation_types}"
    )


def _recognize_entities(text: str) -> str:
    """识别文本中的健康实体（供内部调用）"""
    results = health_ner.recognize(text)
    entities = [r for r in results if r["entity_type"] > 0]
    if entities:
        entity_list = [f"{e['entity_name']} ({e['entity_type_name']})" for e in entities]
        return f"识别到的健康实体：{', '.join(entity_list)}"
    return "文本中未识别到健康实体"


def _kg_food_nutrients(food: str) -> Optional[dict]:
    """查询食物营养成分（供内部调用，analyze_nutrition 使用）

    返回结构化 dict（含 calories/protein/carbs/fat/fiber 等数值字段），
    或 None 表示图谱中无此食物数据。
    """
    nutrients_contains = health_kg.find_entities_by_relation(food, "含有", "out")
    nutrients_rich = health_kg.find_entities_by_relation(food, "富含", "out")
    all_nutrients = list(set(nutrients_contains + nutrients_rich))
    attrs = health_kg.get_entity_attributes(food)

    # 无任何营养数据
    if not all_nutrients and not attrs:
        return None

    result: dict = {"food": food, "nutrients": all_nutrients}

    # 从属性中提取数值型营养字段
    for key in ("calories", "protein", "carbs", "fat", "fiber"):
        if key in attrs:
            try:
                result[key] = float(attrs[key])
            except (ValueError, TypeError):
                pass

    return result


def _kg_exercise_for_goal(goal: str) -> str:
    """查询适合目标的运动（供内部调用，recommend_exercise 使用）"""
    exercises = health_kg.find_entities_by_relation(goal, "适合", "in")
    if exercises:
        return f"适合 '{goal}' 的运动包括：{', '.join(exercises)}"
    return ""


# ==================== 图谱问答工具 ====================

@tool(description='用自然语言提问关于健康、疾病、营养、运动的问题，返回基于知识图谱的回答。参数query为自然语言问题')
def kg_query(query: str) -> str:
    """知识图谱自然语言问答"""
    result = kg_qa.answer(query)
    return result.get("answer", "暂未找到答案")


# ==================== 实体关联查询工具（合并原疾病/营养/路径工具） ====================

@tool(description=(
    "查询健康实体之间的关联信息。提供实体名称和关系类型，返回相关实体列表。\n"
    "常用关系类型：\n"
    '- "symptoms": 查询疾病的症状，如 entity="高血压"\n'
    '- "treatment": 查询疾病的治疗方法\n'
    '- "risk_factors": 查询疾病的风险因素\n'
    '- "foods": 查询富含某营养素的食物，如 entity="蛋白质"\n'
    '- "nutrients": 查询食物含有的营养成分，如 entity="鸡蛋"\n'
    '- "path": 查询两个实体之间的关系路径，需提供 entity2\n'
    '示例：查询糖尿病的症状 → entity="糖尿病", relation="symptoms"\n'
    '示例：查询富含维生素C的食物 → entity="维生素C", relation="foods"'
))
def kg_entity_lookup(entity: str, relation: str = "", entity2: str = "") -> str:
    """查询健康实体关联信息"""
    if not relation and not entity2:
        return "请提供 relation 参数（如 symptoms/treatment/risk_factors/foods/nutrients）或 entity2 参数（查询关系路径）"

    # 关系路径查询
    if entity2:
        paths = health_kg.find_path(entity, entity2, max_depth=3)
        if paths:
            path_strs = []
            for path in paths[:3]:
                path_str = " -> ".join(str(p) for p in path[:5])
                path_strs.append(path_str)
            return f"'{entity}' 与 '{entity2}' 的关系路径：\n" + "\n".join(path_strs)
        return f"'{entity}' 和 '{entity2}' 暂无直接关联"

    # 关系映射：用户友好的名称 → 图谱内部关系名
    relation_map = {
        "symptoms": ("具有症状", "out", "常见症状"),
        "treatment": ("治疗方式", "out", "治疗方法"),
        "risk_factors": ("风险因素", "out", "风险因素"),
        "foods": ("富含", "in", "富含的食物"),
        "nutrients_contains": ("含有", "out", "含有的营养成分"),
        "nutrients_rich": ("富含", "out", "富含的营养成分"),
    }

    # 特殊处理：foods 需要双向查询
    if relation == "foods":
        foods_rich = health_kg.find_entities_by_relation(entity, "富含", "in")
        foods_contains = health_kg.find_entities_by_relation(entity, "含有", "in")
        all_foods = list(set(foods_rich + foods_contains))
        if all_foods:
            parts = []
            if foods_rich:
                parts.append(f"富含 '{entity}' 的食物：{', '.join(foods_rich)}")
            if foods_contains:
                parts.append(f"含 '{entity}' 的食物：{', '.join(foods_contains)}")
            return "; ".join(parts)
        return f"富含 '{entity}' 的食物信息暂未收录"

    # 特殊处理：nutrients 需要双向查询
    if relation == "nutrients":
        nutrients_contains = health_kg.find_entities_by_relation(entity, "含有", "out")
        nutrients_rich = health_kg.find_entities_by_relation(entity, "富含", "out")
        all_nutrients = list(set(nutrients_contains + nutrients_rich))
        attrs = health_kg.get_entity_attributes(entity)
        result_parts = []
        if all_nutrients:
            result_parts.append(f"'{entity}' 含有营养素：{', '.join(all_nutrients)}")
        if attrs:
            attr_str = ", ".join(f"{k}: {v}" for k, v in attrs.items())
            result_parts.append(f"营养成分数据：{attr_str}")
        if result_parts:
            return "; ".join(result_parts)
        return f"'{entity}' 的营养成分暂未收录"

    # 通用关系查询
    mapped = relation_map.get(relation)
    if mapped:
        graph_relation, direction, label = mapped
        results = health_kg.find_entities_by_relation(entity, graph_relation, direction)
        if results:
            return f"'{entity}' 的{label}包括：{', '.join(results)}"
        return f"'{entity}' 的{label}暂未收录"

    # 未知关系类型，直接尝试用原始关系名查询
    results = health_kg.find_entities_by_relation(entity, relation, "out")
    if results:
        return f"'{entity}' 的{relation}包括：{', '.join(results)}"
    return f"未找到 '{entity}' 的 '{relation}' 关联信息。支持的关系类型：symptoms, treatment, risk_factors, foods, nutrients, path"
