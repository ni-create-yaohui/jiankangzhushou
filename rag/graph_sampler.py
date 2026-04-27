"""
知识图谱采样器
基于种子节点对 KG 进行 BFS 邻域采样，返回结构化子图并转换为文本描述
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from collections import defaultdict, deque

from agent.knowledge.health_kg import health_kg
from agent.knowledge.entity_types import EntityType, ENTITY_TYPE_DESC
from project.logger_handler import logger


@dataclass
class SampledSubgraph:
    """采样结果"""
    seed_nodes: List[str]                    # 种子节点
    nodes: List[Dict] = field(default_factory=list)   # 所有节点 [{name, entity_type, attributes}]
    edges: List[Dict] = field(default_factory=list)   # 所有边 [{source, relation, target}]
    text: str = ""                           # 子图转换的文本描述


# 关系类型优先级（数值越高优先级越高）
RELATION_PRIORITY = {
    "具有症状": 10, "治疗方式": 9, "药物": 8, "风险因素": 7,
    "含有": 6, "富含": 6, "适合": 5, "不适合": 5,
    "导致": 4, "影响": 4, "改善": 4, "加重": 4,
    "推荐": 3, "有助于": 3, "预防": 3,
}

# 默认优先级
_DEFAULT_PRIORITY = 1


class GraphSampler:
    """知识图谱采样器"""

    def __init__(self):
        self.kg = health_kg

    def sample(
        self,
        seed_nodes: List[str],
        max_hops: int = 2,
        max_nodes: int = 30,
        max_edges: int = 50,
    ) -> SampledSubgraph:
        """
        从种子节点出发进行 BFS 邻域采样

        Args:
            seed_nodes: 种子节点名称列表
            max_hops: 最大跳数（默认2跳）
            max_nodes: 最大节点数
            max_edges: 最大边数

        Returns:
            SampledSubgraph 采样结果
        """
        # 过滤有效种子节点（存在于KG中的）
        valid_seeds = []
        for name in seed_nodes:
            node = self.kg.get_entity(name)
            if node:
                valid_seeds.append(node.name)  # 使用规范名称（同义词映射后）

        if not valid_seeds:
            logger.debug("[GraphSampler] 无有效种子节点")
            return SampledSubgraph(seed_nodes=seed_nodes)

        # BFS采样
        nodes, edges = self._bfs_sample(valid_seeds, max_hops, max_nodes)

        # 关系类型过滤（按优先级排序，保留高信息量边）
        edges = self._relation_priority_filter(edges, max_edges)

        # 过滤掉孤立节点（无边的节点，但保留种子节点）
        connected_nodes = set()
        for e in edges:
            connected_nodes.add(e["source"])
            connected_nodes.add(e["target"])
        connected_nodes.update(valid_seeds)
        nodes = [n for n in nodes if n["name"] in connected_nodes]

        # 转文本
        text = self._subgraph_to_text(nodes, edges)

        result = SampledSubgraph(
            seed_nodes=valid_seeds,
            nodes=nodes,
            edges=edges,
            text=text,
        )
        logger.info(
            f"[GraphSampler] 采样完成: 种子={valid_seeds}, "
            f"节点={len(nodes)}, 边={len(edges)}"
        )
        return result

    def _bfs_sample(
        self,
        seed_nodes: List[str],
        max_hops: int,
        max_nodes: int,
    ) -> tuple:
        """
        BFS邻域采样

        Returns:
            (nodes_list, edges_list)
        """
        visited_nodes: Set[str] = set()
        nodes_data: List[Dict] = []
        edges_data: List[Dict] = []
        queue = deque()

        # 初始化队列：(节点名, 当前跳数)
        for seed in seed_nodes:
            if seed not in visited_nodes:
                queue.append((seed, 0))
                visited_nodes.add(seed)
                node_info = self._get_node_info(seed)
                if node_info:
                    nodes_data.append(node_info)

        while queue and len(nodes_data) < max_nodes:
            current, hop = queue.popleft()

            if hop >= max_hops:
                continue

            # 获取当前节点的所有关系
            relations = self.kg.get_entity_relations(current)

            for rel in relations:
                # 获取对端实体
                neighbor = rel["entity2"] if rel["direction"] == "out" else rel["entity1"]

                # 添加边
                edge = {
                    "source": rel["entity1"],
                    "relation": rel["relation"],
                    "target": rel["entity2"],
                }
                edges_data.append(edge)

                # BFS扩展邻居
                if neighbor not in visited_nodes and len(nodes_data) < max_nodes:
                    visited_nodes.add(neighbor)
                    queue.append((neighbor, hop + 1))
                    node_info = self._get_node_info(neighbor)
                    if node_info:
                        nodes_data.append(node_info)

        return nodes_data, edges_data

    def _get_node_info(self, name: str) -> Optional[Dict]:
        """获取节点信息"""
        node = self.kg.get_entity(name)
        if not node:
            return None
        type_desc = ENTITY_TYPE_DESC.get(EntityType(node.entity_type), {})
        return {
            "name": node.name,
            "entity_type": node.entity_type,
            "entity_type_name": type_desc.get("name", EntityType(node.entity_type).name),
            "attributes": node.attributes,
        }

    def _relation_priority_filter(
        self,
        edges: List[Dict],
        max_edges: int,
    ) -> List[Dict]:
        """
        按关系类型优先级过滤和排序边

        高优先级的关系（如症状、治疗）排在前面
        """
        if len(edges) <= max_edges:
            return edges

        # 按优先级排序
        def edge_priority(e):
            return RELATION_PRIORITY.get(e["relation"], _DEFAULT_PRIORITY)

        sorted_edges = sorted(edges, key=edge_priority, reverse=True)
        return sorted_edges[:max_edges]

    def _subgraph_to_text(
        self,
        nodes: List[Dict],
        edges: List[Dict],
    ) -> str:
        """
        将子图转换为自然语言文本描述

        按关系类型分组，使用模板生成可读文本
        """
        if not edges:
            return ""

        # 按关系类型分组
        relation_groups: Dict[str, List[Dict]] = defaultdict(list)
        for edge in edges:
            relation_groups[edge["relation"]].append(edge)

        # 构建节点类型查找表
        node_types: Dict[str, Dict] = {n["name"]: n for n in nodes}

        text_parts = []

        for relation, group_edges in relation_groups.items():
            # 按 source 分组，合并相同实体相同关系的 target
            source_targets: Dict[str, List[str]] = defaultdict(list)
            for edge in group_edges:
                source_targets[edge["source"]].append(edge["target"])

            for source, targets in source_targets.items():
                source_info = node_types.get(source, {})
                source_type_name = source_info.get("entity_type_name", "实体")

                # 获取 target 的类型名
                target_names = []
                for t in targets:
                    t_info = node_types.get(t, {})
                    t_type = t_info.get("entity_type_name", "")
                    target_names.append(t)

                targets_str = "、".join(target_names)

                # 根据关系类型生成描述
                desc = self._generate_relation_text(
                    source, source_type_name, relation, targets_str, targets, node_types
                )
                if desc:
                    text_parts.append(desc)

        # 添加实体属性信息
        attribute_texts = self._generate_attribute_texts(nodes)
        if attribute_texts:
            text_parts.append(attribute_texts)

        return "\n".join(text_parts)

    def _generate_relation_text(
        self,
        source: str,
        source_type: str,
        relation: str,
        targets_str: str,
        targets: List[str],
        node_types: Dict[str, Dict],
    ) -> str:
        """根据关系类型生成自然语言描述"""
        templates = {
            "具有症状": f"{source}的症状包括{targets_str}。",
            "治疗方式": f"{source}的治疗方式包括{targets_str}。",
            "药物": f"{source}可使用的药物有{targets_str}。",
            "风险因素": f"{source}的风险因素包括{targets_str}。",
            "含有": f"{source}含有{targets_str}。",
            "富含": f"{source}富含{targets_str}。",
            "适合": f"{targets_str}适合{source}。",
            "不适合": f"{targets_str}不适合{source}。",
            "导致": f"{source}可能导致{targets_str}。",
            "影响": f"{source}会影响{targets_str}。",
            "改善": f"{source}可以改善{targets_str}。",
            "加重": f"{source}可能加重{targets_str}。",
            "推荐": f"对于{source}，推荐{targets_str}。",
            "有助于": f"{targets_str}有助于{source}。",
            "预防": f"{source}可以预防{targets_str}。",
            "位于": f"{source}位于{targets_str}。",
            "需要": f"{source}需要进行{targets_str}。",
            "属于": f"{source}属于{targets_str}。",
        }

        template = templates.get(relation)
        if template:
            return template

        # 默认模板
        return f"{source}{relation}{targets_str}。"

    def _generate_attribute_texts(self, nodes: List[Dict]) -> str:
        """生成实体属性描述文本"""
        parts = []

        for node in nodes:
            attrs = node.get("attributes", {})
            if not attrs:
                continue

            name = node["name"]
            type_name = node.get("entity_type_name", "")
            attr_parts = []

            # 常见属性字段映射
            attr_map = {
                "热量": "热量",
                "calories": "热量",
                "热量单位": "",
                "蛋白质": "蛋白质",
                "protein": "蛋白质",
                "脂肪": "脂肪",
                "fat": "脂肪",
                "碳水化合物": "碳水化合物",
                "carbs": "碳水化合物",
                "单位": "",
                "amount": "",
                "description": "",
                "别名": "",
                "source": "",
                "source_doc_id": "",
            }

            readable_attrs = []
            for key, value in attrs.items():
                label = attr_map.get(key)
                if label is None and key not in attr_map:
                    # 未知属性但可能是有效信息
                    readable_attrs.append(f"{key}{value}")
                elif label:
                    readable_attrs.append(f"{label}为{value}")

            if readable_attrs:
                attr_str = "，".join(readable_attrs[:5])  # 最多5个属性
                parts.append(f"{name}({type_name})：{attr_str}。")

        return "\n".join(parts)
