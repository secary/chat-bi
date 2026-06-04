import { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/useAuth';
import { FormattedMarkdown } from '../lib/formattedMarkdown';
import { helpDocTopics, type DocTopicId } from '../lib/helpDocs';
import { isAdminRole } from '../lib/roles';

export function HelpPage() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const isAdmin = isAdminRole(user?.role);
  const visibleTopics = useMemo(() => helpDocTopics.filter((topic) => !topic.adminOnly || isAdmin), [isAdmin]);
  const requestedTopic = searchParams.get('topic') as DocTopicId | null;
  const activeTopic = visibleTopics.find((topic) => topic.id === requestedTopic) ?? visibleTopics[0];
  const markdownContent = activeTopic?.markdown.replace(/^# .*(\r?\n)+/, '') ?? '';

  if (!activeTopic) {
    return null;
  }

  return (
    <div className="h-full overflow-y-auto bg-white">
      <div className="mx-auto max-w-5xl px-8 py-8">
        <header className="mb-7">
          <p className="text-sm font-medium text-accent">帮助文档</p>
          <h1 className="mt-2 text-2xl font-semibold text-gray-950">{activeTopic.label}</h1>
        </header>

        <article className="pb-10">
          <FormattedMarkdown content={markdownContent} />
        </article>
      </div>
    </div>
  );
}
