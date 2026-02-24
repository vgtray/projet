'use client';

import Header from '@/components/Header';
import LogViewer from '@/components/LogViewer';

export default function LogsPage() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-screen-2xl space-y-6 px-4 py-6 lg:px-6">
        <LogViewer />
      </main>
    </>
  );
}
