# 银行业智能数据分析平台 —— ChatBI 演示环境

面向银行场景的智能数据分析平台方案文档与演示数据库。提供从自然语言问数到语义治理的完整框架，并附带可一键启动的 MySQL 演示环境。

---

## 目录

- [产品定位](#产品定位)
- [功能框架](#功能框架)
- [演示环境](#演示环境)
- [数据库结构](#数据库结构)
- [语义层结构](#语义层结构)
- [快速开始](#快速开始)

---

## 产品定位

本产品定位为面向银行场景的智能数据分析平台，覆盖数据接入、语义治理、自然语言问数、智能分析、报告生成、安全合规和运维审计的一体化能力。

核心目标用户：

| 用户角色 | 典型使用场景 |
|---|---|
| 管理层 | 查看经营指标、异常预警、经营分析结论 |
| 业务人员 | 自然语言查询指标、生成图表、日常经营分析 |
| 数据分析师 | 快速取数、验证口径、生成专题报告 |
| 一线客户经理 | 分析客户经营、营销机会、业绩目标 |
| IT / 数据治理团队 | 管理指标口径、权限、审计日志 |

---

## 功能框架

```
用户与业务场景层
        │
        ▼
   智能应用层
   ├── 自然语言问数 (ChatBI)
   ├── 智能报表生成
   ├── 经营分析报告生成
   ├── 指标监控与异常预警
   ├── 专题分析助手
   └── 数据资产问答助手
        │
        ▼
  智能分析能力层
  ├── NL2SQL / Text2SQL
  ├── 多轮问答与上下文理解
  ├── 图表推荐与可视化生成
  ├── 趋势分析与预测
  ├── 异常检测
  ├── 归因分析
  └── 指标解释与结论生成
        │
        ▼
  语义与指标治理层
  ├── 业务语义层（字段中文映射）
  ├── 指标口径管理
  ├── 维度模型管理
  ├── 标签体系管理
  ├── 数据血缘与影响分析
  └── 权限映射与数据分级分类
        │
        ▼
  数据接入与计算层
  ├── 数据仓库 / 数据湖 / 湖仓一体
  ├── MySQL / Oracle / ClickHouse 等
  ├── CRM / 核心 / 风控 / 营销系统
  └── SQL 执行与查询优化
        │
        ▼
  基础设施与安全合规层
  ├── 私有化 / 专有云部署
  ├── 统一身份认证（LDAP / SSO）
  ├── 行列级权限控制
  ├── 数据脱敏
  ├── 操作审计 & 模型调用审计
  └── Prompt 安全与结果校验
```

完整框架图见 [bank_chatbi_framework_diagram.svg](bank_chatbi_framework_diagram.svg)。

---

## 演示环境

演示环境通过 Docker Compose 启动一个 MySQL 8.0 实例，自动初始化业务数据表和语义层元数据表。

### 环境依赖

- Docker 20.10+
- Docker Compose v2+

### 服务配置

| 配置项 | 值 |
|---|---|
| 镜像 | mysql:8.0 |
| 容器名 | chatbi-demo-mysql |
| 宿主机端口 | 3307 |
| 数据库名 | chatbi_demo |
| 用户名 | demo_user |
| 密码 | demo_pass |
| Root 密码 | root123456 |
| 字符集 | utf8mb4 |
| 时区 | Asia/Shanghai |

数据持久化到本地 `./mysql-data/` 目录。

---

## 数据库结构

数据库 `chatbi_demo` 包含两类表：**业务数据表**和**语义层元数据表**。

### 业务数据表

#### `sales_order` — 销售订单

| 字段 | 类型 | 业务含义 |
|---|---|---|
| id | BIGINT | 主键 |
| order_date | DATE | 订单日期 |
| region | VARCHAR(50) | 区域（华东 / 华南 / 华北 / 西南） |
| department | VARCHAR(50) | 负责部门 |
| product_category | VARCHAR(50) | 产品类别（软件服务 / 数据产品 / 咨询服务） |
| product_name | VARCHAR(80) | 具体产品名称 |
| channel | VARCHAR(50) | 成交渠道（线上 / 渠道 / 直销） |
| customer_type | VARCHAR(50) | 客户类型（企业客户 / 中小客户） |
| sales_amount | DECIMAL(12,2) | 销售额 |
| order_count | INT | 订单数 |
| customer_count | INT | 客户数 |
| gross_profit | DECIMAL(12,2) | 毛利 |
| target_amount | DECIMAL(12,2) | 目标销售额 |

#### `customer_profile` — 客户画像（月度快照）

| 字段 | 类型 | 业务含义 |
|---|---|---|
| id | BIGINT | 主键 |
| stat_month | DATE | 统计月份 |
| region | VARCHAR(50) | 区域 |
| customer_type | VARCHAR(50) | 客户类型 |
| new_customers | INT | 新增客户数 |
| active_customers | INT | 活跃客户数 |
| retained_customers | INT | 留存客户数 |
| churned_customers | INT | 流失客户数 |

演示数据覆盖 **2026 年 1–4 月**，包含华东、华南、华北、西南四个区域。

---

## 语义层结构

语义层是 ChatBI 能在真实业务中稳定可用的核心。演示环境预置了以下六张元数据表。

### `data_source_config` — 数据源配置

记录数据源名称、类型、连接信息、所属数据库和表、刷新模式与负责人。

### `field_dictionary` — 字段字典

将数据库字段映射为业务人员可理解的中文名称与含义，是 NL2SQL 理解字段语义的基础。

预置字段示例：

| 字段名 | 业务名 | 业务含义 |
|---|---|---|
| sales_amount | 销售额 | 订单确认收入金额 |
| gross_profit | 毛利 | 销售额扣除直接成本后的利润 |
| target_amount | 目标销售额 | 用于计算目标完成率的计划值 |
| new_customers | 新增客户数 | 统计周期内首次产生业务关系的客户数 |
| churned_customers | 流失客户数 | 从活跃转为非活跃的客户数量 |

### `metric_definition` — 指标定义

统一指标口径，包含指标名称、计算公式和默认分析维度。

预置指标：

| 指标名 | 公式 | 默认维度 |
|---|---|---|
| 销售额 | SUM(sales_amount) | 时间、区域、部门、产品类别、渠道 |
| 毛利率 | SUM(gross_profit) / SUM(sales_amount) | 时间、区域、产品类别、渠道 |
| 目标完成率 | SUM(sales_amount) / SUM(target_amount) | 时间、区域、部门 |
| 客户留存率 | SUM(retained_customers) / SUM(active_customers) | 月份、区域、客户类型 |

### `dimension_definition` — 维度定义

维护分析维度及其对应的数据库字段，支持时间、区域、部门、产品类别、渠道、客户类型等维度。

### `business_term` — 业务术语

定义业务场景术语（如"经营概览""归因分析""客户留存"），帮助系统理解用户问题的业务意图。

### `alias_mapping` — 别名映射

将用户自然语言中的口语表达映射到标准指标或维度，减少歧义。

预置映射示例：

| 别名 | 标准名 | 说明 |
|---|---|---|
| 收入 | 销售额 | 用户问收入时默认映射到销售额 |
| 利润 | 毛利 | 演示环境中利润默认使用毛利口径 |
| 完成情况 | 目标完成率 | 用于回答目标完成、达成率相关问题 |
| 大区 | 区域 | 大区、地区统一映射到区域维度 |
| 产品线 | 产品类别 | 产品线、品类统一映射到产品类别 |

---

## 快速开始

### 1. 启动演示数据库

```bash
docker compose up -d
```

首次启动会自动执行 `init.sql`（业务数据）和 `demo_metadata.sql`（语义层元数据）。

### 2. 连接数据库

```
Host:     127.0.0.1
Port:     3307
Database: chatbi_demo
User:     demo_user
Password: demo_pass
```

### 3. 验证数据

```sql
-- 查看业务数据
SELECT region, SUM(sales_amount) AS 销售额 FROM sales_order GROUP BY region;

-- 查看指标定义
SELECT metric_name, formula, business_caliber FROM metric_definition;

-- 查看别名映射
SELECT alias_name, standard_name FROM alias_mapping;
```

### 4. 停止环境

```bash
docker compose down
```

如需同时清除数据（重置演示状态）：

```bash
docker compose down -v
rm -rf ./mysql-data
```

---

## 分阶段建设路线

| 阶段 | 目标 | 主要内容 |
|---|---|---|
| 第一阶段 | ChatBI MVP | 接入核心数据源，建设基础语义层，支持自然语言问数和图表生成 |
| 第二阶段 | 智能分析增强 | 多轮追问、趋势分析、异常检测、归因分析、报告自动生成 |
| 第三阶段 | 场景化智能助手 | 管理层、营销、风控、运营、客户经理等条线专题分析能力 |
| 第四阶段 | 企业级数据智能平台 | 完善语义层、指标体系、数据治理、Prompt 安全和持续运营机制 |

---

## 本地部署要求概览

| 资源类型 | 主要用途 |
|---|---|
| 应用服务器 | 前端、后端、网关、权限服务、任务调度 |
| 模型推理服务器 | 大模型、Embedding、Rerank、NL2SQL 服务 |
| 元数据库服务器 | 用户、权限、配置、语义层、指标、审计日志 |
| 向量数据库服务器 | 知识库、指标说明、字段说明文档向量 |
| 缓存 / 消息队列 | 高并发查询、异步任务、报告生成和通知推送 |

支持私有化或专有云部署，数据不出安全边界。对接 LDAP / AD / SSO，支持行列级权限控制、数据脱敏、操作审计和模型调用审计。
