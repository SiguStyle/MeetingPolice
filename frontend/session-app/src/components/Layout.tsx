import { PropsWithChildren } from 'react';

export function Layout({ children }: PropsWithChildren) {
  return (
    <div className="mp-session-layout">
      <header>
        <h1>MeetingPolice Session</h1>
        <p>参加者はここで Meeting ID を入力し、音声解析の結果をリアルタイムに確認します。</p>
      </header>
      <main>{children}</main>
    </div>
  );
}
