/** Whether the chat main area shows the centered welcome shell (logo + composer). */
export function shouldShowChatWelcomeView(
  booting: boolean,
  messageCount: number,
): boolean {
  return !booting && messageCount === 0;
}
