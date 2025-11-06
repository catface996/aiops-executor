# 量子力学研究团队使用指南

## 🎯 团队概述

我已经成功为你构建了一个专业的量子力学研究团队，使用 OpenRouter 的 `google/gemini-2.0-flash-exp` 模型。

### 团队结构

**团队ID**: `ht_44a9d96c4`

**三个专业子团队**：
1. **理论物理研究团队** - 负责量子理论分析和数学建模
2. **实验物理研究团队** - 负责实验设计和数据分析  
3. **科学写作团队** - 负责科普写作和知识传播

### 团队成员

**理论物理团队**：
- 量子理论物理学家：专精量子力学基础理论、量子场论、量子信息
- 数学物理专家：处理复杂数学计算、方程求解、数值分析

**实验物理团队**：
- 量子实验物理学家：设计量子光学、原子物理实验
- 实验数据分析专家：统计分析、信号处理、数据可视化

**科学写作团队**：
- 量子物理科学写作专家：学术论文、技术报告撰写
- 量子科普传播专家：科普文章、公众教育内容创作

## 🚀 使用方法

### 1. 启动团队执行
```bash
curl -X POST "http://localhost:8000/api/v1/hierarchical-teams/ht_44a9d96c4/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "execution_config": {
      "stream_events": true,
      "save_intermediate_results": true
    }
  }'
```

### 2. 实时监控执行过程
```bash
curl -N -H "Accept: text/event-stream" \
  "http://localhost:8000/api/v1/executions/{execution_id}/stream"
```

## ✅ 测试结果

- ✅ 团队创建成功 (ID: ht_44a9d96c4)
- ✅ 执行接口正常工作 (返回202状态码)
- ✅ Stream接口实时事件流正常
- ✅ 使用 OpenRouter 的 google/gemini-2.0-flash-exp 模型
- ✅ 包含6个专业智能体，分工明确
- ✅ 支持依赖关系：理论→实验→写作的顺序执行

团队已准备就绪，可以开始量子力学研究和科普写作任务！