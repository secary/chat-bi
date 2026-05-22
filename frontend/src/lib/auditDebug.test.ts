import { describe, expect, it } from 'vitest';
import type { HarnessAuditEvent } from '../types/admin';
import {
  auditEventTone,
  filterAuditEvents,
  formatAuditPayload,
  keywordForIssue,
  summarizeAuditEvent,
} from './auditDebug';

function makeEvent(overrides: Partial<HarnessAuditEvent> = {}): HarnessAuditEvent {
  return {
    id: 1,
    trace_id: 'trace-1',
    span_name: 'agent.harness',
    event_name: 'action_executing',
    level: 'INFO',
    message: '',
    payload: {},
    created_at: '2026-05-20T10:00:00Z',
    ...overrides,
  };
}

describe('auditDebug', () => {
  it('summarizes key payload fields', () => {
    const summary = summarizeAuditEvent(
      makeEvent({
        payload: {
          action: 'run_specialist',
          agent_id: 'business_advisor',
          skill: 'chatbi-decision-advisor',
        },
      }),
    );
    expect(summary).toContain('run_specialist');
    expect(summary).toContain('agent=business_advisor');
    expect(summary).toContain('skill=chatbi-decision-advisor');
  });

  it('filters events by payload or event metadata', () => {
    const events = [
      makeEvent({
        id: 1,
        payload: { agent_id: 'upload_analyst' },
      }),
      makeEvent({
        id: 2,
        event_name: 'summary_dependency_unmet',
        payload: { dependency_warning: '缺少已采纳指标具体数值' },
      }),
    ];
    expect(filterAuditEvents(events, 'upload_analyst')).toHaveLength(1);
    expect(filterAuditEvents(events, 'summary_dependency_unmet')).toHaveLength(1);
    expect(filterAuditEvents(events, '缺少已采纳指标')).toHaveLength(1);
  });

  it('formats payload as pretty json', () => {
    const text = formatAuditPayload({ step: 1, ok: true });
    expect(text).toContain('"step": 1');
    expect(text).toContain('"ok": true');
  });

  it('maps important events to visual tones', () => {
    expect(auditEventTone(makeEvent({ event_name: 'policy_rejected' }))).toBe('critical');
    expect(auditEventTone(makeEvent({ event_name: 'summary_dependency_unmet' }))).toBe(
      'warning',
    );
    expect(auditEventTone(makeEvent({ event_name: 'finish_emitted' }))).toBe('normal');
  });

  it('maps issue code to debug search keyword', () => {
    expect(
      keywordForIssue({
        code: 'SUMMARY_WITH_UNMET_DEPENDENCY',
        level: 'warning',
        message: 'x',
      }),
    ).toBe('summary_dependency_unmet');
  });
});
