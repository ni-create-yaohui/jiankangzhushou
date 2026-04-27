"""
核心组件:
- HealthKG: 健康知识图谱存储和查询
- KGQA: 基于图谱的智能问答
- HealthNER: 健康领域命名实体识别
"""
from agent.knowledge.entity_types import EntityType, HealthEntity, ENTITY_TYPE_DESC, get_entity_type_desc, ENTITY_LABELS
from agent.knowledge.relation_types import RelationType, HealthRelation, RELATION_TYPE_DESC, get_relation_desc, RELATION_LABELS
from agent.knowledge.health_kg import health_kg, HealthKG
from agent.knowledge.kg_qa import kg_qa, KGQA
from agent.knowledge.ner import health_ner, HealthNER

__all__ = [
    "EntityType", "HealthEntity", "ENTITY_TYPE_DESC", "get_entity_type_desc", "ENTITY_LABELS",
    "RelationType", "HealthRelation", "RELATION_TYPE_DESC", "get_relation_desc", "RELATION_LABELS",
    "health_kg", "HealthKG",
    "kg_qa", "KGQA",
    "health_ner", "HealthNER"
]