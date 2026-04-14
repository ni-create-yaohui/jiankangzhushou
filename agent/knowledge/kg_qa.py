"""
健康知识图谱问答系统
基于规则模式匹配 + 图谱查询推理
"""
import re
from typing import Dict, List, Optional, Tuple
from project.logger_handler import logger

from agent.knowledge.health_kg import health_kg, HealthKG
from agent.knowledge.entity_types import EntityType, ENTITY_TYPE_DESC, ENTITY_LABELS
from agent.knowledge.relation_types import RELATION_LABELS


class KGQA:
    """
    知识图谱问答系统 - 基于规则匹配和图谱推理
    1. 问题模式识别（正则匹配）
    2. 实体识别（NER）
    3. 关系提取
    4. 图谱查询推理
    5. 答案生成
    """

    def __init__(self, kg: HealthKG = None):
        self.kg = kg or health_kg
        self._init_question_patterns()
        logger.info("[KGQA] 知识图谱问答系统初始化完成")

    def _init_question_patterns(self):
        """初始化问题模式"""
        # 问题类型 -> (关键词模式列表, 处理函数名)
        self.question_patterns = {
            # 疾病相关问答
            "disease_symptom": [
                [r"([\u4e00-\u9fa5]+)有什么症状", r"([\u4e00-\u9fa5]+)的症状", r"([\u4e00-\u9fa5]+)有哪些症状"],
                "_query_disease_symptom"
            ],
            "symptom_disease": [
                [r"([\u4e00-\u9fa5]+)是什么病", r"([\u4e00-\u9fa5]+)可能是什么疾病", r"([\u4e00-\u9fa5]+)对应的疾病"],
                "_query_symptom_disease"
            ],
            "disease_treatment": [
                [r"([\u4e00-\u9fa5]+)怎么治疗", r"([\u4e00-\u9fa5]+)治疗方法", r"([\u4e00-\u9fa5]+)怎么治"],
                "_query_disease_treatment"
            ],
            "disease_risk": [
                [r"([\u4e00-\u9fa5]+)的风险因素", r"([\u4e00-\u9fa5]+)由什么引起", r"([\u4e00-\u9fa5]+)的原因"],
                "_query_disease_risk"
            ],
            "disease_prevention": [
                [r"如何预防([\u4e00-\u9fa5]+)", r"([\u4e00-\u9fa5]+)如何预防", r"预防([\u4e00-\u9fa5]+)的方法"],
                "_query_disease_prevention"
            ],

            # 药物相关问答
            "drug_disease": [
                [r"([\u4e00-\u9fa5]+)治什么病", r"([\u4e00-\u9fa5]+)用于治疗", r"([\u4e00-\u9fa5]+)的用途"],
                "_query_drug_disease"
            ],
            "disease_drug": [
                [r"([\u4e00-\u9fa5]+)吃什么药", r"([\u4e00-\u9fa5]+)用什么药", r"治疗([\u4e00-\u9fa5]+)的药"],
                "_query_disease_drug"
            ],

            # 食物营养相关问答
            "food_nutrient": [
                [r"([\u4e00-\u9fa5]+)有什么营养", r"([\u4e00-\u9fa5]+)的营养成分", r"([\u4e00-\u9fa5]+)含有哪些营养"],
                "_query_food_nutrient"
            ],
            "nutrient_food": [
                [r"([\u4e00-\u9fa5]+)富含的食物", r"含([\u4e00-\u9fa5]+)的食物", r"([\u4e00-\u9fa5]+)在哪些食物中"],
                "_query_nutrient_food"
            ],
            "food_disease_good": [
                [r"([\u4e00-\u9fa5]+)吃什么好", r"([\u4e00-\u9fa5]+)适合吃什么", r"对([\u4e00-\u9fa5]+)有益的食物"],
                "_query_food_good_for_disease"
            ],
            "food_disease_bad": [
                [r"([\u4e00-\u9fa5]+)不能吃什么", r"([\u4e00-\u9fa5]+)忌口", r"([\u4e00-\u9fa5]+)不宜吃什么"],
                "_query_food_bad_for_disease"
            ],

            # 运动相关问答
            "exercise_goal": [
                [r"([\u4e00-\u9fa5]+)做什么运动", r"([\u4e00-\u9fa5]+)适合的运动", r"想([\u4e00-\u9fa5]+)怎么运动"],
                "_query_exercise_for_goal"
            ],
            "exercise_disease": [
                [r"([\u4e00-\u9fa5]+)适合运动吗", r"([\u4e00-\u9fa5]+)能做什么运动", r"([\u4e00-\u9fa5]+)患者运动"],
                "_query_exercise_for_disease"
            ],

            # 实体信息问答
            "entity_info": [
                [r"([\u4e00-\u9fa5]+)是什么", r"([\u4e00-\u9fa5]+)介绍", r"([\u4e00-\u9fa5]+)的信息"],
                "_query_entity_info"
            ],
            "entity_relation": [
                [r"([\u4e00-\u9fa5]+)和([\u4e00-\u9fa5]+)的关系", r"([\u4e00-\u9fa5]+)与([\u4e00-\u9fa5]+)有什么关系"],
                "_query_entity_relation"
            ],
        }

    def answer(self, question: str) -> Dict:
        """
        回答问题

        Args:
            question: 用户问题

        Returns:
            答案字典 {answer: str, relations: List, confidence: float}
        """
        logger.info(f"[KGQA] 收到问题: {question}")

        # 识别问题类型
        q_type, entities, match_pos = self._identify_question_type(question)

        if not q_type:
            # 无法识别问题类型，尝试通用实体查询
            return self._generic_query(question)

        # 获取处理函数
        handler_name = self.question_patterns[q_type][1]
        handler = getattr(self, handler_name, None)

        if handler:
            result = handler(entities, question)
            logger.info(f"[KGQA] 问题类型: {q_type}, 答案: {result.get('answer', '无')}")
            return result

        return {"answer": "暂未找到答案", "relations": [], "confidence": 0}

    def _identify_question_type(self, question: str) -> Tuple[Optional[str], List[str], int]:
        """
        识别问题类型

        Returns:
            (问题类型, 实体列表, 匹配位置)
        """
        for q_type, (patterns, _) in self.question_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, question)
                if match:
                    entities = list(match.groups())
                    return q_type, entities, match.start()
        return None, [], -1

    def _extract_entity(self, text: str) -> Optional[str]:
        """从文本中提取实体"""
        # 直接匹配
        entity = self.kg.match_entity(text)
        if entity:
            return entity

        # 分词后逐个匹配
        words = text.split()
        for word in words:
            entity = self.kg.match_entity(word)
            if entity:
                return entity

        # 尝试提取中文实体
        chinese_pattern = re.findall(r'[\u4e00-\u9fa5]+', text)
        for word in chinese_pattern:
            entity = self.kg.match_entity(word)
            if entity:
                return entity

        return None

    def _build_result(self, answer: str, relations: List[Dict], confidence: float = 1.0) -> Dict:
        """构建结果字典"""
        return {
            "answer": answer,
            "relations": relations,
            "confidence": confidence
        }

    # ========== 疾病相关问答 ==========

    def _query_disease_symptom(self, entities: List[str], question: str) -> Dict:
        """查询疾病症状"""
        disease_name = entities[0] if entities else self._extract_entity(question)
        if not disease_name:
            return self._build_result("请提供疾病名称", [])

        # 匹配实体
        disease = self.kg.match_entity(disease_name)
        if not disease:
            return self._build_result(f"未找到疾病 '{disease_name}' 的信息", [])

        # 查询症状关系
        symptoms = self.kg.find_entities_by_relation(disease, "具有症状", "out")

        if not symptoms:
            return self._build_result(f"'{disease}' 的症状信息暂未收录", [])

        relations = [
            {"entity1": disease, "relation": "具有症状", "entity2": s}
            for s in symptoms
        ]

        answer = f"'{disease}' 的常见症状包括：{', '.join(symptoms)}"
        return self._build_result(answer, relations)

    def _query_symptom_disease(self, entities: List[str], question: str) -> Dict:
        """查询症状对应的疾病"""
        symptom_name = entities[0] if entities else self._extract_entity(question)
        if not symptom_name:
            return self._build_result("请提供症状名称", [])

        symptom = self.kg.match_entity(symptom_name)
        if not symptom:
            return self._build_result(f"未找到症状 '{symptom_name}' 的信息", [])

        # 反向查询：症状对应的疾病
        diseases = self.kg.find_entities_by_relation(symptom, "具有症状", "in")

        if not diseases:
            return self._build_result(f"'{symptom}' 对应的疾病信息暂未收录", [])

        relations = [
            {"entity1": d, "relation": "具有症状", "entity2": symptom}
            for d in diseases
        ]

        answer = f"'{symptom}' 可能与以下疾病相关：{', '.join(diseases)}"
        return self._build_result(answer, relations)

    def _query_disease_treatment(self, entities: List[str], question: str) -> Dict:
        """查询疾病治疗方法"""
        disease_name = entities[0] if entities else self._extract_entity(question)
        if not disease_name:
            return self._build_result("请提供疾病名称", [])

        disease = self.kg.match_entity(disease_name)
        if not disease:
            return self._build_result(f"未找到疾病 '{disease_name}' 的信息", [])

        treatments = self.kg.find_entities_by_relation(disease, "治疗方式", "out")

        if not treatments:
            return self._build_result(f"'{disease}' 的治疗信息暂未收录", [])

        relations = [
            {"entity1": disease, "relation": "治疗方式", "entity2": t}
            for t in treatments
        ]

        answer = f"'{disease}' 的治疗方法包括：{', '.join(treatments)}"
        return self._build_result(answer, relations)

    def _query_disease_risk(self, entities: List[str], question: str) -> Dict:
        """查询疾病风险因素"""
        disease_name = entities[0] if entities else self._extract_entity(question)
        if not disease_name:
            return self._build_result("请提供疾病名称", [])

        disease = self.kg.match_entity(disease_name)
        if not disease:
            return self._build_result(f"未找到疾病 '{disease_name}' 的信息", [])

        risks = self.kg.find_entities_by_relation(disease, "风险因素", "out")

        if not risks:
            return self._build_result(f"'{disease}' 的风险因素信息暂未收录", [])

        relations = [
            {"entity1": disease, "relation": "风险因素", "entity2": r}
            for r in risks
        ]

        answer = f"'{disease}' 的风险因素包括：{', '.join(risks)}"
        return self._build_result(answer, relations)

    def _query_disease_prevention(self, entities: List[str], question: str) -> Dict:
        """查询疾病预防方法"""
        disease_name = entities[0] if entities else self._extract_entity(question)
        if not disease_name:
            return self._build_result("请提供疾病名称", [])

        disease = self.kg.match_entity(disease_name)
        if not disease:
            return self._build_result(f"未找到疾病 '{disease_name}' 的信息", [])

        # 查询预防关系（反向：什么可以预防该疾病）
        preventions = self.kg.find_entities_by_relation(disease, "预防", "in")

        # 查询风险因素，给出预防建议
        risks = self.kg.find_entities_by_relation(disease, "风险因素", "out")

        relations = []
        preventions_list = []

        for p in preventions:
            relations.append({"entity1": p, "relation": "预防", "entity2": disease})
            preventions_list.append(p)

        if risks:
            for r in risks:
                relations.append({"entity1": disease, "relation": "风险因素", "entity2": r})
            preventions_list.append(f"避免风险因素：{', '.join(risks)}")

        if not preventions_list:
            return self._build_result(f"'{disease}' 的预防方法暂未收录", [])

        answer = f"预防 '{disease}' 的方法：{'; '.join(preventions_list)}"
        return self._build_result(answer, relations)


    def _query_drug_disease(self, entities: List[str], question: str) -> Dict:
        """查询药物治疗的疾病"""
        drug_name = entities[0] if entities else self._extract_entity(question)
        if not drug_name:
            return self._build_result("请提供药物名称", [])

        drug = self.kg.match_entity(drug_name)
        if not drug:
            return self._build_result(f"未找到药物 '{drug_name}' 的信息", [])

        diseases = self.kg.find_entities_by_relation(drug, "药物用途", "out")

        if not diseases:
            return self._build_result(f"'{drug}' 的用途信息暂未收录", [])

        relations = [
            {"entity1": drug, "relation": "药物用途", "entity2": d}
            for d in diseases
        ]

        answer = f"'{drug}' 用于治疗：{', '.join(diseases)}"
        return self._build_result(answer, relations)

    def _query_disease_drug(self, entities: List[str], question: str) -> Dict:
        """查询疾病用药"""
        disease_name = entities[0] if entities else self._extract_entity(question)
        if not disease_name:
            return self._build_result("请提供疾病名称", [])

        disease = self.kg.match_entity(disease_name)
        if not disease:
            return self._build_result(f"未找到疾病 '{disease_name}' 的信息", [])

        # 查询治疗方式，筛选药物类型
        treatments = self.kg.find_entities_by_relation(disease, "治疗方式", "out")
        drugs = [t for t in treatments if self.kg.get_entity_type(t) == EntityType.DRUG.value]

        # 反向查询药物用途
        drugs_from_relation = self.kg.find_entities_by_relation(disease, "药物用途", "in")
        drugs.extend(drugs_from_relation)

        if not drugs:
            return self._build_result(f"'{disease}' 的用药信息暂未收录", [])

        relations = [
            {"entity1": d, "relation": "药物用途", "entity2": disease}
            for d in drugs
        ]

        answer = f"'{disease}' 常用药物：{', '.join(drugs)}"
        return self._build_result(answer, relations)

    # ========== 食物营养相关问答 ==========

    def _query_food_nutrient(self, entities: List[str], question: str) -> Dict:
        """查询食物营养成分"""
        food_name = entities[0] if entities else self._extract_entity(question)
        if not food_name:
            return self._build_result("请提供食物名称", [])

        food = self.kg.match_entity(food_name)
        if not food:
            return self._build_result(f"未找到食物 '{food_name}' 的信息", [])

        # 查询含有和富含关系
        nutrients_contains = self.kg.find_entities_by_relation(food, "含有", "out")
        nutrients_rich = self.kg.find_entities_by_relation(food, "富含", "out")

        all_nutrients = list(set(nutrients_contains + nutrients_rich))

        relations = []
        for n in nutrients_contains:
            relations.append({"entity1": food, "relation": "含有", "entity2": n})
        for n in nutrients_rich:
            relations.append({"entity1": food, "relation": "富含", "entity2": n})

        if not all_nutrients:
            # 尝试获取食物属性
            attrs = self.kg.get_entity_attributes(food)
            if attrs:
                attr_info = ", ".join(f"{k}: {v}" for k, v in attrs.items())
                return self._build_result(f"'{food}' 的营养成分：{attr_info}", [])

            return self._build_result(f"'{food}' 的营养成分暂未收录", [])

        answer = f"'{food}' 含有营养素：{', '.join(all_nutrients)}"
        return self._build_result(answer, relations)

    def _query_nutrient_food(self, entities: List[str], question: str) -> Dict:
        """查询富含某营养素的食物"""
        nutrient_name = entities[0] if entities else self._extract_entity(question)
        if not nutrient_name:
            return self._build_result("请提供营养素名称", [])

        nutrient = self.kg.match_entity(nutrient_name)
        if not nutrient:
            return self._build_result(f"未找到营养素 '{nutrient_name}' 的信息", [])

        foods_contains = self.kg.find_entities_by_relation(nutrient, "含有", "in")
        foods_rich = self.kg.find_entities_by_relation(nutrient, "富含", "in")

        all_foods = list(set(foods_contains + foods_rich))

        relations = []
        for f in foods_rich:
            relations.append({"entity1": f, "relation": "富含", "entity2": nutrient})
        for f in foods_contains:
            relations.append({"entity1": f, "relation": "含有", "entity2": nutrient})

        if not all_foods:
            return self._build_result(f"富含 '{nutrient}' 的食物信息暂未收录", [])

        rich_foods_str = f"富含 '{nutrient}' 的食物：{', '.join(foods_rich)}" if foods_rich else ""
        contains_foods_str = f"含 '{nutrient}' 的食物：{', '.join(foods_contains)}" if foods_contains else ""

        answer = (rich_foods_str + "; " + contains_foods_str).strip()
        return self._build_result(answer, relations)

    def _query_food_good_for_disease(self, entities: List[str], question: str) -> Dict:
        """查询对疾病有益的食物"""
        disease_name = entities[0] if entities else self._extract_entity(question)
        if not disease_name:
            return self._build_result("请提供疾病名称", [])

        disease = self.kg.match_entity(disease_name)
        if not disease:
            return self._build_result(f"未找到疾病 '{disease_name}' 的信息", [])

        foods = self.kg.find_entities_by_relation(disease, "有益于", "in")
        diet_types = self.kg.find_entities_by_relation(disease, "有益于", "in")

        relations = [
            {"entity1": f, "relation": "有益于", "entity2": disease}
            for f in foods + diet_types
        ]

        if not foods and not diet_types:
            return self._build_result(f"对 '{disease}' 有益的食物信息暂未收录", [])

        result_list = foods + diet_types
        answer = f"对 '{disease}' 有益：{', '.join(result_list)}"
        return self._build_result(answer, relations)

    def _query_food_bad_for_disease(self, entities: List[str], question: str) -> Dict:
        """查询对疾病不利的食物"""
        disease_name = entities[0] if entities else self._extract_entity(question)
        if not disease_name:
            return self._build_result("请提供疾病名称", [])

        disease = self.kg.match_entity(disease_name)
        if not disease:
            return self._build_result(f"未找到疾病 '{disease_name}' 的信息", [])

        bad_foods = self.kg.find_entities_by_relation(disease, "不利于", "in")
        risks = self.kg.find_entities_by_relation(disease, "风险因素", "out")

        relations = [
            {"entity1": f, "relation": "不利于", "entity2": disease}
            for f in bad_foods
        ]
        for r in risks:
            relations.append({"entity1": disease, "relation": "风险因素", "entity2": r})

        if not bad_foods and not risks:
            return self._build_result(f"'{disease}' 的忌口信息暂未收录", [])

        result_list = bad_foods + risks
        answer = f"'{disease}' 应避免：{', '.join(result_list)}"
        return self._build_result(answer, relations)


    def _query_exercise_for_goal(self, entities: List[str], question: str) -> Dict:
        """查询适合某目标的运动"""
        goal_name = entities[0] if entities else self._extract_entity(question)
        if not goal_name:
            return self._build_result("请提供健康目标", [])

        goal = self.kg.match_entity(goal_name)
        if not goal:
            return self._build_result(f"未找到健康目标 '{goal_name}' 的信息", [])

        exercises = self.kg.find_entities_by_relation(goal, "适合", "in")

        relations = [
            {"entity1": e, "relation": "适合", "entity2": goal}
            for e in exercises
        ]

        if not exercises:
            return self._build_result(f"适合 '{goal}' 的运动信息暂未收录", [])

        answer = f"适合 '{goal}' 的运动：{', '.join(exercises)}"
        return self._build_result(answer, relations)

    def _query_exercise_for_disease(self, entities: List[str], question: str) -> Dict:
        """查询适合某疾病的运动"""
        disease_name = entities[0] if entities else self._extract_entity(question)
        if not disease_name:
            return self._build_result("请提供疾病名称", [])

        disease = self.kg.match_entity(disease_name)
        if not disease:
            return self._build_result(f"未找到疾病 '{disease_name}' 的信息", [])

        # 查询运动对疾病的益处
        exercises = self.kg.find_entities_by_relation(disease, "有益于", "in")

        # 查询运动改善疾病
        improves = self.kg.find_entities_by_relation(disease, "帮助改善", "in")

        all_exercises = list(set(exercises + improves))

        relations = [
            {"entity1": e, "relation": "有益于/帮助改善", "entity2": disease}
            for e in all_exercises
        ]

        if not all_exercises:
            return self._build_result(f"'{disease}' 患者的运动建议暂未收录，建议咨询医生", [])

        answer = f"'{disease}' 患者可尝试的运动：{', '.join(all_exercises)}（建议咨询医生后进行）"
        return self._build_result(answer, relations)


    def _query_entity_info(self, entities: List[str], question: str) -> Dict:
        """查询实体基本信息"""
        entity_name = entities[0] if entities else self._extract_entity(question)
        if not entity_name:
            return self._build_result("请提供实体名称", [])

        entity = self.kg.match_entity(entity_name)
        if not entity:
            return self._build_result(f"未找到 '{entity_name}' 的信息", [])

        # 获取实体信息
        node = self.kg.get_entity(entity)
        entity_type_desc = self.kg.get_entity_type_desc(entity)

        # 获取所有关系
        relations = self.kg.get_entity_relations(entity)

        info_parts = []
        info_parts.append(f"'{entity}' ({entity_type_desc.get('name', '未知类型')})")

        attrs = self.kg.get_entity_attributes(entity)
        if attrs:
            info_parts.append("属性：" + ", ".join(f"{k}: {v}" for k, v in attrs.items()))

        if relations:
            rel_strs = [f"{r['entity1']} - {r['relation']} -> {r['entity2']}" for r in relations[:6]]
            info_parts.append("关系：" + "; ".join(rel_strs))

        answer = "\n".join(info_parts)
        return self._build_result(answer, relations)

    def _query_entity_relation(self, entities: List[str], question: str) -> Dict:
        """查询两个实体之间的关系"""
        if len(entities) < 2:
            return self._build_result("请提供两个实体名称", [])

        entity1 = self.kg.match_entity(entities[0])
        entity2 = self.kg.match_entity(entities[1])

        if not entity1 or not entity2:
            return self._build_result(f"未找到实体 '{entities[0]}' 或 '{entities[1]}'", [])

        # 查找路径
        paths = self.kg.find_path(entity1, entity2, max_depth=3)

        if not paths:
            return self._build_result(f"'{entity1}' 和 '{entity2}' 暂无直接关联", [])

        relations = []
        for path in paths[:3]:  # 只返回前3条路径
            for i in range(0, len(path) - 1, 2):
                relations.append({
                    "entity1": path[i],
                    "relation": path[i + 1] if i + 1 < len(path) else "",
                    "entity2": path[i + 2] if i + 2 < len(path) else ""
                })

        path_str = " -> ".join(path[:5] for path in paths[0])
        answer = f"'{entity1}' 与 '{entity2}' 的关系路径：{path_str}"
        return self._build_result(answer, relations)

    def _generic_query(self, question: str) -> Dict:
        """通用查询"""
        # 尝试提取实体
        entity = self._extract_entity(question)
        if entity:
            return self._query_entity_info([entity], question)

        return self._build_result("未能识别问题中的实体，请提供更具体的健康问题", [], 0)


# 全局问答系统实例
kg_qa = KGQA()