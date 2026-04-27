"""
知识图谱抽取模块

负责从文档文本中抽取实体和关系，用于动态更新知识图谱
"""
import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from project.logger_handler import logger
from project.path_tool import get_abs_path

from agent.knowledge.health_kg import health_kg
from agent.knowledge.ner import health_ner
from agent.knowledge.entity_types import EntityType, HealthEntity, ENTITY_TYPE_DESC
from agent.knowledge.relation_types import RelationType, HealthRelation, RELATION_LABELS, RELATION_TYPE_DESC


@dataclass
class ExtractionResult:
    """抽取结果"""
    entities: List[Dict] = field(default_factory=list)
    relations: List[Dict] = field(default_factory=list)
    source_doc_id: str = ""
    source_chunk_index: int = 0
    extraction_time: str = ""

    def to_dict(self) -> Dict:
        return {
            "entities": self.entities,
            "relations": self.relations,
            "source_doc_id": self.source_doc_id,
            "source_chunk_index": self.source_chunk_index,
            "extraction_time": self.extraction_time
        }


class KGExtractor:
    """
    知识图谱抽取器

    功能：
    1. 使用NER识别已知实体
    2. 使用LLM抽取新实体和关系
    3. 合并去重，过滤已存在实体
    4. 返回待新增的实体和关系列表
    """

    def __init__(self):
        self.kg = health_kg
        self.ner = health_ner
        self._config = self._load_config()
        logger.info("[KGExtractor] 知识抽取器初始化完成")

    def _load_config(self) -> Dict:
        """加载配置"""
        config_path = get_abs_path("config/kg.yml")
        default_config = {
            "enable_llm_extraction": True,
            "min_chunk_length": 50,
            "max_chunks_to_extract": 10,
            "entity_confidence_threshold": 0.7,
            "enable_persistence": True,
            "persistence_file": "data/knowledge/kg_data.json",
            "auto_save_interval": 300,
            "sync_ner_dictionary": True,
            "add_kg_metadata": True
        }

        if os.path.exists(config_path):
            try:
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    yaml_config = yaml.safe_load(f) or {}
                    # 合并配置
                    for key in default_config:
                        if key in yaml_config.get("kg_extraction", {}):
                            default_config[key] = yaml_config["kg_extraction"][key]
                        elif key in yaml_config.get("kg_storage", {}):
                            default_config[key] = yaml_config["kg_storage"][key]
                        elif key in yaml_config.get("kg_sync", {}):
                            default_config[key] = yaml_config["kg_sync"][key]
                    logger.info(f"[KGExtractor] 加载配置成功")
            except Exception as e:
                logger.warning(f"[KGExtractor] 加载配置失败，使用默认配置: {e}")

        return default_config

    def extract_from_text(self, text: str, doc_id: str = "", chunk_index: int = 0) -> ExtractionResult:
        """
        从文本中抽取实体和关系

        Args:
            text: 输入文本
            doc_id: 文档ID
            chunk_index: chunk索引

        Returns:
            ExtractionResult 抽取结果
        """
        from datetime import datetime

        result = ExtractionResult(
            source_doc_id=doc_id,
            source_chunk_index=chunk_index,
            extraction_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        # 文本长度检查
        if len(text) < self._config.get("min_chunk_length", 50):
            logger.debug(f"[KGExtractor] 文本长度不足({len(text)}字符)，跳过抽取")
            return result

        # Step 1: 使用NER识别已知实体
        known_entities = self._extract_known_entities(text)

        # Step 2: 使用LLM抽取新实体和关系
        if self._config.get("enable_llm_extraction", True):
            llm_result = self._extract_with_llm(text, known_entities)
            result.entities = llm_result.get("entities", [])
            result.relations = llm_result.get("relations", [])
        else:
            # 仅使用NER结果
            result.entities = known_entities

        # Step 3: 过滤已存在的实体
        result.entities = self._filter_existing_entities(result.entities)

        logger.info(f"[KGExtractor] 抽取完成: 实体{len(result.entities)}个, 关系{len(result.relations)}个")
        return result

    def _extract_known_entities(self, text: str) -> List[Dict]:
        """使用NER识别已知实体"""
        entities = []
        try:
            # 使用NER识别
            ner_results = self.ner.recognize(text)
            for r in ner_results:
                if r["entity_type"] > 0 and r["entity_name"]:
                    entities.append({
                        "name": r["entity_name"],
                        "entity_type": r["entity_type"],
                        "entity_type_name": r.get("entity_type_name", ""),
                        "source": "ner",
                        "confidence": 1.0
                    })
            logger.debug(f"[KGExtractor] NER识别到{len(entities)}个已知实体")
        except Exception as e:
            logger.warning(f"[KGExtractor] NER识别失败: {e}")

        return entities

    def _extract_with_llm(self, text: str, known_entities: List[Dict]) -> Dict:
        """使用LLM抽取新实体和关系"""
        try:
            from model.factory import chat_model

            # 构建Prompt
            prompt = self._build_extraction_prompt(text, known_entities)

            # 调用LLM
            response = chat_model.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            # 解析结果
            result = self._parse_llm_response(content)
            logger.debug(f"[KGExtractor] LLM抽取结果: 实体{len(result.get('entities', []))}个, 关系{len(result.get('relations', []))}个")
            return result

        except Exception as e:
            logger.error(f"[KGExtractor] LLM抽取失败: {e}", exc_info=True)
            return {"entities": [], "relations": []}

    def _build_extraction_prompt(self, text: str, known_entities: List[Dict]) -> str:
        """构建抽取Prompt"""
        # 实体类型说明
        entity_types_desc = []
        for et in EntityType:
            desc = ENTITY_TYPE_DESC.get(et, {})
            examples = desc.get("examples", [])
            entity_types_desc.append(f"- {et.name}({et.value}): {desc.get('name', '')}。例如: {', '.join(examples[:3]) if examples else '无'}")

        # 关系类型说明
        relation_types_desc = []
        for rt in RelationType:
            desc = RELATION_TYPE_DESC.get(rt, {})
            relation_types_desc.append(f"- {desc.get('name', rt.name)}: {desc.get('description', '')}")

        # 已识别实体
        known_entities_str = ""
        if known_entities:
            known_entities_str = f"已识别的实体: {', '.join([e['name'] for e in known_entities])}"

        prompt = f"""请从以下健康领域文本中抽取实体和关系。请以JSON格式输出。

## 实体类型说明
{chr(10).join(entity_types_desc)}

## 关系类型说明
{chr(10).join(relation_types_desc)}

## 文本内容
{text}

{known_entities_str}

## 输出格式要求
请输出JSON格式，包含entities和relations两个数组：
```json
{{
    "entities": [
        {{"name": "实体名称", "entity_type": 类型数字, "entity_type_name": "类型名称", "description": "描述"}}
    ],
    "relations": [
        {{"entity1": "实体1", "relation": "关系名称", "entity2": "实体2"}}
    ]
}}
```

注意：
1. 只抽取与健康相关的实体（疾病、症状、药物、食物、营养素、运动、习惯等）
2. 关系的relation字段使用上面关系类型说明中的关系名称
3. 不要重复抽取已识别的实体
4. 确保抽取的实体和关系在文本中有明确的依据

请直接输出JSON，不要有其他解释文字。"""
        return prompt

    def _parse_llm_response(self, content: str) -> Dict:
        """解析LLM响应"""
        result = {"entities": [], "relations": []}

        try:
            # 提取JSON部分
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)

                # 处理实体
                for e in parsed.get("entities", []):
                    entity_type = e.get("entity_type", 0)
                    if isinstance(entity_type, str):
                        # 尝试转换类型名称到数字
                        entity_type = self._convert_entity_type_name(entity_type)
                    result["entities"].append({
                        "name": e.get("name", ""),
                        "entity_type": entity_type,
                        "entity_type_name": e.get("entity_type_name", ""),
                        "description": e.get("description", ""),
                        "source": "llm",
                        "confidence": 0.8
                    })

                # 处理关系
                for r in parsed.get("relations", []):
                    result["relations"].append({
                        "entity1": r.get("entity1", ""),
                        "relation": r.get("relation", ""),
                        "entity2": r.get("entity2", ""),
                        "source": "llm",
                        "confidence": 0.8
                    })

        except json.JSONDecodeError as e:
            logger.warning(f"[KGExtractor] JSON解析失败: {e}")
            # 尝试简单的实体提取
            result["entities"] = self._simple_entity_extraction(content)

        return result

    def _convert_entity_type_name(self, type_name: str) -> int:
        """转换实体类型名称到数字"""
        type_name_upper = type_name.upper()
        for et in EntityType:
            if et.name == type_name_upper:
                return et.value
        return EntityType.OTHER.value

    def _simple_entity_extraction(self, content: str) -> List[Dict]:
        """简单的实体提取（作为fallback）"""
        entities = []
        # 尝试匹配常见模式
        patterns = [
            r'"name":\s*"([^"]+)"',
            r'"entity":\s*"([^"]+)"',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for m in matches:
                if len(m) > 1 and m not in [e["name"] for e in entities]:
                    entities.append({
                        "name": m,
                        "entity_type": EntityType.OTHER.value,
                        "entity_type_name": "OTHER",
                        "source": "llm_fallback",
                        "confidence": 0.5
                    })
        return entities

    def _filter_existing_entities(self, entities: List[Dict]) -> List[Dict]:
        """过滤已存在的实体"""
        filtered = []
        for e in entities:
            name = e.get("name", "")
            if not name:
                continue
            # 检查是否已存在
            if not self.kg.get_entity(name):
                filtered.append(e)
        return filtered

    def extract_from_chunks(self, chunks: List[str], doc_id: str) -> List[ExtractionResult]:
        """
        从多个chunks中抽取

        Args:
            chunks: 文本chunks列表
            doc_id: 文档ID

        Returns:
            抽取结果列表
        """
        results = []
        max_chunks = self._config.get("max_chunks_to_extract", 10)

        for i, chunk in enumerate(chunks[:max_chunks]):
            result = self.extract_from_text(chunk, doc_id, i)
            if result.entities or result.relations:
                results.append(result)

        return results

    def merge_results(self, results: List[ExtractionResult]) -> ExtractionResult:
        """合并多个抽取结果"""
        from datetime import datetime

        merged = ExtractionResult(
            source_doc_id=results[0].source_doc_id if results else "",
            extraction_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        seen_entities: Set[str] = set()
        seen_relations: Set[str] = set()

        for r in results:
            for e in r.entities:
                name = e.get("name", "")
                if name and name not in seen_entities:
                    merged.entities.append(e)
                    seen_entities.add(name)

            for rel in r.relations:
                key = f"{rel.get('entity1', '')}-{rel.get('relation', '')}-{rel.get('entity2', '')}"
                if key not in seen_relations:
                    merged.relations.append(rel)
                    seen_relations.add(key)

        return merged


# 全局抽取器实例
kg_extractor = KGExtractor()