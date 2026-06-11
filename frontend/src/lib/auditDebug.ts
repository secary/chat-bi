import type { HarnessAuditEvent } from '../types/admin';
import type { HarnessAuditIssue } from '../types/admin';

export function filterAuditEvents(
  events: HarnessAuditEvent[],
  query: string,
): HarnessAuditEvent[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return events;
  return events.filter((event) => {
    const payloadText = JSON.stringify(event.payload ?? {}).toLowerCase();
    return [
      event.span_name,
      event.event_name,
      event.level,
      event.message,
      payloadText,
    ].some((part) => String(part || '').toLowerCase().includes(needle));
  });
}

export function summarizeAuditEvent(event: HarnessAuditEvent): string {
  const payload = event.payload ?? {};
  const parts: string[] = [];
  const action = toText(payload.action);
  const agentId = toText(payload.agent_id);
  const skill = toText(payload.skill);
  const reason = toText(payload.reason);
  const warning = toText(payload.dependency_warning);
  const auditStatus = toText(payload.audit_status);
  const issueCount = typeof payload.issue_count === 'number' ? payload.issue_count : null;

  if (action) parts.push(action);
  if (agentId) parts.push(`agent=${agentId}`);
  if (skill) parts.push(`skill=${skill}`);
  if (reason) parts.push(reason);
  if (warning) parts.push(warning);
  if (auditStatus) parts.push(`audit=${auditStatus}`);
  if (issueCount !== null) parts.push(`issues=${String(issueCount)}`);

  if (parts.length > 0) return parts.join(' · ');
  if (event.message) return event.message;
  return '查看原始 payload';
}

export function formatAuditPayload(payload: Record<string, unknown>): string {
  try {
    return JSON.stringify(payload, null, 2);
  } catch {
    return '{}';
  }
}

export function auditEventTone(event: HarnessAuditEvent): 'critical' | 'warning' | 'normal' {
  const eventName = event.event_name.toLowerCase();
  if (
    event.level.toUpperCase() === 'ERROR' ||
    eventName.includes('failed') ||
    eventName.includes('rejected')
  ) {
    return 'critical';
  }
  if (
    eventName.includes('summary_dependency_unmet') ||
    eventName.includes('observation_built') ||
    eventName.includes('decision_content_audited')
  ) {
    return 'warning';
  }
  return 'normal';
}

export function keywordForIssue(issue: HarnessAuditIssue): string {
  const mapping: Record<string, string> = {
    HARNESS_SCHEMA_REJECTED: 'schema_rejected',
    HARNESS_POLICY_REJECTED: 'policy_rejected',
    SKILL_FAILED: 'failed',
    MISSING_OBSERVATION: 'observation_built',
    MISSING_FINISH_EVENT: 'finish_emitted',
    REPEATED_SKILL: 'action_executing',
    EMPTY_LEGACY_SPECIALIST_OUTCOME: 'has_result false',
    DOWNSTREAM_DATA_MISSING: 'dependency_warning',
    SUMMARY_WITH_UNMET_DEPENDENCY: 'summary_dependency_unmet',
    FACTS_MISSING_FOR_DECISION: 'decision_content_audited',
    DECISION_ADVICE_EMPTY: 'decision_content_audited',
    DECISION_ADVICE_INCOMPLETE: 'decision_content_audited',
    DECISION_ADVICE_TOO_GENERIC: 'decision_content_audited',
    DECISION_ADVICE_NOT_GROUNDED: 'decision_content_audited',
    DECISION_SCOPE_MISMATCH: 'decision_content_audited',
  };
  return mapping[issue.code] || issue.code;
}

function toText(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}
