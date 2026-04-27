"""
提示词加载器 - 支持动态加载专家提示词

参考 AI-IDE-Agent 的提示词架构设计：
- YAML前置元数据支持
- 专家角色提示词动态加载
- 提示词版本管理
"""
from pathlib import Path
from typing import Dict, Optional
from project.config_hander import prompts_conf
from project.path_tool import get_abs_path
from project.logger_handler import logger

# 提示词目录
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _parse_frontmatter(content: str) -> Dict:
    """解析提示词的YAML前置元数据"""
    if not content.startswith("---"):
        return {}

    try:
        end_idx = content.find("---", 3)
        if end_idx == -1:
            return {}

        frontmatter = content[3:end_idx].strip()
        metadata = {}
        for line in frontmatter.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
        return metadata
    except Exception:
        return {}


def _load_prompt_file(file_path: str) -> str:
    """加载提示词文件"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"加载提示词文件失败: {file_path}, {str(e)}")
        raise e


def load_system_prompts() -> str:
    """加载主系统提示词"""
    try:
        system_prompt_path = get_abs_path(prompts_conf["main_prompt_path"])
    except KeyError as e:
        logger.error(f"[load_system_prompts] 配置项缺少 main_prompt_path")
        raise e

    return _load_prompt_file(system_prompt_path)


def load_rag_prompts() -> str:
    """加载RAG摘要提示词"""
    try:
        rag_prompt_path = get_abs_path(prompts_conf["rag_summarize_prompt_path"])
    except KeyError as e:
        logger.error(f"[load_rag_prompts] 配置项缺少 rag_summarize_prompt_path")
        raise e

    return _load_prompt_file(rag_prompt_path)


def load_report_prompts() -> str:
    """加载报告生成提示词"""
    try:
        report_prompt_path = get_abs_path(prompts_conf["report_prompt_path"])
    except KeyError as e:
        logger.error(f"[load_report_prompts] 配置项缺少 report_prompt_path")
        raise e

    return _load_prompt_file(report_prompt_path)


def load_health_diagnosis_prompts() -> str:
    """加载健康诊断提示词"""
    try:
        diagnosis_prompt_path = get_abs_path(prompts_conf["health_diagnosis_prompt_path"])
    except KeyError as e:
        logger.error(f"[load_health_diagnosis_prompts] 配置项缺少 health_diagnosis_prompt_path")
        raise e

    return _load_prompt_file(diagnosis_prompt_path)


# ========== 专家提示词加载 ==========

def load_expert_prompt(expert_name: str) -> str:
    """
    加载专家提示词

    Args:
        expert_name: 专家名称（如 health_diagnostician, nutrition_analyst）

    Returns:
        提示词内容（已去除YAML前置元数据）
    """
    expert_file = PROMPTS_DIR / f"{expert_name}.md"

    if not expert_file.exists():
        logger.warning(f"[load_expert_prompt] 专家提示词不存在: {expert_name}")
        return load_system_prompts()  # 返回默认系统提示词

    content = _load_prompt_file(str(expert_file))

    # 去除YAML前置元数据，只返回正文
    if content.startswith("---"):
        end_idx = content.find("---", 3)
        if end_idx != -1:
            return content[end_idx + 3:].strip()

    return content