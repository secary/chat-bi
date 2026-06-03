import auditsMarkdown from '../../../docs/help/audits.md?raw';
import chatMarkdown from '../../../docs/help/chat.md?raw';
import dataSourcesMarkdown from '../../../docs/help/data-sources.md?raw';
import developerMarkdown from '../../../docs/help/developer.md?raw';
import llmMarkdown from '../../../docs/help/llm.md?raw';
import skillsMarkdown from '../../../docs/help/skills.md?raw';
import usersMarkdown from '../../../docs/help/users.md?raw';

export type DocTopicId = 'chat' | 'data-sources' | 'llm' | 'skills' | 'users' | 'audits' | 'developer';

export type HelpDocTopic = {
  id: DocTopicId;
  label: string;
  adminOnly?: boolean;
  markdown: string;
};

export const helpTopicByPath: Array<{ prefix: string; topic: DocTopicId }> = [
  { prefix: '/data-sources', topic: 'data-sources' },
  { prefix: '/llm', topic: 'llm' },
  { prefix: '/skills', topic: 'skills' },
  { prefix: '/users', topic: 'users' },
  { prefix: '/audits', topic: 'audits' },
  { prefix: '/help', topic: 'chat' },
  { prefix: '/', topic: 'chat' },
];

export function helpTopicForPath(pathname: string): DocTopicId {
  return helpTopicByPath.find((item) => pathname.startsWith(item.prefix))?.topic ?? 'chat';
}

export const helpDocTopics: HelpDocTopic[] = [
  {
    id: 'chat',
    label: '对话教程',
    markdown: chatMarkdown,
  },
  {
    id: 'data-sources',
    label: '数据源配置',
    adminOnly: true,
    markdown: dataSourcesMarkdown,
  },
  {
    id: 'llm',
    label: 'LLM 配置',
    adminOnly: true,
    markdown: llmMarkdown,
  },
  {
    id: 'skills',
    label: '技能接入',
    adminOnly: true,
    markdown: skillsMarkdown,
  },
  {
    id: 'users',
    label: '用户管理',
    adminOnly: true,
    markdown: usersMarkdown,
  },
  {
    id: 'audits',
    label: '审计说明',
    adminOnly: true,
    markdown: auditsMarkdown,
  },
  {
    id: 'developer',
    label: '开发者文档',
    adminOnly: true,
    markdown: developerMarkdown,
  },
];
