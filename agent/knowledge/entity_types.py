"""
健康知识图谱实体类型定义
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import IntEnum


class EntityType(IntEnum):
    """健康实体类型枚举"""
    # 人体相关
    BODY_PART = 1        # 人体部位/器官
    SYMPTOM = 2          # 症状
    DISEASE = 3          # 疾病

    # 医疗相关
    DRUG = 4             # 药物
    TREATMENT = 5        # 治疗方法
    MEDICAL_TEST = 6     # 医学检查

    # 营养相关
    FOOD = 7             # 食物
    NUTRIENT = 8         # 营养素
    DIET_TYPE = 9        # 饮食类型

    # 运动相关
    EXERCISE = 10        # 运动/运动方式
    FITNESS_LEVEL = 11   # 运动水平

    # 生活方式
    HABIT = 12           # 生活习惯
    RISK_FACTOR = 13     # 危险因素

    # 其他
    HEALTH_GOAL = 14     # 健康目标
    HEALTH_TERM = 15     # 健康术语
    OTHER = 16           # 其他实体


@dataclass
class HealthEntity:
    """健康实体"""
    name: str
    entity_type: EntityType
    description: str = ""
    attributes: Dict = field(default_factory=dict)
    synonyms: List[str] = field(default_factory=list)
    source: str = ""

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "entity_type": self.entity_type.value,
            "entity_type_name": self.entity_type.name,
            "description": self.description,
            "attributes": self.attributes,
            "synonyms": self.synonyms,
            "source": self.source
        }


# 实体类型详细描述
ENTITY_TYPE_DESC = {
    EntityType.BODY_PART: {
        "name": "人体部位",
        "description": "包括人体各部位、器官、组织等",
        "examples": ["心脏", "肝脏", "肺部", "胃", "肾脏", "大脑", "血管"]
    },
    EntityType.SYMPTOM: {
        "name": "症状",
        "description": "包括各种身体不适、异常表现",
        "examples": ["头痛", "发热", "咳嗽", "失眠", "乏力", "恶心", "头晕"]
    },
    EntityType.DISEASE: {
        "name": "疾病",
        "description": "包括各种疾病名称、病理状态",
        "examples": ["高血压", "糖尿病", "感冒", "胃炎", "冠心病", "肥胖症"]
    },
    EntityType.DRUG: {
        "name": "药物",
        "description": "包括各类药物、药品名称",
        "examples": ["阿司匹林", "降压药", "胰岛素", "抗生素", "维生素"]
    },
    EntityType.TREATMENT: {
        "name": "治疗方法",
        "description": "包括医疗手段、治疗方式",
        "examples": ["手术", "药物治疗", "物理治疗", "中医治疗", "针灸"]
    },
    EntityType.MEDICAL_TEST: {
        "name": "医学检查",
        "description": "包括各种体检、检验项目",
        "examples": ["血压测量", "血糖检测", "心电图", "血常规", "CT检查"]
    },
    EntityType.FOOD: {
        "name": "食物",
        "description": "包括各类食物、食材",
        "examples": ["米饭", "鸡胸肉", "西兰花", "牛奶", "苹果", "三文鱼"]
    },
    EntityType.NUTRIENT: {
        "name": "营养素",
        "description": "包括蛋白质、维生素、矿物质等",
        "examples": ["蛋白质", "维生素C", "钙", "铁", "膳食纤维"]
    },
    EntityType.DIET_TYPE: {
        "name": "饮食类型",
        "description": "包括各种饮食模式、饮食习惯",
        "examples": ["低盐饮食", "低糖饮食", "高蛋白饮食", "素食"]
    },
    EntityType.EXERCISE: {
        "name": "运动",
        "description": "包括各种运动方式、锻炼项目",
        "examples": ["跑步", "游泳", "瑜伽", "深蹲", "快走", "力量训练"]
    },
    EntityType.FITNESS_LEVEL: {
        "name": "运动水平",
        "description": "包括运动强度等级",
        "examples": ["初学者", "中级", "高级", "久坐不动", "中度活动"]
    },
    EntityType.HABIT: {
        "name": "生活习惯",
        "description": "包括各种生活方式、习惯",
        "examples": ["熬夜", "吸烟", "饮酒", "规律作息", "早睡早起"]
    },
    EntityType.RISK_FACTOR: {
        "name": "危险因素",
        "description": "包括各种健康风险因素",
        "examples": ["高盐饮食", "缺乏运动", "肥胖", "高血压家族史"]
    },
    EntityType.HEALTH_GOAL: {
        "name": "健康目标",
        "description": "包括各种健康目标",
        "examples": ["减脂瘦身", "增肌塑形", "保持健康", "控制血糖"]
    },
    EntityType.HEALTH_TERM: {
        "name": "健康术语",
        "description": "包括健康领域的专业术语",
        "examples": ["BMI", "基础代谢率", "体脂率", "有氧运动"]
    },
    EntityType.OTHER: {
        "name": "其他实体",
        "description": "与健康相关但未分类的实体",
        "examples": []
    }
}


def get_entity_type_desc(entity_type: EntityType) -> Dict:
    """获取实体类型描述"""
    return ENTITY_TYPE_DESC.get(entity_type, ENTITY_TYPE_DESC[EntityType.OTHER])


# 预定义的健康实体数据（用于初始化知识图谱）
PREDEFINED_ENTITIES = [
    # 症状
    HealthEntity("头痛", EntityType.SYMPTOM, "头部疼痛不适", synonyms=["头疼", "偏头痛"]),
    HealthEntity("发热", EntityType.SYMPTOM, "体温升高超过正常范围", synonyms=["发烧", "高烧"]),
    HealthEntity("咳嗽", EntityType.SYMPTOM, "呼吸道反射性动作", synonyms=["干咳", "咳痰"]),
    HealthEntity("失眠", EntityType.SYMPTOM, "入睡困难或睡眠质量差", synonyms=["睡不着", "睡眠障碍"]),
    HealthEntity("乏力", EntityType.SYMPTOM, "身体疲乏无力", synonyms=["疲劳", "无力"]),
    HealthEntity("恶心", EntityType.SYMPTOM, "胃部不适欲吐", synonyms=["想吐", "反胃"]),
    HealthEntity("头晕", EntityType.SYMPTOM, "头部晕眩感", synonyms=["眩晕", "头昏"]),
    HealthEntity("心悸", EntityType.SYMPTOM, "心跳异常感觉", synonyms=["心跳加速", "心慌"]),
    HealthEntity("胸闷", EntityType.SYMPTOM, "胸部闷胀不适", synonyms=["胸口闷"]),
    HealthEntity("食欲不振", EntityType.SYMPTOM, "不想吃东西", synonyms=["没胃口", "厌食"]),

    # 疾病
    HealthEntity("高血压", EntityType.DISEASE, "血压持续升高的慢性病",
                 attributes={"诊断标准": "血压≥140/90mmHg"}),
    HealthEntity("糖尿病", EntityType.DISEASE, "血糖代谢异常的慢性病",
                 attributes={"诊断标准": "空腹血糖≥7.0mmol/L"}),
    HealthEntity("感冒", EntityType.DISEASE, "上呼吸道感染", synonyms=["普通感冒", "流感"]),
    HealthEntity("胃炎", EntityType.DISEASE, "胃黏膜炎症", synonyms=["胃病"]),
    HealthEntity("冠心病", EntityType.DISEASE, "冠状动脉粥样硬化性心脏病"),
    HealthEntity("肥胖", EntityType.DISEASE, "体脂过多导致的健康问题",
                 attributes={"诊断标准": "BMI≥28"}),
    HealthEntity("失眠症", EntityType.DISEASE, "长期睡眠障碍"),
    HealthEntity("抑郁症", EntityType.DISEASE, "情绪障碍性疾病"),
    HealthEntity("贫血", EntityType.DISEASE, "血液中红细胞或血红蛋白减少"),
    HealthEntity("高血脂", EntityType.DISEASE, "血脂水平过高"),
    HealthEntity("肝炎", EntityType.DISEASE, "肝脏炎症性疾病"),

    # 人体部位
    HealthEntity("心脏", EntityType.BODY_PART, "循环系统核心器官"),
    HealthEntity("肝脏", EntityType.BODY_PART, "代谢解毒器官"),
    HealthEntity("肺部", EntityType.BODY_PART, "呼吸器官", synonyms=["肺"]),
    HealthEntity("胃", EntityType.BODY_PART, "消化器官"),
    HealthEntity("肾脏", EntityType.BODY_PART, "泌尿系统器官", synonyms=["肾"]),
    HealthEntity("大脑", EntityType.BODY_PART, "神经系统核心"),
    HealthEntity("血管", EntityType.BODY_PART, "血液运输通道"),
    HealthEntity("骨骼", EntityType.BODY_PART, "身体支架"),
    HealthEntity("肌肉", EntityType.BODY_PART, "运动系统组成部分"),
    HealthEntity("眼睛", EntityType.BODY_PART, "视觉器官"),

    # 药物
    HealthEntity("阿司匹林", EntityType.DRUG, "解热镇痛药"),
    HealthEntity("降压药", EntityType.DRUG, "治疗高血压的药物"),
    HealthEntity("胰岛素", EntityType.DRUG, "调节血糖的激素药物"),
    HealthEntity("抗生素", EntityType.DRUG, "抗感染药物"),
    HealthEntity("维生素", EntityType.DRUG, "营养补充剂"),
    HealthEntity("钙片", EntityType.DRUG, "钙补充剂"),
    HealthEntity("止痛药", EntityType.DRUG, "缓解疼痛的药物"),
    HealthEntity("降糖药", EntityType.DRUG, "治疗糖尿病的药物"),

    # 食物
    HealthEntity("米饭", EntityType.FOOD, "主食，碳水化合物来源",
                 attributes={"热量": 230, "蛋白质": 4.3, "碳水": 50}),
    HealthEntity("鸡胸肉", EntityType.FOOD, "高蛋白低脂肉类",
                 attributes={"热量": 165, "蛋白质": 31}),
    HealthEntity("西兰花", EntityType.FOOD, "低热量蔬菜",
                 attributes={"热量": 34, "纤维": 2.6}),
    HealthEntity("牛奶", EntityType.FOOD, "营养丰富的饮品",
                 attributes={"热量": 160, "蛋白质": 8}),
    HealthEntity("苹果", EntityType.FOOD, "水果",
                 attributes={"热量": 95, "纤维": 4.4}),
    HealthEntity("三文鱼", EntityType.FOOD, "富含Omega-3的鱼类",
                 attributes={"热量": 208, "蛋白质": 20}),
    HealthEntity("燕麦", EntityType.FOOD, "健康谷物",
                 attributes={"热量": 195, "纤维": 5}),
    HealthEntity("鸡蛋", EntityType.FOOD, "优质蛋白来源",
                 attributes={"热量": 78, "蛋白质": 6}),
    HealthEntity("豆腐", EntityType.FOOD, "植物蛋白来源",
                 attributes={"热量": 76, "蛋白质": 8}),
    HealthEntity("菠菜", EntityType.FOOD, "富含铁的蔬菜",
                 attributes={"热量": 23, "铁": "丰富"}),

    # 营养素
    HealthEntity("蛋白质", EntityType.NUTRIENT, "身体构建的基本物质"),
    HealthEntity("维生素C", EntityType.NUTRIENT, "抗氧化维生素"),
    HealthEntity("钙", EntityType.NUTRIENT, "骨骼健康必需元素"),
    HealthEntity("铁", EntityType.NUTRIENT, "血红蛋白组成部分"),
    HealthEntity("膳食纤维", EntityType.NUTRIENT, "促进肠道健康"),
    HealthEntity("维生素D", EntityType.NUTRIENT, "骨骼健康相关"),
    HealthEntity("Omega-3", EntityType.NUTRIENT, "健康脂肪酸"),
    HealthEntity("维生素A", EntityType.NUTRIENT, "视力相关维生素"),
    HealthEntity("锌", EntityType.NUTRIENT, "免疫相关矿物质"),
    HealthEntity("钾", EntityType.NUTRIENT, "电解质平衡"),

    # 运动
    HealthEntity("跑步", EntityType.EXERCISE, "有氧运动", attributes={"强度": "中高"}),
    HealthEntity("游泳", EntityType.EXERCISE, "全身有氧运动", attributes={"强度": "中"}),
    HealthEntity("瑜伽", EntityType.EXERCISE, "身心调节运动", attributes={"强度": "低"}),
    HealthEntity("深蹲", EntityType.EXERCISE, "下肢力量训练", attributes={"强度": "中"}),
    HealthEntity("快走", EntityType.EXERCISE, "低强度有氧运动", attributes={"强度": "低"}),
    HealthEntity("力量训练", EntityType.EXERCISE, "增肌塑形运动", attributes={"强度": "高"}),
    HealthEntity("太极拳", EntityType.EXERCISE, "传统健身运动", attributes={"强度": "低"}),
    HealthEntity("跳绳", EntityType.EXERCISE, "高效有氧运动", attributes={"强度": "高"}),
    HealthEntity("冥想", EntityType.EXERCISE, "心理调节活动", attributes={"强度": "低"}),
    HealthEntity("骑自行车", EntityType.EXERCISE, "有氧运动", attributes={"强度": "中"}),
    HealthEntity("运动", EntityType.EXERCISE, "身体活动", synonyms=["锻炼", "健身"]),

    # 危险因素
    HealthEntity("高盐饮食", EntityType.RISK_FACTOR, "增加高血压风险"),
    HealthEntity("缺乏运动", EntityType.RISK_FACTOR, "多种慢性病风险因素"),
    HealthEntity("熬夜", EntityType.RISK_FACTOR, "影响免疫和代谢"),
    HealthEntity("吸烟", EntityType.RISK_FACTOR, "多种疾病风险因素"),
    HealthEntity("饮酒过量", EntityType.RISK_FACTOR, "肝脏等器官损伤风险"),
    HealthEntity("久坐", EntityType.RISK_FACTOR, "心血管和代谢风险"),
    HealthEntity("压力大", EntityType.RISK_FACTOR, "心理健康风险因素"),
    HealthEntity("饮食不规律", EntityType.RISK_FACTOR, "消化系统风险"),

    # 健康目标
    HealthEntity("减脂瘦身", EntityType.HEALTH_GOAL, "减少体脂降低体重"),
    HealthEntity("增肌塑形", EntityType.HEALTH_GOAL, "增加肌肉塑造体型"),
    HealthEntity("保持健康", EntityType.HEALTH_GOAL, "维持健康状态"),
    HealthEntity("控制血糖", EntityType.HEALTH_GOAL, "糖尿病管理目标"),
    HealthEntity("控制血压", EntityType.HEALTH_GOAL, "高血压管理目标"),
    HealthEntity("改善睡眠", EntityType.HEALTH_GOAL, "提高睡眠质量"),
    HealthEntity("减压放松", EntityType.HEALTH_GOAL, "缓解压力放松身心"),

    # 饮食类型
    HealthEntity("低盐饮食", EntityType.DIET_TYPE, "减少盐摄入的饮食方式"),
    HealthEntity("低糖饮食", EntityType.DIET_TYPE, "减少糖摄入的饮食方式"),
    HealthEntity("高蛋白饮食", EntityType.DIET_TYPE, "高蛋白质摄入饮食"),
    HealthEntity("素食", EntityType.DIET_TYPE, "不摄入肉类的饮食方式"),

    # 治疗方法
    HealthEntity("休息", EntityType.TREATMENT, "身体恢复的基本方法"),
    HealthEntity("饮食调理", EntityType.TREATMENT, "通过饮食改善健康"),
    HealthEntity("规律作息", EntityType.HABIT, "按时睡觉起床的习惯"),
    HealthEntity("睡眠", EntityType.HEALTH_TERM, "生理休息状态"),
]


# 实体名称到类型的映射字典（类似 Agriculture_KnowledgeGraph 的 predict_labels）
ENTITY_LABELS = {e.name: e.entity_type.value for e in PREDEFINED_ENTITIES}
# 包含同义词
for e in PREDEFINED_ENTITIES:
    for syn in e.synonyms:
        ENTITY_LABELS[syn] = e.entity_type.value

# 添加扩展实体标签（延迟加载，避免循环导入）
def _load_extended_labels():
    """加载扩展实体标签"""
    global ENTITY_LABELS
    try:
        from agent.knowledge.kg_extended_data import EXTENDED_ENTITY_LABELS
        for name, type_id in EXTENDED_ENTITY_LABELS.items():
            ENTITY_LABELS[name] = type_id
    except ImportError:
        pass

# 在模块加载后尝试加载扩展标签
_load_extended_labels()