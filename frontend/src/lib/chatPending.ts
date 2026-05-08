/** UI / hook helper: last row is user ⇒ assistant reply not yet loaded from DB. */

export function isWaitingForAssistantMessage(
  sessionId: number | null,
  messages: readonly { role: string }[],
): boolean {
  return (
    sessionId != null &&
    messages.length > 0 &&
    messages[messages.length - 1]?.role === 'user'
  );
}
