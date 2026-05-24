"""
Neo4j 后端知识图谱存储

暴露与 HealthKG 相同的查询 API，底层使用 Neo4j 原生图查询。
注意：entity_types / relation_types 的导入放在方法体内，避免循环依赖。
"""
import json
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from agent.database.neo4j_config import (
    NEO4J_TYPE_TO_RELATION,
    RELATION_TO_NEO4J_TYPE,
    neo4j_conn,
)
from project.logger_handler import logger


# ── 共享映射表（从 entity_types 惰性构建，避免循环导入）──
_CATEGORY_MAP = None
_TYPE_NAME_MAP = None


def _get_category_map() -> Dict:
    """EntityType value → ECharts category index"""
    global _CATEGORY_MAP
    if _CATEGORY_MAP is None:
        from agent.knowledge.entity_types import EntityType
        _CATEGORY_MAP = {
            EntityType.DISEASE.value: 0,
            EntityType.SYMPTOM.value: 1,
            EntityType.DRUG.value: 2,
            EntityType.FOOD.value: 3,
            EntityType.NUTRIENT.value: 4,
            EntityType.EXERCISE.value: 5,
            EntityType.RISK_FACTOR.value: 6,
            EntityType.DIET_TYPE.value: 7,
            EntityType.HEALTH_GOAL.value: 8,
            EntityType.BODY_PART.value: 9,
            EntityType.HABIT.value: 10,
            EntityType.TREATMENT.value: 11,
            EntityType.MEDICAL_TEST.value: 12,
            EntityType.HEALTH_TERM.value: 13,
            EntityType.FITNESS_LEVEL.value: 14,
            EntityType.OTHER.value: 14,
        }
    return _CATEGORY_MAP


def _get_type_name_map() -> Dict:
    """EntityType value → type name string"""
    global _TYPE_NAME_MAP
    if _TYPE_NAME_MAP is None:
        from agent.knowledge.entity_types import EntityType
        _TYPE_NAME_MAP = {
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
    return _TYPE_NAME_MAP


class Neo4jKGStore:
    """Neo4j 后端知识图谱存储"""

    def __init__(self):
        self._initialized = False

    # ── 初始化 ────────────────────────────────────────────
    def initialize(self):
        """创建约束和索引"""
        if self._initialized:
            return
        try:
            with neo4j_conn.get_session() as session:
                session.run(
                    "CREATE CONSTRAINT entity_name_unique IF NOT EXISTS "
                    "FOR (e:HealthEntity) REQUIRE e.name IS UNIQUE"
                )
                try:
                    session.run(
                        "CREATE FULLTEXT INDEX entity_name_search IF NOT EXISTS "
                        "FOR (e:HealthEntity) ON EACH [e.name, e.synonyms]"
                    )
                except Exception:
                    pass
            self._initialized = True
            logger.info("[Neo4jKGStore] 初始化完成")
        except Exception as e:
            logger.error(f"[Neo4jKGStore] 初始化失败: {e}")
            raise

    def initialize_predefined_data(self, predefined_entities, predefined_relations,
                                   extended_entities=None, extended_relations=None):
        """初始化预定义数据到 Neo4j"""
        self.initialize()

        with neo4j_conn.get_session() as session:
            for entity in predefined_entities:
                self._merge_entity(session, entity)

            if extended_entities:
                for entity in extended_entities:
                    self._merge_entity(session, entity)

            for rel in predefined_relations:
                self._merge_relation(session, rel)

            if extended_relations:
                for rel in extended_relations:
                    self._merge_relation(session, rel)

        logger.info("[Neo4jKGStore] 预定义数据初始化完成")

    # ── 内部写入方法 ──────────────────────────────────────
    def _merge_entity(self, session, entity):
        """MERGE 单个实体节点"""
        synonyms_json = json.dumps(entity.synonyms, ensure_ascii=False)
        attrs_json = json.dumps(entity.attributes, ensure_ascii=False)
        session.run(
            """
            MERGE (e:HealthEntity {name: $name})
            SET e.entity_type = $entity_type,
                e.attributes = $attributes,
                e.synonyms = $synonyms
            """,
            name=entity.name,
            entity_type=entity.entity_type.value,
            attributes=attrs_json,
            synonyms=synonyms_json,
        )

    def _merge_relation(self, session, relation):
        """MERGE 单个关系边"""
        neo4j_type = RELATION_TO_NEO4J_TYPE.get(relation.relation, _sanitize_relation(relation.relation))
        session.run(
            """
            MERGE (e1:HealthEntity {name: $e1})
            ON CREATE SET e1.entity_type = $e1_type
            MERGE (e2:HealthEntity {name: $e2})
            ON CREATE SET e2.entity_type = $e2_type
            MERGE (e1)-[r:%s]->(e2)
            ON CREATE SET r.confidence = $confidence, r.source_doc_id = $source, r.created_at = $created_at
            """ % neo4j_type,
            e1=relation.entity1,
            e1_type=relation.entity1_type or 0,
            e2=relation.entity2,
            e2_type=relation.entity2_type or 0,
            confidence=1.0,
            source=relation.source or "",
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    # ── 实体操作 ──────────────────────────────────────────
    def add_entity(self, entity) -> bool:
        """添加实体节点"""
        try:
            with neo4j_conn.get_session() as session:
                result = session.run(
                    """
                    MERGE (e:HealthEntity {name: $name})
                    ON CREATE SET e.entity_type = $entity_type,
                                  e.attributes = $attributes,
                                  e.synonyms = $synonyms
                    RETURN e
                    """,
                    name=entity.name,
                    entity_type=entity.entity_type.value,
                    attributes=json.dumps(entity.attributes, ensure_ascii=False),
                    synonyms=json.dumps(entity.synonyms, ensure_ascii=False),
                )
                return result.single() is not None
        except Exception as e:
            logger.error(f"[Neo4jKGStore] add_entity 失败: {e}")
            return False

    def add_relation(self, relation) -> bool:
        """添加关系边"""
        try:
            with neo4j_conn.get_session() as session:
                self._merge_relation(session, relation)
                return True
        except Exception as e:
            logger.error(f"[Neo4jKGStore] add_relation 失败: {e}")
            return False

    def get_entity(self, name: str) -> Optional[Dict]:
        """获取实体（返回 dict，兼容 KGNode 接口）"""
        try:
            with neo4j_conn.get_session() as session:
                result = session.run(
                    "MATCH (e:HealthEntity {name: $name}) RETURN e",
                    name=name,
                )
                record = result.single()
                if record is None:
                    return None
                return self._node_to_dict(record["e"])
        except Exception:
            return None

    def get_entity_type(self, name: str) -> Optional[int]:
        entity = self.get_entity(name)
        return entity.get("entity_type") if entity else None

    # ── 关系查询 ──────────────────────────────────────────
    def find_entities_by_relation(self, entity: str, relation: str, direction: str = "out") -> List[str]:
        neo4j_type = RELATION_TO_NEO4J_TYPE.get(relation, _sanitize_relation(relation))
        try:
            with neo4j_conn.get_session() as session:
                if direction == "out":
                    result = session.run(
                        f"MATCH (e1:HealthEntity {{name: $name}})-[:{neo4j_type}]->(e2:HealthEntity) "
                        "RETURN e2.name AS name",
                        name=entity,
                    )
                else:
                    result = session.run(
                        f"MATCH (e1:HealthEntity)-[:{neo4j_type}]->(e2:HealthEntity {{name: $name}}) "
                        "RETURN e1.name AS name",
                        name=entity,
                    )
                return [r["name"] for r in result]
        except Exception:
            return []

    def get_entity_relations(self, entity: str) -> List[Dict]:
        relations = []
        try:
            with neo4j_conn.get_session() as session:
                result = session.run(
                    "MATCH (e1:HealthEntity {name: $name})-[r]->(e2:HealthEntity) "
                    "RETURN type(r) AS rel_type, e2.name AS target",
                    name=entity,
                )
                for record in result:
                    rel_cn = NEO4J_TYPE_TO_RELATION.get(record["rel_type"], record["rel_type"])
                    relations.append({
                        "entity1": entity, "relation": rel_cn,
                        "entity2": record["target"], "direction": "out",
                    })

                result = session.run(
                    "MATCH (e1:HealthEntity)-[r]->(e2:HealthEntity {name: $name}) "
                    "RETURN type(r) AS rel_type, e1.name AS source",
                    name=entity,
                )
                for record in result:
                    rel_cn = NEO4J_TYPE_TO_RELATION.get(record["rel_type"], record["rel_type"])
                    relations.append({
                        "entity1": record["source"], "relation": rel_cn,
                        "entity2": entity, "direction": "in",
                    })
        except Exception:
            pass
        return relations

    # ── 路径查询 ──────────────────────────────────────────
    def find_path(self, entity1: str, entity2: str, max_depth: int = 4) -> List[List[str]]:
        paths = []
        try:
            with neo4j_conn.get_session() as session:
                result = session.run(
                    """
                    MATCH path = (e1:HealthEntity {name: $name1})-[*..%d]-(e2:HealthEntity {name: $name2})
                    RETURN path LIMIT 10
                    """ % max_depth,
                    name1=entity1, name2=entity2,
                )
                for record in result:
                    path = record["path"]
                    elements = []
                    nodes = path.nodes
                    rels = path.relationships
                    for i, node in enumerate(nodes):
                        elements.append(node["name"])
                        if i < len(rels):
                            rel_type = rels[i].type
                            rel_cn = NEO4J_TYPE_TO_RELATION.get(rel_type, rel_type)
                            elements.append(rel_cn)
                    paths.append(elements)
        except Exception:
            pass
        return paths

    # ── 文本匹配 ──────────────────────────────────────────
    def match_entity(self, text: str) -> Optional[str]:
        try:
            with neo4j_conn.get_session() as session:
                result = session.run(
                    "MATCH (e:HealthEntity {name: $name}) RETURN e.name AS name",
                    name=text,
                )
                record = result.single()
                if record:
                    return record["name"]

                result = session.run(
                    "MATCH (e:HealthEntity) WHERE e.name CONTAINS $text OR $text CONTAINS e.name "
                    "RETURN e.name AS name LIMIT 1",
                    text=text,
                )
                record = result.single()
                return record["name"] if record else None
        except Exception:
            return None

    # ── 搜索 ──────────────────────────────────────────────
    def search_entities(self, keyword: str, entity_type: Optional[int] = None) -> List[Dict]:
        results = []
        try:
            with neo4j_conn.get_session() as session:
                if entity_type is not None:
                    result = session.run(
                        "MATCH (e:HealthEntity) "
                        "WHERE toLower(e.name) CONTAINS toLower($kw) AND e.entity_type = $etype "
                        "RETURN e",
                        kw=keyword, etype=entity_type,
                    )
                else:
                    result = session.run(
                        "MATCH (e:HealthEntity) WHERE toLower(e.name) CONTAINS toLower($kw) RETURN e",
                        kw=keyword,
                    )
                for record in result:
                    results.append(self._node_to_dict(record["e"]))
        except Exception:
            pass
        return results

    # ── Schema / Stats ───────────────────────────────────
    def get_schema(self) -> Dict:
        from agent.knowledge.entity_types import ENTITY_TYPE_DESC, EntityType
        entity_stats = {}
        relation_stats = {}
        try:
            with neo4j_conn.get_session() as session:
                result = session.run(
                    "MATCH (e:HealthEntity) RETURN e.entity_type AS etype, count(*) AS cnt"
                )
                for r in result:
                    type_desc = ENTITY_TYPE_DESC.get(EntityType(r["etype"]), {})
                    cn_name = type_desc.get("name", str(r["etype"]))
                    entity_stats[cn_name] = r["cnt"]

                result = session.run(
                    "MATCH (:HealthEntity)-[r]->(:HealthEntity) "
                    "RETURN type(r) AS rel_type, count(*) AS cnt"
                )
                for r in result:
                    rel_cn = NEO4J_TYPE_TO_RELATION.get(r["rel_type"], r["rel_type"])
                    relation_stats[rel_cn] = r["cnt"]
        except Exception:
            pass

        return {
            "nodes": sum(entity_stats.values()),
            "edges": sum(relation_stats.values()),
            "entity_types": entity_stats,
            "relation_types": relation_stats,
        }

    def get_all_diseases(self) -> List[str]:
        from agent.knowledge.entity_types import EntityType
        try:
            with neo4j_conn.get_session() as session:
                result = session.run(
                    "MATCH (e:HealthEntity {entity_type: $etype}) RETURN e.name AS name",
                    etype=EntityType.DISEASE.value,
                )
                return [r["name"] for r in result]
        except Exception:
            return []

    def get_disease_graph(self, disease_name: str) -> Dict:
        try:
            with neo4j_conn.get_session() as session:
                check = session.run(
                    "MATCH (e:HealthEntity {name: $name}) RETURN e",
                    name=disease_name,
                )
                disease_record = check.single()
                if not disease_record:
                    return {"disease": disease_name, "nodes": [], "links": [], "error": "疾病不存在"}

                category_map = _get_category_map()
                type_name_map = _get_type_name_map()

                nodes = []
                links = []
                visited = set()

                disease_node = disease_record["e"]
                nodes.append({
                    "name": disease_name,
                    "entity_type": disease_node["entity_type"],
                    "type": type_name_map.get(disease_node["entity_type"], "other"),
                    "category": category_map.get(disease_node["entity_type"], 14),
                    "symbolSize": 60,
                    "attributes": _safe_json_loads(disease_node.get("attributes", "{}")),
                })
                visited.add(disease_name)

                relations = self.get_entity_relations(disease_name)
                for rel in relations:
                    related = rel["entity2"] if rel["direction"] == "out" else rel["entity1"]
                    if related not in visited:
                        ent = self.get_entity(related)
                        if ent:
                            et = ent["entity_type"]
                            nodes.append({
                                "name": related,
                                "entity_type": et,
                                "type": type_name_map.get(et, "other"),
                                "category": category_map.get(et, 14),
                                "symbolSize": 40,
                                "attributes": ent.get("attributes", {}),
                            })
                            visited.add(related)

                    links.append({
                        "source": rel["entity1"],
                        "target": rel["entity2"],
                        "relation": rel["relation"],
                    })

                details = _build_disease_details(nodes)
                return {
                    "disease": disease_name,
                    "nodes": nodes,
                    "links": links,
                    "details": details,
                }
        except Exception as e:
            return {"disease": disease_name, "nodes": [], "links": [], "error": str(e)}

    # ── 批量操作 ──────────────────────────────────────────
    def bulk_add_entities(self, entities) -> Dict:
        added = 0
        skipped = 0
        added_names = []
        try:
            with neo4j_conn.get_session() as session:
                for entity in entities:
                    result = session.run(
                        """
                        MERGE (e:HealthEntity {name: $name})
                        ON CREATE SET e.entity_type = $entity_type,
                                      e.attributes = $attributes,
                                      e.synonyms = $synonyms
                        RETURN e.name AS name
                        """,
                        name=entity.name,
                        entity_type=entity.entity_type.value,
                        attributes=json.dumps(entity.attributes, ensure_ascii=False),
                        synonyms=json.dumps(entity.synonyms, ensure_ascii=False),
                    )
                    record = result.single()
                    if record:
                        added += 1
                        added_names.append(entity.name)
                    else:
                        skipped += 1
        except Exception as e:
            logger.error(f"[Neo4jKGStore] bulk_add_entities 失败: {e}")
        return {"added": added, "skipped": skipped, "added_names": added_names}

    def bulk_add_relations(self, relations) -> Dict:
        added = 0
        skipped = 0
        try:
            with neo4j_conn.get_session() as session:
                for relation in relations:
                    try:
                        self._merge_relation(session, relation)
                        added += 1
                    except Exception:
                        skipped += 1
        except Exception as e:
            logger.error(f"[Neo4jKGStore] bulk_add_relations 失败: {e}")
        return {"added": added, "skipped": skipped}

    # ── 统计 ──────────────────────────────────────────────
    def get_stats_detailed(self) -> Dict:
        from agent.knowledge.entity_types import PREDEFINED_ENTITIES
        from agent.knowledge.relation_types import PREDEFINED_RELATIONS
        try:
            with neo4j_conn.get_session() as session:
                total_entities = session.run(
                    "MATCH (e:HealthEntity) RETURN count(*) AS cnt"
                ).single()["cnt"]

                total_relations = session.run(
                    "MATCH (:HealthEntity)-[r]->(:HealthEntity) RETURN count(*) AS cnt"
                ).single()["cnt"]

                type_dist = {}
                result = session.run(
                    "MATCH (e:HealthEntity) RETURN e.entity_type AS etype, count(*) AS cnt"
                )
                for r in result:
                    type_dist[r["etype"]] = r["cnt"]

                predefined_names = {e.name for e in PREDEFINED_ENTITIES}
                predefined_count = session.run(
                    "MATCH (e:HealthEntity) WHERE e.name IN $names RETURN count(*) AS cnt",
                    names=list(predefined_names),
                ).single()["cnt"]

                return {
                    "total_entities": total_entities,
                    "predefined_entities": predefined_count,
                    "new_entities": total_entities - predefined_count,
                    "total_relations": total_relations,
                    "predefined_relations": len(PREDEFINED_RELATIONS),
                    "new_relations": max(0, total_relations - len(PREDEFINED_RELATIONS)),
                    "entity_types": type_dist,
                    "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
        except Exception:
            return {
                "total_entities": 0, "predefined_entities": 0, "new_entities": 0,
                "total_relations": 0, "predefined_relations": 0, "new_relations": 0,
                "entity_types": {}, "last_update": "",
            }

    def get_new_entities(self, limit: int = 100) -> List[Dict]:
        from agent.knowledge.entity_types import PREDEFINED_ENTITIES
        predefined_names = {e.name for e in PREDEFINED_ENTITIES}
        try:
            with neo4j_conn.get_session() as session:
                result = session.run(
                    "MATCH (e:HealthEntity) "
                    "WHERE NOT e.name IN $names "
                    "RETURN e LIMIT $limit",
                    names=list(predefined_names), limit=limit,
                )
                entities = []
                for record in result:
                    d = self._node_to_dict(record["e"])
                    d["is_new"] = True
                    entities.append(d)
                return entities
        except Exception:
            return []

    def get_entities_by_source(self, source_doc_id: str) -> List[Dict]:
        try:
            with neo4j_conn.get_session() as session:
                result = session.run(
                    "MATCH (e:HealthEntity) WHERE e.attributes CONTAINS $doc_id RETURN e",
                    doc_id=source_doc_id,
                )
                return [self._node_to_dict(r["e"]) for r in result]
        except Exception:
            return []

    def get_all_entity_names_and_types(self) -> Dict[str, int]:
        try:
            with neo4j_conn.get_session() as session:
                result = session.run(
                    "MATCH (e:HealthEntity) RETURN e.name AS name, e.entity_type AS etype"
                )
                return {r["name"]: r["etype"] for r in result}
        except Exception:
            return {}

    # ── 导出 ──────────────────────────────────────────────
    def export_to_json(self, filepath: str) -> bool:
        try:
            os = __import__("os")
            dir_path = os.path.dirname(filepath)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)

            with neo4j_conn.get_session() as session:
                nodes_result = session.run("MATCH (e:HealthEntity) RETURN e")
                nodes = [self._node_to_dict(r["e"]) for r in nodes_result]

                edges_result = session.run(
                    "MATCH (e1:HealthEntity)-[r]->(e2:HealthEntity) "
                    "RETURN e1.name AS source, type(r) AS rel_type, e2.name AS target"
                )
                edges = []
                for r in edges_result:
                    rel_cn = NEO4J_TYPE_TO_RELATION.get(r["rel_type"], r["rel_type"])
                    edges.append({
                        "source": r["source"], "relation": rel_cn, "target": r["target"],
                    })

            data = {
                "nodes": nodes, "edges": edges,
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"[Neo4jKGStore] 导出成功: {filepath}")
            return True
        except Exception as e:
            logger.error(f"[Neo4jKGStore] 导出失败: {e}")
            return False

    # ── 工具方法 ──────────────────────────────────────────
    def _node_to_dict(self, node) -> Dict:
        from agent.knowledge.entity_types import EntityType
        return {
            "name": node["name"],
            "entity_type": node["entity_type"],
            "entity_type_name": EntityType(node["entity_type"]).name
                if node["entity_type"] else "OTHER",
            "attributes": _safe_json_loads(node.get("attributes", "{}")),
            "synonyms": _safe_json_loads(node.get("synonyms", "[]")),
        }


# ── 辅助函数 ──────────────────────────────────────────────
def _sanitize_relation(relation: str) -> str:
    import hashlib
    return "REL_" + hashlib.md5(relation.encode()).hexdigest()[:8].upper()


def _safe_json_loads(s):
    if isinstance(s, (dict, list)):
        return s
    try:
        return json.loads(s)
    except Exception:
        return {}


def _build_disease_details(nodes: List[Dict]) -> Dict:
    type_name_map = {
        3: "symptoms", 13: "risk_factors", 5: "treatments", 4: "drugs",
        9: "diets", 1: "affected_parts", 12: "habits", 7: "foods",
        8: "nutrients", 10: "exercises", 14: "health_goals",
        6: "medical_tests", 15: "health_terms",
    }
    details = {v: [] for v in type_name_map.values()}
    for node in nodes[1:]:
        key = type_name_map.get(node.get("entity_type"))
        if key:
            details[key].append(node["name"])
    return details
