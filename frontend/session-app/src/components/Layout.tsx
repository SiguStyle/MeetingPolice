import { PropsWithChildren } from 'react';

export function Layout({ children }: PropsWithChildren) {
  return (
    <div className="mp-session-layout">
      <header>
        <h1>MeetingPolice Session</h1>
        <p>Live insights for active participants</p>
      </header>
      <main>{children}</main>
    </div>
  );
}
