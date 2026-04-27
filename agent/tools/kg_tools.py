
from langchain_core.tools import tool
from project.logger_handler import logger

from agent.knowledge.health_kg import health_kg
from agent.knowledge.kg_qa import kg_qa
from agent.knowledge.ner import health_ner


@tool(description='从健康知识图谱中查询信息。参数query为查询问题')
def kg_query(query: str) -> str:
    """知识图谱问答"""
    result = kg_qa.answer(query)
    return result.get("answer", "暂未找到答案")


@tool(description='查询疾病的症状。参数disease为疾病名称')
def kg_disease_symptoms(disease: str) -> str:
    """查询疾病症状"""
    symptoms = health_kg.find_entities_by_relation(disease, "具有症状", "out")
    if symptoms:
        return f"'{disease}' 的常见症状包括：{', '.join(symptoms)}"
    return f"'{disease}' 的症状信息暂未收录"


@tool(description='查询疾病的治疗方法。参数disease为疾病名称')
def kg_disease_treatment(disease: str) -> str:
    """查询疾病治疗方法"""
    treatments = health_kg.find_entities_by_relation(disease, "治疗方式", "out")
    if treatments:
        return f"'{disease}' 的治疗方法包括：{', '.join(treatments)}"
    return f"'{disease}' 的治疗信息暂未收录"


@tool(description='查询疾病的风险因素。参数disease为疾病名称')
def kg_disease_risk_factors(disease: str) -> str:
    """查询疾病风险因素"""
    risks = health_kg.find_entities_by_relation(disease, "风险因素", "out")
    if risks:
        return f"'{disease}' 的风险因素包括：{', '.join(risks)}"
    return f"'{disease}' 的风险因素信息暂未收录"


@tool(description='查询食物的营养成分。参数food为食物名称')
def kg_food_nutrients(food: str) -> str:
    """查询食物营养成分"""
    nutrients_contains = health_kg.find_entities_by_relation(food, "含有", "out")
    nutrients_rich = health_kg.find_entities_by_relation(food, "富含", "out")

    all_nutrients = list(set(nutrients_contains + nutrients_rich))

    attrs = health_kg.get_entity_attributes(food)

    result_parts = []
    if all_nutrients:
        result_parts.append(f"'{food}' 含有营养素：{', '.join(all_nutrients)}")
    if attrs:
        attr_str = ", ".join(f"{k}: {v}" for k, v in attrs.items())
        result_parts.append(f"营养成分数据：{attr_str}")

    if result_parts:
        return "; ".join(result_parts)
    return f"'{food}' 的营养成分暂未收录"


@tool(description='查询富含某营养素的食物。参数nutrient为营养素名称')
def kg_nutrient_foods(nutrient: str) -> str:
    """查询富含营养素的食物"""
    foods_rich = health_kg.find_entities_by_relation(nutrient, "富含", "in")
    foods_contains = health_kg.find_entities_by_relation(nutrient, "含有", "in")

    all_foods = list(set(foods_rich + foods_contains))

    if all_foods:
        rich_str = f"富含 '{nutrient}' 的食物：{', '.join(foods_rich)}" if foods_rich else ""
        contains_str = f"含 '{nutrient}' 的食物：{', '.join(foods_contains)}" if foods_contains else ""
        return (rich_str + "; " + contains_str).strip()
    return f"富含 '{nutrient}' 的食物信息暂未收录"


@tool(description='查询适合某健康目标的运动。参数goal为健康目标')
def kg_exercise_for_goal(goal: str) -> str:
    """查询适合目标的运动"""
    exercises = health_kg.find_entities_by_relation(goal, "适合", "in")
    if exercises:
        return f"适合 '{goal}' 的运动包括：{', '.join(exercises)}"
    return f"适合 '{goal}' 的运动信息暂未收录"


@tool(description='从文本中识别健康实体。参数text为待识别的文本')
def kg_recognize_entities(text: str) -> str:
    """识别文本中的健康实体"""
    results = health_ner.recognize(text)
    entities = [r for r in results if r["entity_type"] > 0]

    if entities:
        entity_list = [f"{e['entity_name']} ({e['entity_type_name']})" for e in entities]
        return f"识别到的健康实体：{', '.join(entity_list)}"
    return "文本中未识别到健康实体"


@tool(description='获取健康知识图谱的架构统计信息。无需参数')
def kg_schema() -> str:
    """获取知识图谱架构"""
    schema = health_kg.get_schema()
    entity_types = ', '.join(f'{k}: {v}个' for k, v in schema['entity_types'].items())
    relation_types = ', '.join(f'{k}: {v}条' for k, v in schema['relation_types'].items())
    return f"健康知识图谱统计：节点总数 {schema['nodes']}，关系总数 {schema['edges']}\n实体类型：{entity_types}\n关系类型：{relation_types}"


@tool(description='查询两个健康实体之间的关系。参数entity1为第一个实体，entity2为第二个实体')
def kg_entity_relation(entity1: str, entity2: str) -> str:
    paths = health_kg.find_path(entity1, entity2, max_depth=3)

    if paths:
        path_strs = []
        for path in paths[:3]:
            path_str = " -> ".join(str(p) for p in path[:5])
            path_strs.append(path_str)
        return f"'{entity1}' 与 '{entity2}' 的关系路径：\n" + "\n".join(path_strs)
    return f"'{entity1}' 和 '{entity2}' 暂无直接关联"