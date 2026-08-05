import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import { ClerkProvider } from '@clerk/nextjs';
import { Providers } from '@/providers';
import { APP_NAME } from '@/lib/constants';
import './globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

export const metadata: Metadata = {
  title: {
    default: APP_NAME,
    template: `%s · ${APP_NAME}`,
  },
  description:
    'Enterprise secure online examination management system for colleges with AI-powered question generation and live proctoring.',
  keywords: ['online exams', 'proctoring', 'question bank', 'college', 'examination management'],
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: 'hsl(0 0% 100%)',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <ClerkProvider>
      <html lang="en" suppressHydrationWarning>
        <body className={`${inter.variable} font-sans`}>
          <Providers>{children}</Providers>
        </body>
      </html>
    </ClerkProvider>
  );
}
