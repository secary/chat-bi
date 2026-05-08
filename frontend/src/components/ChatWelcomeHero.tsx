import type { ReactNode } from 'react';

interface ChatWelcomeHeroProps {
  title: string;
  subtitle: string;
  children: ReactNode;
}

export function ChatWelcomeHero({ title, subtitle, children }: ChatWelcomeHeroProps) {
  return (
    <div className="flex w-full max-w-3xl flex-col items-center text-center">
      <h2 className="text-xl font-semibold tracking-tight text-gray-900 md:text-2xl">
        {title}
      </h2>
      <p className="mt-2 text-sm text-gray-500">{subtitle}</p>
      <div className="mt-8 w-full">{children}</div>
    </div>
  );
}
