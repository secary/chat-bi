export type DocTable = {
  headers: string[];
  rows: string[][];
};

export type DocSection = {
  title: string;
  body?: string;
  items?: string[];
  table?: DocTable;
};

export type DocTab = {
  id: 'user' | 'admin' | 'developer';
  label: string;
  intro: string;
  sections: DocSection[];
};

const userSections: DocSection[] = [
  {
    title: 'ChatBI 能帮你做什么',
    items: [
      '用中文查询指标、排行、趋势和环比对比。',
      '基于已查询的数据生成经营建议。',
      '解释指标口径，帮助确认结果含义。',
      '上传 CSV 或 XLSX 文件，生成指标提案并采纳为分析看板。',
      '将当前会话导出为 PDF 报告。',
    ],
  },
  {
    title: '主要界面',
    table: {
      headers: ['区域', '用途'],
      rows: [
        ['会话列表', '新建、切换或删除历史对话。'],
        ['消息区', '查看提问、思考步骤、文字结论、图表和指标卡片。'],
        ['输入区', '输入问题、上传附件、发送或中止当前生成。'],
      ],
    },
  },
  {
    title: '推荐问法',
    table: {
      headers: ['目标', '示例'],
      rows: [
        ['查指标', '2026 年 1-4 月各区域销售额排行'],
        ['看趋势', '2026 年每月销售额趋势'],
        ['做对比', '4 月相较于 3 月各区域销售额环比'],
        ['要建议', '基于 2026 年 1-4 月各区域销售额，给出经营建议'],
        ['问口径', '销售额是怎么计算的'],
        ['上传分析', '上传文件后输入：分析这个文件，并给出可采纳的指标'],
      ],
    },
  },
  {
    title: '上传文件分析',
    items: [
      '上传 CSV 或 XLSX 文件。',
      '发送分析问题，例如“分析这个文件，给出关键指标提案”。',
      '查看系统生成的指标提案。',
      '回复“采纳全部指标”，或指定要采纳的指标。',
      '查看采纳看板中的 KPI、图表和数据表。',
    ],
  },
  {
    title: '常见问题',
    table: {
      headers: ['问题', '处理建议'],
      rows: [
        ['登录失败', '确认账号、密码是否正确，或联系管理员重置密码。'],
        ['回答要求补充条件', '重新提问时补充时间、指标、区域或对象。'],
        ['没有出现图表', '可以明确说“请用图表展示”。'],
        ['上传文件解析失败', '检查文件格式、表头、空行和异常字符。'],
        ['生成时间太长', '点击“中止”，缩小范围后重试。'],
      ],
    },
  },
];

const adminSections: DocSection[] = [
  {
    title: '管理员职责',
    items: [
      '维护用户账号、角色、密码和启停状态。',
      '配置 LLM Profile，并测试连接和激活默认模型。',
      '维护 MySQL 数据源连接，优先使用只读账号。',
      '控制 Skill 和多 Agent 专线启用状态。',
      '处理部署、健康检查、日志排查和安全配置。',
    ],
  },
  {
    title: '管理入口',
    table: {
      headers: ['菜单', '用途'],
      rows: [
        ['审计', '查看运行链路和 trace 调试信息。'],
        ['技能接入', '启用、禁用或查看 Skill。'],
        ['数据源', '保存和测试 MySQL 连接。'],
        ['LLM配置', '管理模型 Profile、测试连接并激活默认模型。'],
        ['用户管理', '创建账号、调整角色、重置密码、启停账号。'],
      ],
    },
  },
  {
    title: '安全检查',
    items: [
      '生产或对外演示环境应开启鉴权。',
      '首次部署后立即替换默认管理员密码。',
      '设置强随机 CHATBI_JWT_SECRET。',
      'API Key、数据库密码和 GitHub Secrets 不出现在普通用户材料中。',
      '确认普通用户看不到 LLM、用户管理、技能接入、数据源和审计入口。',
      '接入数据源时使用最小权限账号，敏感数据先脱敏或隔离。',
    ],
  },
  {
    title: '故障排查',
    table: {
      headers: ['现象', '优先检查'],
      rows: [
        ['登录失败', '用户状态、角色、密码、鉴权开关。'],
        ['模型无响应', 'LLM Profile、API Key、Base URL、服务商额度。'],
        ['问数失败', '数据源连接、Skill 是否启用、语义层指标和维度。'],
        ['上传分析失败', '文件格式、表头、上传相关 Skill 是否启用。'],
        ['PDF 乱码', '中文字体和部署镜像。'],
      ],
    },
  },
];

const developerSections: DocSection[] = [
  {
    title: '本地开发',
    items: [
      '首次或依赖变动：bash scripts/bootstrap_dev.sh --sync。',
      '日常进入：bash scripts/bootstrap_dev.sh。',
      '启动开发服务：bash scripts/start_dev.sh。',
      '前端默认 5173，后端默认 8000，本机开发 MySQL 默认 3306。',
    ],
  },
  {
    title: '代码结构',
    table: {
      headers: ['路径', '说明'],
      rows: [
        ['frontend/', 'React 前端、页面、组件、hooks、API client。'],
        ['backend/', 'FastAPI 路由、Agent 编排、配置、存储、渲染。'],
        ['skills/', 'Skill 文档和确定性脚本。'],
        ['database/', 'MySQL 初始化脚本、业务数据和语义层。'],
        ['scripts/', '启动、测试、格式化、审计辅助脚本。'],
        ['tests/', 'Python 测试。'],
      ],
    },
  },
  {
    title: 'Agent 主线',
    items: [
      '统一入口是 backend/agent/runner.py 的 stream_chat。',
      '前端默认发送 multi_agents="auto"，由 execution_decider 判断 ask、single 或 multi。',
      '单 Agent 默认走 ReAct，多 Agent 由 Manager 规划后交给专线执行并汇总。',
      'Skill 脚本输出归一为 SkillResult，再由 formatter 和 renderers 转成前端消息。',
    ],
  },
  {
    title: '测试与格式化',
    items: [
      '.venv/bin/python scripts/format_code.py。',
      'PYTHONPATH=. .venv/bin/python scripts/run_tests.py quick -- -q。',
      '改 Agent 跑 agent 套件，改管理功能跑 admin 套件。',
      '前端执行 cd frontend && npm run lint && npm run test && npm run build。',
      '新增 tests/test_*.py 时注册到 scripts/run_tests.py 的 MODULE_SUITES。',
    ],
  },
  {
    title: '开发规则',
    items: [
      '单文件不超过 300 行。',
      '禁止 console.log，前端 API 统一走 apiClient。',
      '问数和决策建议脚本只执行 SELECT。',
      '新功能必须补测试。',
    ],
  },
];

export const helpDocTabs: DocTab[] = [
  {
    id: 'user',
    label: '使用文档',
    intro: '面向普通业务用户，只包含提问、上传、查看结果和常见问题。',
    sections: userSections,
  },
  {
    id: 'admin',
    label: '管理员文档',
    intro: '面向系统管理员，包含账号、模型、数据源、Skill 和安全检查。',
    sections: adminSections,
  },
  {
    id: 'developer',
    label: '开发者文档',
    intro: '面向研发人员，包含本地开发、架构主线、测试和代码规范。',
    sections: developerSections,
  },
];
