"""
健康领域命名实体识别 (NER)
使用分词 + 实体词典匹配的方式
"""
import re
from typing import Dict, List, Optional, Tuple
from project.logger_handler import logger

from agent.knowledge.health_kg import health_kg
from agent.knowledge.entity_types import EntityType, ENTITY_LABELS, ENTITY_TYPE_DESC, get_entity_type_desc


class HealthNER:
    """
    健康领域命名实体识别
    1. 分词处理
    2. 实体词典匹配
    3. 词性筛选
    4. 组合实体识别
    """

    def __init__(self):
        self.kg = health_kg
        self.entity_labels = ENTITY_LABELS
        # 尝试加载分词工具
        self._tokenizer = None
        self._init_tokenizer()
        logger.info("[HealthNER] 健康NER系统初始化完成")

    def _init_tokenizer(self):
        """初始化分词器"""
        try:
            import thulac
            self._tokenizer = thulac.thulac()
            self._tokenizer_type = "thulac"
            logger.info("[HealthNER] 使用 thulac 分词器")
        except ImportError:
            try:
                import jieba
                self._tokenizer = jieba
                self._tokenizer_type = "jieba"
                logger.info("[HealthNER] 使用 jieba 分词器")
            except ImportError:
                self._tokenizer_type = "simple"
                logger.info("[HealthNER] 使用简单分词器（按空格/标点分割）")

    def tokenize(self, text: str) -> List[Tuple[str, str]]:
        """
        分词

        Returns:
            [(word, pos_tag), ...]
        """
        if self._tokenizer_type == "thulac":
            return self._tokenizer.cut(text, text=False)
        elif self._tokenizer_type == "jieba":
            import jieba.posseg as pseg
            return [(w.word, w.flag) for w in pseg.cut(text)]
        else:
            # 简单分词
            words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+|\d+', text)
            return [(w, self._guess_pos(w)) for w in words]

    def _guess_pos(self, word: str) -> str:
        """猜测词性"""
        if re.match(r'\d+', word):
            return 'm'  # 数字
        if re.match(r'[a-zA-Z]+', word):
            return 'nz'  # 其他
        if len(word) <= 1:
            return 'x'  # 单字
        return 'n'  # 默认名词

    def recognize(self, text: str) -> List[Dict]:
        """
        识别文本中的健康实体

        Args:
            text: 输入文本

        Returns:
            [{"word": word, "entity_type": type_id, "entity_name": name, "desc": desc}, ...]
        """
        logger.debug(f"[HealthNER] 输入文本: {text}")

        # 分词
        tokens = self.tokenize(text)
        tokens.append(('===', None))  # 添加结束标记

        results = []
        i = 0
        length = len(tokens) - 1

        while i < length:
            p1, t1 = tokens[i]
            p2, t2 = tokens[i + 1] if i + 1 < length else ('', '')
            p12 = p1 + p2

            # 尝试组合词匹配
            if self._is_valid_pos(t1, 'pre') and self._is_valid_pos(t2, 'now'):
                entity12 = self.kg.match_entity(p12)
                if entity12 and p12 in self.entity_labels:
                    results.append(self._make_entity_result(p12, self.entity_labels[p12]))
                    i += 2
                    continue

            # 单词匹配
            entity1 = self.kg.match_entity(p1)
            if entity1 and p1 in self.entity_labels:
                if self._is_valid_pos(t1, 'now'):
                    results.append(self._make_entity_result(p1, self.entity_labels[p1]))
                    i += 1
                    continue

            # 检查是否可能是实体（词性判断）
            if self._is_temporary_entity(t1):
                results.append({"word": p1, "entity_type": 0, "entity_name": None, "desc": "待确认实体"})
                i += 1
                continue

            results.append({"word": p1, "entity_type": 0, "entity_name": None, "desc": "非实体"})
            i += 1

        logger.debug(f"[HealthNER] 识别结果: {results}")
        return results

    def _is_valid_pos(self, pos: str, position: str) -> bool:
        """
        词性筛选

        参考 Agriculture_KnowledgeGraph 的 preok/nowok 函数
        """
        valid_pos = ['n', 'np', 'ns', 'ni', 'nz', 'v', 'a', 'i', 'j', 'x', 'id', 'g', 'u', 't', 'm']
        return pos in valid_pos if pos else False

    def _is_temporary_entity(self, pos: str) -> bool:
        """
        判断是否可能是实体（词性判断）
        """
        temp_pos = ['np', 'ns', 'ni', 'nz', 'j', 'x', 't']
        return pos in temp_pos if pos else False

    def _make_entity_result(self, word: str, entity_type: int) -> Dict:
        """构建实体识别结果"""
        entity_name = self.kg.match_entity(word)
        desc = get_entity_type_desc(EntityType(entity_type)) if entity_type else {}

        return {
            "word": word,
            "entity_type": entity_type,
            "entity_name": entity_name,
            "entity_type_name": EntityType(entity_type).name if entity_type else "未知",
            "desc": desc.get("name", ""),
            "description": desc.get("description", "")
        }

    def extract_entities(self, text: str) -> List[Tuple[str, int]]:
        """
        提取文本中的实体

        Returns:
            [(entity_name, entity_type), ...]
        """
        results = self.recognize(text)
        return [(r["entity_name"], r["entity_type"])
                for r in results if r["entity_type"] > 0 and r["entity_name"]]

    def get_entities_text(self, text: str) -> List[str]:
        """获取文本中的实体名称列表"""
        entities = self.extract_entities(text)
        return [e[0] for e in entities]

    def annotate_text(self, text: str) -> str:
        """
        标注文本中的实体

        Returns:
            标注后的文本，实体用 [实体名/类型] 标记
        """
        results = self.recognize(text)
        annotated = []
        for r in results:
            if r["entity_type"] > 0:
                annotated.append(f"[{r['entity_name']}/{r['entity_type_name']}]")
            else:
                annotated.append(r["word"])
        return "".join(annotated)


# 全局NER实例
health_ner = HealthNER()


def update_entity_labels(new_entities: List[Tuple[str, int]]) -> Dict:
    """
    动态更新实体词典

    Args:
        new_entities: [(实体名称, 实体类型ID), ...]

    Returns:
        {"added": 新增数量, "updated": 更新数量}
    """
    global ENTITY_LABELS

    added = 0
    updated = 0

    for name, type_id in new_entities:
        if name and type_id > 0:
            if name not in ENTITY_LABELS:
                ENTITY_LABELS[name] = type_id
                added += 1
            else:
                ENTITY_LABELS[name] = type_id
                updated += 1

    logger.info(f"[HealthNER] 词典更新: 新增{added}个, 更新{updated}个")
    return {"added": added, "updated": updated}


def refresh_entity_labels() -> Dict:
    """
    从知识图谱刷新全部词典

    Returns:
        {"total": 总数量}
    """
    global ENTITY_LABELS, health_ner

    # 重置为预定义实体
    from agent.knowledge.entity_types import PREDEFINED_ENTITIES
    ENTITY_LABELS.clear()
    ENTITY_LABELS = {e.name: e.entity_type.value for e in PREDEFINED_ENTITIES}
    for e in PREDEFINED_ENTITIES:
        for syn in e.synonyms:
            ENTITY_LABELS[syn] = e.entity_type.value

    # 从 Neo4j 后端获取所有实体
    from agent.knowledge.health_kg import health_kg
    entity_map = health_kg.get_all_entity_names_and_types()
    for name, type_id in entity_map.items():
        ENTITY_LABELS[name] = type_id

    # 更新NER实例的词典引用
    health_ner.entity_labels = ENTITY_LABELS

    logger.info(f"[HealthNER] 词典刷新完成，总计{len(ENTITY_LABELS)}个实体")
    return {"total": len(ENTITY_LABELS)}


def sync_ner_dictionary() -> Dict:
    """
    同步NER词典与知识图谱

    Returns:
        {"synced": 同步数量, "total": 总数量}
    """
    global ENTITY_LABELS, health_ner

    # 重置为预定义实体
    from agent.knowledge.entity_types import PREDEFINED_ENTITIES
    ENTITY_LABELS.clear()
    ENTITY_LABELS = {e.name: e.entity_type.value for e in PREDEFINED_ENTITIES}
    for e in PREDEFINED_ENTITIES:
        for syn in e.synonyms:
            ENTITY_LABELS[syn] = e.entity_type.value

    # 添加扩展实体
    try:
        from agent.knowledge.kg_extended_data import EXTENDED_ENTITIES, EXTENDED_ENTITY_LABELS
        for name, type_id in EXTENDED_ENTITY_LABELS.items():
            ENTITY_LABELS[name] = type_id
    except ImportError:
        pass

    # 从 Neo4j 后端获取所有实体
    from agent.knowledge.health_kg import health_kg
    entity_map = health_kg.get_all_entity_names_and_types()
    for name, type_id in entity_map.items():
        ENTITY_LABELS[name] = type_id

    # 更新NER实例的词典引用
    health_ner.entity_labels = ENTITY_LABELS

    logger.info(f"[HealthNER] 词典刷新完成，总计{len(ENTITY_LABELS)}个实体")
    return {"synced": len(ENTITY_LABELS), "total": len(ENTITY_LABELS)}
