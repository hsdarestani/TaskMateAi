import type { ReactNode } from 'react';

interface CTAButtonProps {
  children: ReactNode;
  href?: string;
  size?: 'md' | 'lg';
  className?: string;
}

export function CTAButton({
  children,
  href = 'https://t.me/TaskMateAIBot',
  size = 'lg',
  className = ''
}: CTAButtonProps) {
  const sizing = size === 'lg' ? 'px-6 py-3 text-base md:text-lg' : 'px-4 py-2 text-sm';

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center justify-center rounded-full bg-emerald-400/90 font-semibold text-slate-900 shadow-[0_12px_30px_-15px_rgba(16,185,129,1)] transition hover:bg-emerald-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-200 ${sizing} ${className}`}
    >
      {children}
    </a>
  );
}
