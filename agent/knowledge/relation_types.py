"""
健康知识图谱关系类型定义
"""
from dataclasses import dataclass, field
from typing import Dict, List
from enum import IntEnum


class RelationType(IntEnum):
    """健康实体关系类型枚举"""
    # 疾病相关关系
    HAS_SYMPTOM = 1      # 疾病-症状: 疾病具有症状
    CAUSES = 2           # 因果: A导致B
    CAUSED_BY = 3        # 因果: A由B导致
    RISK_OF = 4          # 风险: A是B的风险因素
    PREVENTS = 5         # 预防: A可预防B
    DIAGNOSED_BY = 6     # 诊断: 疾病通过检查诊断

    # 治疗相关关系
    TREATS = 7           # 治疗: A治疗B
    TREATED_BY = 8       # 治疗: A由B治疗
    DRUG_FOR = 9         # 药物: 药物用于治疗
    SIDE_EFFECT = 10     # 副作用: 药物的副作用

    # 人体相关关系
    LOCATED_IN = 11      # 位置: A位于B
    AFFECTS = 12         # 影响: A影响B
    RELATED_TO = 13      # 相关: A与B相关

    # 营养相关关系
    CONTAINS = 14        # 含有: 食物含有营养素
    GOOD_FOR = 15        # 有益: A对B有益
    BAD_FOR = 16         # 不利: A对B不利
    RICH_IN = 17         # 富含: 食物富含营养素
    LOW_IN = 18          # 低含量: 食物低含量

    # 运动相关关系
    SUITABLE_FOR = 19    # 适合: 运动适合某目标/人群
    HELPS_WITH = 20      # 帮助: 运动帮助改善某状况
    REQUIRES = 21        # 需要: 运动需要某条件

    # 生活方式关系
    LEADS_TO = 22        # 导致: 习惯导致结果
    IMPROVES = 23        # 改善: A改善B
    WORSENS = 24         # 加重: A加重B
    RECOMMENDED_FOR = 25 # 推荐: A推荐用于B

    # 分类关系
    IS_A = 26            # 是: A是B的一种
    SUBTYPE_OF = 27      # 子类: A是B的子类
    PART_OF = 28         # 部分: A是B的一部分

    # 其他关系
    ASSOCIATED_WITH = 29 # 关联: A与B关联
    INCREASES = 30       # 增加: A增加B
    DECREASES = 31       # 减少: A减少B


@dataclass
class HealthRelation:
    """健康实体关系"""
    entity1: str
    entity1_type: int
    relation: str
    entity2: str
    entity2_type: int
    confidence: float = 1.0
    source: str = ""
    attributes: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "entity1": self.entity1,
            "entity1_type": self.entity1_type,
            "relation": self.relation,
            "entity2": self.entity2,
            "entity2_type": self.entity2_type,
            "confidence": self.confidence,
            "source": self.source,
            "attributes": self.attributes
        }


# 关系类型详细描述
RELATION_TYPE_DESC = {
    RelationType.HAS_SYMPTOM: {
        "name": "具有症状",
        "description": "疾病具有的症状表现",
        "example": "高血压-具有症状-头晕",
        "reverse": "SYMPTOM_OF"
    },
    RelationType.CAUSES: {
        "name": "导致",
        "description": "A导致B发生",
        "example": "熬夜-导致-失眠",
        "reverse": "CAUSED_BY"
    },
    RelationType.CAUSED_BY: {
        "name": "由...导致",
        "description": "A由B导致",
        "example": "失眠-由...导致-熬夜",
        "reverse": "CAUSES"
    },
    RelationType.RISK_OF: {
        "name": "风险因素",
        "description": "A是B的风险因素",
        "example": "高盐饮食-风险因素-高血压",
        "reverse": "HAS_RISK_FACTOR"
    },
    RelationType.PREVENTS: {
        "name": "预防",
        "description": "A可预防B",
        "example": "规律运动-预防-肥胖",
        "reverse": "PREVENTED_BY"
    },
    RelationType.DIAGNOSED_BY: {
        "name": "诊断方式",
        "description": "疾病通过何种检查诊断",
        "example": "高血压-诊断方式-血压测量",
        "reverse": "DIAGNOSES"
    },
    RelationType.TREATS: {
        "name": "治疗",
        "description": "A治疗B",
        "example": "降压药-治疗-高血压",
        "reverse": "TREATED_BY"
    },
    RelationType.TREATED_BY: {
        "name": "治疗方式",
        "description": "A由B治疗",
        "example": "高血压-治疗方式-降压药",
        "reverse": "TREATS"
    },
    RelationType.DRUG_FOR: {
        "name": "药物用途",
        "description": "药物用于治疗疾病",
        "example": "胰岛素-药物用途-糖尿病",
        "reverse": "TREATED_WITH"
    },
    RelationType.SIDE_EFFECT: {
        "name": "副作用",
        "description": "药物的副作用",
        "example": "阿司匹林-副作用-胃部不适",
        "reverse": "IS_SIDE_EFFECT_OF"
    },
    RelationType.LOCATED_IN: {
        "name": "位于",
        "description": "A位于B位置",
        "example": "心脏-位于-胸腔",
        "reverse": "CONTAINS"
    },
    RelationType.AFFECTS: {
        "name": "影响",
        "description": "A影响B",
        "example": "高血压-影响-心脏",
        "reverse": "AFFECTED_BY"
    },
    RelationType.RELATED_TO: {
        "name": "相关",
        "description": "A与B相关",
        "example": "肥胖-相关-糖尿病",
        "reverse": "RELATED_TO"
    },
    RelationType.CONTAINS: {
        "name": "含有",
        "description": "食物含有营养素",
        "example": "鸡胸肉-含有-蛋白质",
        "reverse": "FOUND_IN"
    },
    RelationType.GOOD_FOR: {
        "name": "有益于",
        "description": "A对B有益",
        "example": "运动-有益于-心脏健康",
        "reverse": "BENEFITS_FROM"
    },
    RelationType.BAD_FOR: {
        "name": "不利于",
        "description": "A对B不利",
        "example": "高盐饮食-不利于-高血压患者",
        "reverse": "HARMED_BY"
    },
    RelationType.RICH_IN: {
        "name": "富含",
        "description": "食物富含营养素",
        "example": "菠菜-富含-铁",
        "reverse": "ABUNDANT_IN"
    },
    RelationType.SUITABLE_FOR: {
        "name": "适合",
        "description": "运动适合某目标/人群",
        "example": "瑜伽-适合-减压放松",
        "reverse": "CAN_DO"
    },
    RelationType.HELPS_WITH: {
        "name": "帮助改善",
        "description": "A帮助改善B",
        "example": "运动-帮助改善-失眠",
        "reverse": "IMPROVED_BY"
    },
    RelationType.LEADS_TO: {
        "name": "导致",
        "description": "习惯导致结果",
        "example": "缺乏运动-导致-肥胖",
        "reverse": "RESULT_OF"
    },
    RelationType.IMPROVES: {
        "name": "改善",
        "description": "A改善B",
        "example": "规律作息-改善-睡眠",
        "reverse": "IMPROVED_BY"
    },
    RelationType.WORSENS: {
        "name": "加重",
        "description": "A加重B",
        "example": "熬夜-加重-高血压",
        "reverse": "WORSENED_BY"
    },
    RelationType.IS_A: {
        "name": "是",
        "description": "A是B的一种",
        "example": "感冒-是-上呼吸道感染",
        "reverse": "HAS_SUBTYPE"
    },
}


def get_relation_desc(relation_type: RelationType) -> Dict:
    """获取关系类型描述"""
    return RELATION_TYPE_DESC.get(relation_type, {"name": "未知关系", "description": ""})


# 预定义的健康关系三元组（用于初始化知识图谱）
PREDEFINED_RELATIONS = [
    # 疾病-症状关系
    HealthRelation("高血压", 3, "具有症状", "头晕", 2),
    HealthRelation("高血压", 3, "具有症状", "心悸", 2),
    HealthRelation("高血压", 3, "具有症状", "胸闷", 2),
    HealthRelation("糖尿病", 3, "具有症状", "乏力", 2),
    HealthRelation("糖尿病", 3, "具有症状", "食欲不振", 2),
    HealthRelation("感冒", 3, "具有症状", "发热", 2),
    HealthRelation("感冒", 3, "具有症状", "咳嗽", 2),
    HealthRelation("感冒", 3, "具有症状", "头痛", 2),
    HealthRelation("胃炎", 3, "具有症状", "恶心", 2),
    HealthRelation("胃炎", 3, "具有症状", "食欲不振", 2),
    HealthRelation("失眠症", 3, "具有症状", "失眠", 2),
    HealthRelation("失眠症", 3, "具有症状", "乏力", 2),
    HealthRelation("贫血", 3, "具有症状", "乏力", 2),
    HealthRelation("贫血", 3, "具有症状", "头晕", 2),

    # 疾病-风险因素关系
    HealthRelation("高血压", 3, "风险因素", "高盐饮食", 13),
    HealthRelation("高血压", 3, "风险因素", "缺乏运动", 13),
    HealthRelation("高血压", 3, "风险因素", "肥胖", 3),
    HealthRelation("糖尿病", 3, "风险因素", "肥胖", 3),
    HealthRelation("糖尿病", 3, "风险因素", "缺乏运动", 13),
    HealthRelation("冠心病", 3, "风险因素", "高血压", 3),
    HealthRelation("冠心病", 3, "风险因素", "高血脂", 3),
    HealthRelation("肥胖", 3, "风险因素", "缺乏运动", 13),
    HealthRelation("肥胖", 3, "风险因素", "饮食不规律", 13),

    # 疾病-治疗关系
    HealthRelation("高血压", 3, "治疗方式", "降压药", 4),
    HealthRelation("高血压", 3, "治疗方式", "低盐饮食", 9),
    HealthRelation("糖尿病", 3, "治疗方式", "胰岛素", 4),
    HealthRelation("糖尿病", 3, "治疗方式", "降糖药", 4),
    HealthRelation("糖尿病", 3, "治疗方式", "低糖饮食", 9),
    HealthRelation("感冒", 3, "治疗方式", "休息", 5),
    HealthRelation("胃炎", 3, "治疗方式", "饮食调理", 5),
    HealthRelation("失眠症", 3, "治疗方式", "规律作息", 12),
    HealthRelation("失眠症", 3, "治疗方式", "冥想", 10),

    # 药物-疾病关系
    HealthRelation("降压药", 4, "药物用途", "高血压", 3),
    HealthRelation("胰岛素", 4, "药物用途", "糖尿病", 3),
    HealthRelation("降糖药", 4, "药物用途", "糖尿病", 3),
    HealthRelation("阿司匹林", 4, "药物用途", "感冒", 3),
    HealthRelation("维生素", 4, "药物用途", "贫血", 3),

    # 食物-营养素关系
    HealthRelation("鸡胸肉", 7, "含有", "蛋白质", 8),
    HealthRelation("牛奶", 7, "含有", "蛋白质", 8),
    HealthRelation("牛奶", 7, "含有", "钙", 8),
    HealthRelation("鸡蛋", 7, "含有", "蛋白质", 8),
    HealthRelation("菠菜", 7, "富含", "铁", 8),
    HealthRelation("西兰花", 7, "含有", "膳食纤维", 8),
    HealthRelation("三文鱼", 7, "富含", "Omega-3", 8),
    HealthRelation("苹果", 7, "含有", "维生素C", 8),
    HealthRelation("燕麦", 7, "富含", "膳食纤维", 8),
    HealthRelation("豆腐", 7, "含有", "蛋白质", 8),

    # 食物-疾病关系（有益/不利）
    HealthRelation("低盐饮食", 9, "有益于", "高血压", 3),
    HealthRelation("低糖饮食", 9, "有益于", "糖尿病", 3),
    HealthRelation("高盐饮食", 13, "不利于", "高血压", 3),
    HealthRelation("高蛋白饮食", 9, "有益于", "增肌塑形", 14),

    # 运动-健康目标关系
    HealthRelation("跑步", 10, "适合", "减脂瘦身", 14),
    HealthRelation("游泳", 10, "适合", "减脂瘦身", 14),
    HealthRelation("力量训练", 10, "适合", "增肌塑形", 14),
    HealthRelation("瑜伽", 10, "适合", "减压放松", 14),
    HealthRelation("太极拳", 10, "适合", "保持健康", 14),
    HealthRelation("快走", 10, "适合", "保持健康", 14),
    HealthRelation("冥想", 10, "适合", "减压放松", 14),

    # 运动-疾病关系
    HealthRelation("运动", 10, "预防", "肥胖", 3),
    HealthRelation("运动", 10, "预防", "糖尿病", 3),
    HealthRelation("运动", 10, "帮助改善", "失眠", 2),
    HealthRelation("运动", 10, "有益于", "心脏", 1),

    # 习惯-结果关系
    HealthRelation("熬夜", 13, "导致", "失眠", 2),
    HealthRelation("熬夜", 13, "加重", "高血压", 3),
    HealthRelation("缺乏运动", 13, "导致", "肥胖", 3),
    HealthRelation("缺乏运动", 13, "风险因素", "冠心病", 3),
    HealthRelation("规律作息", 12, "改善", "睡眠", 15),
    HealthRelation("吸烟", 13, "风险因素", "冠心病", 3),
    HealthRelation("饮酒过量", 13, "影响", "肝脏", 1),

    # 人体部位关系
    HealthRelation("高血压", 3, "影响", "心脏", 1),
    HealthRelation("高血压", 3, "影响", "血管", 1),
    HealthRelation("糖尿病", 3, "影响", "血管", 1),
    HealthRelation("肝炎", 3, "影响", "肝脏", 1),
]

# 关系名称到类型映射
RELATION_LABELS = {
    "具有症状": RelationType.HAS_SYMPTOM.value,
    "症状": RelationType.HAS_SYMPTOM.value,
    "导致": RelationType.CAUSES.value,
    "由...导致": RelationType.CAUSED_BY.value,
    "风险因素": RelationType.RISK_OF.value,
    "预防": RelationType.PREVENTS.value,
    "治疗方式": RelationType.TREATED_BY.value,
    "治疗": RelationType.TREATS.value,
    "药物用途": RelationType.DRUG_FOR.value,
    "含有": RelationType.CONTAINS.value,
    "富含": RelationType.RICH_IN.value,
    "有益于": RelationType.GOOD_FOR.value,
    "不利于": RelationType.BAD_FOR.value,
    "适合": RelationType.SUITABLE_FOR.value,
    "帮助改善": RelationType.HELPS_WITH.value,
    "改善": RelationType.IMPROVES.value,
    "加重": RelationType.WORSENS.value,
    "影响": RelationType.AFFECTS.value,
    "是": RelationType.IS_A.value,
}