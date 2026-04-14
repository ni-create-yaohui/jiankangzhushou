"""
健康知识图谱核心模块
支持内存存储（默认）和 Neo4j 存储（可选）
"""
import json
import os
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime
from project.logger_handler import logger
from project.path_tool import get_abs_path

from agent.knowledge.entity_types import (
    EntityType, HealthEntity, PREDEFINED_ENTITIES, ENTITY_LABELS, ENTITY_TYPE_DESC
)
from agent.knowledge.relation_types import (
    RelationType, HealthRelation, PREDEFINED_RELATIONS, RELATION_LABELS
)


@dataclass
class KGNode:
    """知识图谱节点"""
    name: str
    entity_type: int
    attributes: Dict = field(default_factory=dict)
    synonyms: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "entity_type_name": EntityType(self.entity_type).name,
            "attributes": self.attributes,
            "synonyms": self.synonyms
        }


@dataclass
class KGEdge:
    """知识图谱边（关系）"""
    source: str
    relation: str
    target: str
    confidence: float = 1.0
    attributes: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "source": self.source,
            "relation": self.relation,
            "target": self.target,
            "confidence": self.confidence,
            "attributes": self.attributes
        }


class HealthKG:
    """
    功能:
    1. 实体存储和查询
    2. 关系存储和查询
    3. 实体关系推理
    4. 最短路径查找
    5. 支持扩展到 Neo4j
    """

    def __init__(self):
        # 节点存储：name -> KGNode
        self._nodes: Dict[str, KGNode] = {}
        # 边存储：source -> {relation -> [targets]}
        self._edges: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        # 反向边：target -> {relation -> [sources]}
        self._reverse_edges: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        # 实体类型索引：entity_type -> [names]
        self._type_index: Dict[int, List[str]] = defaultdict(list)
        # 初始化预定义数据
        self._init_predefined_data()
        logger.info(f"[HealthKG] 知识图谱初始化完成，节点数: {len(self._nodes)}，边数: {sum(len(v) for v in self._edges.values())}")

    def _init_predefined_data(self):
        """初始化预定义的实体和关系"""
        # 添加预定义实体
        for entity in PREDEFINED_ENTITIES:
            self.add_entity(entity)

        # 添加预定义关系
        for relation in PREDEFINED_RELATIONS:
            self.add_relation(relation)

        # 加载扩展数据
        try:
            from agent.knowledge.kg_extended_data import EXTENDED_ENTITIES, EXTENDED_RELATIONS
            for entity in EXTENDED_ENTITIES:
                self.add_entity(entity)
            for relation in EXTENDED_RELATIONS:
                self.add_relation(relation)
            logger.info(f"[HealthKG] 加载扩展数据: 实体{len(EXTENDED_ENTITIES)}个, 关系{len(EXTENDED_RELATIONS)}条")
        except ImportError as e:
            logger.warning(f"[HealthKG] 未加载扩展数据: {e}")

    def add_entity(self, entity: HealthEntity) -> bool:
        """添加实体节点"""
        if entity.name in self._nodes:
            logger.debug(f"[HealthKG] 实体已存在: {entity.name}")
            return False

        node = KGNode(
            name=entity.name,
            entity_type=entity.entity_type.value,
            attributes=entity.attributes,
            synonyms=entity.synonyms
        )
        self._nodes[entity.name] = node
        self._type_index[entity.entity_type.value].append(entity.name)

        # 添加同义词映射
        for syn in entity.synonyms:
            self._nodes[syn] = node  # 同义词指向同一节点

        logger.debug(f"[HealthKG] 添加实体: {entity.name} (类型: {entity.entity_type.name})")
        return True

    def add_relation(self, relation: HealthRelation) -> bool:
        """添加关系边"""
        if relation.entity1 not in self._nodes or relation.entity2 not in self._nodes:
            logger.warning(f"[HealthKG] 关系实体不存在: {relation.entity1} -> {relation.entity2}")
            return False

        # 添加正向边
        self._edges[relation.entity1][relation.relation].append(relation.entity2)
        # 添加反向边
        self._reverse_edges[relation.entity2][relation.relation].append(relation.entity1)

        logger.debug(f"[HealthKG] 添加关系: {relation.entity1} - {relation.relation} -> {relation.entity2}")
        return True

    def get_entity(self, name: str) -> Optional[KGNode]:
        """获取实体"""
        return self._nodes.get(name)

    def get_entity_type(self, name: str) -> Optional[int]:
        """获取实体类型"""
        node = self.get_entity(name)
        return node.entity_type if node else None

    def get_entity_attributes(self, name: str) -> Dict:
        """获取实体属性"""
        node = self.get_entity(name)
        return node.attributes if node else {}

    def find_entities_by_relation(self, entity: str, relation: str, direction: str = "out") -> List[str]:
        """
        Args:
            entity: 实体名称
            relation: 关系类型
            direction: "out" 出边, "in" 入边

        Returns:
            关联实体列表
        """
        if direction == "out":
            return self._edges.get(entity, {}).get(relation, [])
        else:
            return self._reverse_edges.get(entity, {}).get(relation, [])

    def get_entity_relations(self, entity: str) -> List[Dict]:
        """获取实体的所有关系"""
        relations = []
        # 出边
        for rel, targets in self._edges.get(entity, {}).items():
            for target in targets:
                relations.append({
                    "entity1": entity,
                    "relation": rel,
                    "entity2": target,
                    "direction": "out"
                })
        # 入边
        for rel, sources in self._reverse_edges.get(entity, {}).items():
            for source in sources:
                relations.append({
                    "entity1": source,
                    "relation": rel,
                    "entity2": entity,
                    "direction": "in"
                })
        return relations

    def find_path(self, entity1: str, entity2: str, max_depth: int = 4) -> List[List[str]]:
        """
        查找两个实体之间的路径

        Args:
            entity1: 起始实体
            entity2: 目标实体
            max_depth: 最大搜索深度

        Returns:
            路径列表 [[entity, relation, entity, relation, ...]]
        """
        if entity1 not in self._nodes or entity2 not in self._nodes:
            return []

        results = []
        self._dfs_path(entity1, entity2, [entity1], [], results, max_depth, set())
        return results

    def _dfs_path(self, current: str, target: str, path: List[str], relations: List[str],
                  results: List, max_depth: int, visited: Set):
        """DFS搜索路径"""
        if len(path) > max_depth + 1:
            return

        if current == target:
            # 构建完整路径
            full_path = []
            for i in range(len(path) - 1):
                full_path.append(path[i])
                # 找到连接关系
                for rel, targets in self._edges.get(path[i], {}).items():
                    if path[i + 1] in targets:
                        full_path.append(rel)
                        break
            full_path.append(target)
            results.append(full_path)
            return

        visited.add(current)
        for rel, targets in self._edges.get(current, {}).items():
            for t in targets:
                if t not in visited:
                    self._dfs_path(t, target, path + [t], relations + [rel],
                                   results, max_depth, visited)
        visited.remove(current)

    def match_entity(self, text: str) -> Optional[str]:
        """
        文本匹配实体

        Args:
            text: 输入文本

        Returns:
            匹配的实体名称（优先返回完全匹配，其次同义词匹配）
        """
        # 完全匹配
        if text in self._nodes:
            return self._nodes[text].name

        # 部分匹配
        for name, node in self._nodes.items():
            if text in name or name in text:
                return node.name

        return None

    def get_entity_type_desc(self, name: str) -> Dict:
        """获取实体类型描述"""
        entity_type = self.get_entity_type(name)
        if entity_type:
            return ENTITY_TYPE_DESC.get(EntityType(entity_type), {})
        return {}

    def search_entities(self, keyword: str, entity_type: EntityType = None) -> List[Dict]:
        """搜索实体"""
        results = []
        for name, node in self._nodes.items():
            if keyword.lower() in name.lower() or any(keyword.lower() in syn.lower() for syn in node.synonyms):
                if entity_type is None or node.entity_type == entity_type.value:
                    results.append(node.to_dict())
        return results

    def get_schema(self) -> Dict:
        """获取图谱架构描述"""
        entity_stats = defaultdict(int)
        for name, node in self._nodes.items():
            if name == node.name:  # 只统计主实体，不统计同义词
                entity_stats[node.entity_type] += 1

        relation_stats = defaultdict(int)
        for src, rels in self._edges.items():
            for rel, targets in rels.items():
                relation_stats[rel] += len(targets)

        # 使用中文实体类型名称
        entity_types_cn = {}
        for k, v in entity_stats.items():
            type_desc = ENTITY_TYPE_DESC.get(EntityType(k), {})
            cn_name = type_desc.get("name", EntityType(k).name)
            entity_types_cn[cn_name] = v

        return {
            "nodes": len(set(n.name for n in self._nodes.values())),
            "edges": sum(len(v) for v in self._edges.values()),
            "entity_types": entity_types_cn,
            "relation_types": dict(relation_stats)
        }

    def get_all_diseases(self) -> List[str]:
        """获取所有疾病实体列表"""
        return self._type_index.get(EntityType.DISEASE.value, [])

    def get_disease_graph(self, disease_name: str) -> Dict:
        """
        获取疾病的完整图谱数据

        包含症状、治疗、风险因素、药物、饮食建议等关联信息

        Args:
            disease_name: 疾病名称

        Returns:
            {
                "disease": 疾病名称,
                "nodes": [{"name": 名称, "entity_type": EntityType值, "category": 类别索引}],
                "links": [{"source": 源, "target": 目标, "relation": 关系}]
            }
        """
        if disease_name not in self._nodes:
            return {"disease": disease_name, "nodes": [], "links": [], "error": "疾病不存在"}

        # 统一的节点类别映射：EntityType值 -> category索引
        # 与前端 categories 数组顺序一致
        category_map = {
            EntityType.DISEASE.value: 0,       # 疾病
            EntityType.SYMPTOM.value: 1,       # 症状
            EntityType.DRUG.value: 2,          # 药物
            EntityType.FOOD.value: 3,          # 食物
            EntityType.NUTRIENT.value: 4,      # 营养素
            EntityType.EXERCISE.value: 5,      # 运动
            EntityType.RISK_FACTOR.value: 6,   # 危险因素
            EntityType.DIET_TYPE.value: 7,     # 饮食类型
            EntityType.HEALTH_GOAL.value: 8,   # 健康目标
            EntityType.BODY_PART.value: 9,     # 人体部位
            EntityType.HABIT.value: 10,        # 生活习惯
            EntityType.TREATMENT.value: 11,    # 治疗方法
            EntityType.MEDICAL_TEST.value: 12, # 医学检查
            EntityType.HEALTH_TERM.value: 13,  # 健康术语
            EntityType.FITNESS_LEVEL.value: 14,# 其他
            EntityType.OTHER.value: 14,        # 其他
        }

        # 类型名称映射
        type_name_map = {
            EntityType.DISEASE.value: "disease",
            EntityType.SYMPTOM.value: "symptom",
            EntityType.RISK_FACTOR.value: "risk_factor",
            EntityType.TREATMENT.value: "treatment",
            EntityType.DRUG.value: "drug",
            EntityType.BODY_PART.value: "body_part",
            EntityType.DIET_TYPE.value: "diet",
            EntityType.EXERCISE.value: "exercise",
            EntityType.HABIT.value: "habit",
            EntityType.FOOD.value: "food",
            EntityType.NUTRIENT.value: "nutrient",
            EntityType.HEALTH_GOAL.value: "health_goal",
            EntityType.MEDICAL_TEST.value: "medical_test",
            EntityType.HEALTH_TERM.value: "health_term",
            EntityType.FITNESS_LEVEL.value: "fitness_level",
            EntityType.OTHER.value: "other",
        }

        nodes = []
        links = []
        visited_nodes = set()

        # 添加疾病中心节点
        disease_node = self._nodes[disease_name]
        nodes.append({
            "name": disease_name,
            "entity_type": disease_node.entity_type,
            "type": type_name_map.get(disease_node.entity_type, "other"),
            "category": category_map.get(disease_node.entity_type, 14),
            "symbolSize": 60,  # 中心节点更大
            "attributes": disease_node.attributes
        })
        visited_nodes.add(disease_name)

        # 获取疾病的所有关系
        relations = self.get_entity_relations(disease_name)

        for rel in relations:
            # 获取关联实体名称
            related_entity = rel["entity2"] if rel["direction"] == "out" else rel["entity1"]

            if related_entity not in visited_nodes:
                node = self._nodes.get(related_entity)
                if node:
                    nodes.append({
                        "name": related_entity,
                        "entity_type": node.entity_type,
                        "type": type_name_map.get(node.entity_type, "other"),
                        "category": category_map.get(node.entity_type, 14),
                        "symbolSize": 40,
                        "attributes": node.attributes
                    })
                    visited_nodes.add(related_entity)

            # 构建边
            link = {
                "source": rel["entity1"],
                "target": rel["entity2"],
                "relation": rel["relation"]
            }
            links.append(link)

        # 收集详情信息（用于详情面板展示）
        details = {
            "symptoms": [],
            "risk_factors": [],
            "treatments": [],
            "drugs": [],
            "diets": [],
            "affected_parts": [],
            "habits": [],
            "foods": [],
            "nutrients": [],
            "exercises": [],
            "health_goals": [],
            "medical_tests": [],
            "health_terms": []
        }

        for node in nodes[1:]:  # 跳过中心疾病节点
            node_type = node["type"]
            node_name = node["name"]
            if node_type == "symptom":
                details["symptoms"].append(node_name)
            elif node_type == "risk_factor":
                details["risk_factors"].append(node_name)
            elif node_type == "treatment":
                details["treatments"].append(node_name)
            elif node_type == "drug":
                details["drugs"].append(node_name)
            elif node_type == "diet":
                details["diets"].append(node_name)
            elif node_type == "body_part":
                details["affected_parts"].append(node_name)
            elif node_type == "habit":
                details["habits"].append(node_name)
            elif node_type == "food":
                details["foods"].append(node_name)
            elif node_type == "nutrient":
                details["nutrients"].append(node_name)
            elif node_type == "exercise":
                details["exercises"].append(node_name)
            elif node_type == "health_goal":
                details["health_goals"].append(node_name)
            elif node_type == "medical_test":
                details["medical_tests"].append(node_name)
            elif node_type == "health_term":
                details["health_terms"].append(node_name)

        return {
            "disease": disease_name,
            "nodes": nodes,
            "links": links,
            "details": details
        }

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        # 去重：只保留主实体（name == node.name）
        unique_nodes = []
        seen_names = set()
        for node in self._nodes.values():
            if node.name not in seen_names:
                unique_nodes.append(node)
                seen_names.add(node.name)

        return {
            "nodes": [n.to_dict() for n in unique_nodes],
            "edges": [
                {"source": src, "relation": rel, "target": tgt}
                for src, rels in self._edges.items()
                for rel, targets in rels.items()
                for tgt in targets
            ],
            "schema": self.get_schema()
        }

    def to_json_file(self, filepath: str) -> bool:
        """
        持久化知识图谱到JSON文件

        Args:
            filepath: 文件路径

        Returns:
            是否成功
        """
        try:
            # 确保目录存在
            dir_path = os.path.dirname(filepath)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)

            data = self.to_dict()
            data["saved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"[HealthKG] 知识图谱持久化成功: {filepath}")
            return True

        except Exception as e:
            logger.error(f"[HealthKG] 知识图谱持久化失败: {e}", exc_info=True)
            return False

    def load_from_json_file(self, filepath: str) -> bool:
        """
        从JSON文件恢复知识图谱

        Args:
            filepath: 文件路径

        Returns:
            是否成功
        """
        try:
            if not os.path.exists(filepath):
                logger.warning(f"[HealthKG] 持久化文件不存在: {filepath}")
                return False

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 加载节点
            added_nodes = 0
            for node_data in data.get("nodes", []):
                name = node_data.get("name", "")
                entity_type = node_data.get("entity_type", 0)

                if name and entity_type and not self.get_entity(name):
                    entity = HealthEntity(
                        name=name,
                        entity_type=EntityType(entity_type),
                        description=node_data.get("description", ""),
                        attributes=node_data.get("attributes", {}),
                        synonyms=node_data.get("synonyms", []),
                        source=node_data.get("source", "persistent")
                    )
                    self.add_entity(entity)
                    added_nodes += 1

            # 加载边
            added_edges = 0
            for edge_data in data.get("edges", []):
                src = edge_data.get("source", "")
                rel = edge_data.get("relation", "")
                tgt = edge_data.get("target", "")

                if src and rel and tgt:
                    if src in self._nodes and tgt in self._nodes:
                        # 检查是否已存在
                        if tgt not in self._edges[src].get(rel, []):
                            self._edges[src][rel].append(tgt)
                            self._reverse_edges[tgt][rel].append(src)
                            added_edges += 1

            logger.info(f"[HealthKG] 从文件恢复成功: {filepath}, 新增节点{added_nodes}个, 新增边{added_edges}条")
            return True

        except Exception as e:
            logger.error(f"[HealthKG] 从文件恢复失败: {e}", exc_info=True)
            return False

    def add_entity_if_not_exists(self, entity: HealthEntity) -> Tuple[bool, str]:
        """
        添加实体（如果不存在）

        Args:
            entity: 实体对象

        Returns:
            (是否新增, 实体名称)
        """
        if entity.name in self._nodes:
            return (False, entity.name)
        success = self.add_entity(entity)
        return (success, entity.name)

    def bulk_add_entities(self, entities: List[HealthEntity]) -> Dict:
        """
        批量添加实体

        Args:
            entities: 实体列表

        Returns:
            {"added": 添加数量, "skipped": 跳过数量, "added_names": 已添加名称列表}
        """
        added = 0
        skipped = 0
        added_names = []

        for entity in entities:
            is_new, name = self.add_entity_if_not_exists(entity)
            if is_new:
                added += 1
                added_names.append(name)
            else:
                skipped += 1

        logger.info(f"[HealthKG] 批量添加实体: 新增{added}个, 跳过{skipped}个")
        return {"added": added, "skipped": skipped, "added_names": added_names}

    def bulk_add_relations(self, relations: List[HealthRelation]) -> Dict:
        """
        批量添加关系

        Args:
            relations: 关系列表

        Returns:
            {"added": 添加数量, "skipped": 跳过数量}
        """
        added = 0
        skipped = 0

        for relation in relations:
            # 确保实体存在
            if relation.entity1 not in self._nodes:
                # 创建临时实体
                temp_entity1 = HealthEntity(
                    name=relation.entity1,
                    entity_type=EntityType(relation.entity1_type) if relation.entity1_type else EntityType.OTHER,
                    source=relation.source or "auto"
                )
                self.add_entity(temp_entity1)

            if relation.entity2 not in self._nodes:
                temp_entity2 = HealthEntity(
                    name=relation.entity2,
                    entity_type=EntityType(relation.entity2_type) if relation.entity2_type else EntityType.OTHER,
                    source=relation.source or "auto"
                )
                self.add_entity(temp_entity2)

            # 添加关系
            if self.add_relation(relation):
                added += 1
            else:
                skipped += 1

        logger.info(f"[HealthKG] 批量添加关系: 新增{added}条, 跳过{skipped}条")
        return {"added": added, "skipped": skipped}

    def get_entities_by_source(self, source_doc_id: str) -> List[Dict]:
        """
        按来源文档获取实体

        Args:
            source_doc_id: 文档ID

        Returns:
            实体列表
        """
        entities = []
        for name, node in self._nodes.items():
            if name == node.name:  # 只统计主实体
                if node.attributes.get("source_doc_id") == source_doc_id:
                    entities.append(node.to_dict())
        return entities

    def get_new_entities(self, limit: int = 100) -> List[Dict]:
        """
        获取新增实体列表（非预定义实体）

        Args:
            limit: 最大返回数量

        Returns:
            新增实体列表
        """
        predefined_names = {e.name for e in PREDEFINED_ENTITIES}
        new_entities = []

        for name, node in self._nodes.items():
            if name == node.name and name not in predefined_names:
                entity_data = node.to_dict()
                entity_data["is_new"] = True
                new_entities.append(entity_data)

        return new_entities[:limit]

    def get_stats_detailed(self) -> Dict:
        """
        获取详细统计信息

        Returns:
            详细统计字典
        """
        predefined_names = {e.name for e in PREDEFINED_ENTITIES}
        predefined_relations_count = len(PREDEFINED_RELATIONS)

        new_entities_count = 0
        for name, node in self._nodes.items():
            if name == node.name and name not in predefined_names:
                new_entities_count += 1

        total_edges = sum(len(v) for v in self._edges.values())
        new_relations_count = total_edges - predefined_relations_count if total_edges > predefined_relations_count else 0

        return {
            "total_entities": len(set(n.name for n in self._nodes.values())),
            "predefined_entities": len(predefined_names),
            "new_entities": new_entities_count,
            "total_relations": total_edges,
            "predefined_relations": predefined_relations_count,
            "new_relations": new_relations_count,
            "entity_types": {k: len(v) for k, v in self._type_index.items()},
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


# 全局知识图谱实例
health_kg = HealthKG()