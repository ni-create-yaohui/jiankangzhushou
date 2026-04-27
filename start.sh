#!/bin/bash

echo "========================================"
echo "   健康智能助手 - 启动脚本 v2.0"
echo "   带知识图谱功能"
echo "========================================"
echo ""

cd "$(dirname "$0")"

if ! command -v python &> /dev/null; then
    echo "[错误] 未找到Python环境，请先安装Python"
    exit 1
fi

if [ -z "$DASHSCOPE_API_KEY" ]; then
    echo "[警告] 未设置DASHSCOPE_API_KEY环境变量"
    echo "请设置: export DASHSCOPE_API_KEY=your_api_key"
    echo ""
fi

echo "[检查] 正在检查依赖..."
if ! python -c "import fastapi" &> /dev/null; then
    echo "[安装] 正在安装依赖..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[错误] 依赖安装失败"
        exit 1
    fi
fi

echo "[完成] 依赖检查通过"
echo ""

echo "[检查] 正在检查知识图谱状态..."
python -c "from agent.knowledge.health_kg import health_kg; print('[KG] 节点数:', len(set(n.name for n in health_kg._nodes.values())), '边数:', sum(len(v) for v in health_kg._edges.values()))" 2>/dev/null || echo "[警告] 知识图谱模块加载失败"

echo ""
echo "[启动] 正在启动应用..."
echo "========================================"
echo ""
echo " 访问地址: http://localhost:7958"
echo ""
echo " 功能模块:"
echo " - 知识图谱概览 (93节点, 53关系)"
echo " - 实体查询 (疾病/症状/药物/食物等)"
echo " - 关系查询 (实体关联路径)"
echo " - 智能问答 (KGQA系统)"
echo " - 命名实体识别 (NER)"
echo " - 健康工具 (BMI/热量计算)"
echo ""
echo "========================================"

python -m uvicorn api_server:app --host 0.0.0.0 --port 7958 --reload