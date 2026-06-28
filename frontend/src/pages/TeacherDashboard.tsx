import { useState, useEffect } from 'react';
import { LogOut } from 'lucide-react';
import { api } from '../api/client';

export default function TeacherDashboard({ user, setUser }: { user: any, setUser: (u: any) => void }) {
  const [classData, setClassData] = useState<any>(null);
  const [questions, setQuestions] = useState<any[]>([]);
  const [selectedQuestion, setSelectedQuestion] = useState<any>(null);
  const [state, setState] = useState({ scanning: false, results: {} as Record<string, string>, revealed: false, question: null as any });

  useEffect(() => {
    api.get<any>('/api/class').then(setClassData).catch(console.error);
    api.get<any[]>('/api/questions').then(setQuestions).catch(console.error);

    const sse = new EventSource('/api/events');
    sse.onmessage = (e) => {
      setState(JSON.parse(e.data));
    };
    return () => sse.close();
  }, []);

  const handleLogout = async () => {
    try {
      await api.post('/logout');
    } catch {}
    setUser(null);
  };

  const handleStart = async () => {
    if (!selectedQuestion) return alert('Please select a question!');
    try {
      await api.post('/api/start', { question: selectedQuestion });
    } catch (e) {
      console.error(e);
    }
  };

  const handleStop = async () => await api.post('/api/stop').catch(console.error);
  const handleReveal = async () => await api.post('/api/reveal').catch(console.error);
  const handleReset = async () => {
    if (confirm('Reset session? All results will be cleared.')) {
      await api.post('/api/reset').catch(console.error);
      setSelectedQuestion(null);
    }
  };

  const answeredCount = Object.keys(state.results).length;
  const totalStudents = classData?.students?.length || 0;

  const counts = { A: 0, B: 0, C: 0, D: 0 };
  Object.values(state.results).forEach(v => { if ((counts as any)[v] !== undefined) (counts as any)[v]++; });
  const totalAnswers = answeredCount || 1;

  return (
    <div className="dashboard-layout">
      <header>
        <div className="logo">
          <span>🎯</span>
          <span>Plickers Classroom</span>
        </div>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <span className="class-badge">{classData?.class_name || 'Loading class...'}</span>
          <div className="scan-status">
            <div className={`dot ${state.scanning ? 'active' : ''}`}></div>
            <span>{state.scanning ? 'Scanning...' : state.revealed ? 'Revealed' : 'Paused'}</span>
          </div>
          <button onClick={handleLogout} style={{ background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer' }}><LogOut size={18} /></button>
        </div>
      </header>

      <main>
        <div className="camera-panel">
          <div className="camera-wrap">
            <img src="/video_feed" alt="Camera Feed" />
            <div className="cam-overlay">
              {state.scanning ? `Detected: ${answeredCount} cards` : 'Camera Active'}
            </div>
          </div>
          <div className="controls">
            <button className="btn btn-start" onClick={handleStart} disabled={state.scanning}>▶ START</button>
            <button className="btn btn-stop" onClick={handleStop} disabled={!state.scanning}>⏸ PAUSE</button>
            <button className="btn btn-reveal" onClick={handleReveal} disabled={state.revealed || !state.question}>👁 REVEAL</button>
            <button className="btn btn-reset" onClick={handleReset}>↺</button>
          </div>
        </div>

        <div className="right-panel">
          <div className="q-panel">
            <label>Current Question</label>
            <select 
              className="q-select" 
              value={selectedQuestion ? questions.indexOf(selectedQuestion) : ''}
              onChange={e => setSelectedQuestion(e.target.value === '' ? null : questions[Number(e.target.value)])}
            >
              <option value="">-- Select question --</option>
              {questions.map((q, i) => <option key={i} value={i}>#{q.id} — {q.text}</option>)}
            </select>
            <div className="q-preview">
              {selectedQuestion ? (
                <>
                  <strong>{selectedQuestion.text}</strong><br />
                  <span className="ans-A">A: {selectedQuestion.options.A}</span> &nbsp;
                  <span className="ans-B">B: {selectedQuestion.options.B}</span> &nbsp;
                  <span className="ans-C">C: {selectedQuestion.options.C}</span> &nbsp;
                  <span className="ans-D">D: {selectedQuestion.options.D}</span>
                </>
              ) : 'No question selected.'}
            </div>
          </div>

          <div className="students-wrap">
            <h3>Students — <span style={{ color: 'var(--green)' }}>{answeredCount}/{totalStudents}</span> answered</h3>
            <div className="student-grid">
              {classData?.students?.map((s: any) => {
                const ans = state.results[s.card_no];
                return (
                  <div key={s.card_no} className={`stu-card ${ans ? `answered answered-${ans}` : ''}`}>
                    <div className="stu-no">#{String(s.card_no).padStart(2, '0')}</div>
                    <div className="stu-name">{s.name.split(' ').pop()}</div>
                    <div className={`stu-ans ${ans ? `ans-${ans}` : ''}`}>{ans || '·'}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </main>

      <footer>
        {['A', 'B', 'C', 'D'].map((l) => {
          const isCorrect = state.revealed && state.question?.correct === l;
          return (
            <div key={l} className="stat-block" style={isCorrect ? { background: `rgba(var(--${l}-rgb), 0.15)`, boxShadow: 'inset 0 0 0 2px currentColor' } : {}}>
              <div className={`stat-letter sl-${l}`}>{l}</div>
              <div className="stat-info">
                <span className="stat-count">{(counts as any)[l]}</span>
                <span className="stat-pct">{Math.round(((counts as any)[l] / totalAnswers) * 100)}%</span>
              </div>
            </div>
          );
        })}
      </footer>
    </div>
  );
}
