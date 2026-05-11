import { ClientComponents } from '@/app/ClientComponents';
import { AmbientBackground } from '@/components/AmbientBackground';
import { Plus_Jakarta_Sans } from 'next/font/google';
import './globals.css';

const plusJakartaSans = Plus_Jakarta_Sans({ subsets: ['latin'] });

export const metadata = {
  title: 'ZYRAA',
  description: 'A project management and issue tracking system',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={plusJakartaSans.className}>
        <AmbientBackground />
        <div className="relative z-10">
          <ClientComponents>
            {children}
          </ClientComponents>
        </div>
      </body>
    </html>
  );
}
