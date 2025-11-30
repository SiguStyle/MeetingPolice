import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';

interface ResultData {
    agendaText: string;
    elapsedSeconds: number;
    avgAlignment: number;
    totalItems: number;
}

export function ResultPage() {
    const location = useLocation();
    const navigate = useNavigate();
    const [resultData, setResultData] = useState<ResultData | null>(null);

    useEffect(() => {
        const data = location.state as ResultData;
        if (!data) {
            // データがない場合は元のページに戻る
            navigate('/poc-satomin');
            return;
        }
        setResultData(data);
    }, [location, navigate]);

    if (!resultData) {
        return <Layout title="読み込み中..." subtitle=""><div>読み込み中...</div></Layout>;
    }

    const { agendaText, elapsedSeconds, avgAlignment, totalItems } = resultData;
    const minutes = Math.floor(elapsedSeconds / 60);
    const seconds = elapsedSeconds % 60;
    const isSuccess = avgAlignment >= 60;

    return (
        <Layout title="ミーティング結果" subtitle="お疲れさまでした！">
            <div style={{ maxWidth: '800px', margin: '0 auto' }}>
                {isSuccess && (
                    <div style={{
                        padding: '32px',
                        textAlign: 'center',
                        backgroundColor: '#4caf50',
                        color: 'white',
                        borderRadius: '12px',
                        marginBottom: '24px',
                        fontSize: '2em',
                        fontWeight: 'bold'
                    }}>
                        🎉 おめでとう！ 🎉
                    </div>
                )}

                <section className="panel" style={{ marginBottom: '24px' }}>
                    <h2>📊 ミーティング結果</h2>

                    <div style={{ marginTop: '24px' }}>
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: '1fr 1fr',
                            gap: '16px',
                            marginBottom: '24px'
                        }}>
                            <div style={{
                                padding: '20px',
                                backgroundColor: '#f5f5f5',
                                borderRadius: '8px',
                                textAlign: 'center'
                            }}>
                                <p style={{ margin: '0 0 8px 0', fontSize: '0.9em', color: '#666' }}>
                                    ⏱️ 経過時間
                                </p>
                                <div style={{ fontSize: '2.5em', fontWeight: 'bold', color: '#333' }}>
                                    {minutes}:{seconds.toString().padStart(2, '0')}
                                </div>
                            </div>

                            <div style={{
                                padding: '20px',
                                backgroundColor: '#f5f5f5',
                                borderRadius: '8px',
                                textAlign: 'center'
                            }}>
                                <p style={{ margin: '0 0 8px 0', fontSize: '0.9em', color: '#666' }}>
                                    📈 平均一致度
                                </p>
                                <div style={{
                                    fontSize: '2.5em',
                                    fontWeight: 'bold',
                                    color: avgAlignment >= 60 ? '#4caf50' : avgAlignment >= 40 ? '#ff9800' : '#f44336'
                                }}>
                                    {avgAlignment}%
                                </div>
                                <p style={{ margin: '8px 0 0 0', fontSize: '0.85em', color: '#666' }}>
                                    （全{totalItems}件の発言）
                                </p>
                            </div>
                        </div>

                        <div style={{
                            padding: '20px',
                            backgroundColor: '#f9f9f9',
                            borderRadius: '8px',
                            marginBottom: '16px'
                        }}>
                            <h3 style={{ marginTop: 0 }}>📝 アジェンダ</h3>
                            <pre style={{
                                whiteSpace: 'pre-wrap',
                                fontSize: '0.95em',
                                lineHeight: '1.6',
                                margin: 0
                            }}>
                                {agendaText || '（アジェンダなし）'}
                            </pre>
                        </div>

                        {isSuccess ? (
                            <div style={{
                                padding: '16px',
                                backgroundColor: '#e8f5e9',
                                borderRadius: '8px',
                                color: '#2e7d32',
                                textAlign: 'center'
                            }}>
                                <strong>素晴らしい！</strong> アジェンダに沿った議論ができました 👏
                            </div>
                        ) : (
                            <div style={{
                                padding: '16px',
                                backgroundColor: '#fff3e0',
                                borderRadius: '8px',
                                color: '#e65100',
                                textAlign: 'center'
                            }}>
                                次回はもっとアジェンダに沿った議論を心がけましょう 💪
                            </div>
                        )}
                    </div>
                </section>

                <div style={{ textAlign: 'center' }}>
                    <button
                        type="button"
                        onClick={() => navigate('/poc-satomin')}
                        style={{
                            padding: '12px 32px',
                            fontSize: '1.1em',
                            cursor: 'pointer'
                        }}
                    >
                        新しいミーティングを開始
                    </button>
                </div>
            </div>
        </Layout>
    );
}
