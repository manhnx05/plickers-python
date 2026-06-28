import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

export default function StudentDisplay() {
  const [state, setState] = useState({ scanning: false, results: {} as Record<string, string>, revealed: false, question: null as any });

  useEffect(() => {
    const sse = new EventSource('/api/events');
    sse.onmessage = (e) => {
      setState(JSON.parse(e.data));
    };
    return () => sse.close();
  }, []);

  const counts = { A: 0, B: 0, C: 0, D: 0 };
  Object.values(state.results).forEach(v => { if ((counts as any)[v] !== undefined) (counts as any)[v]++; });

  const data = {
    labels: ['A', 'B', 'C', 'D'],
    datasets: [
      {
        label: 'Votes',
        data: [counts.A, counts.B, counts.C, counts.D],
        backgroundColor: [
          state.revealed && state.question?.correct === 'A' ? '#ef4444' : '#374151',
          state.revealed && state.question?.correct === 'B' ? '#3b82f6' : '#374151',
          state.revealed && state.question?.correct === 'C' ? '#22c55e' : '#374151',
          state.revealed && state.question?.correct === 'D' ? '#f59e0b' : '#374151',
        ],
        borderRadius: 8,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: { display: false },
      title: {
        display: true,
        text: state.question ? `Question: ${state.question.text}` : 'Waiting for question...',
        color: '#e6edf3',
        font: { size: 24, family: 'Inter' }
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: { stepSize: 1, color: '#7d8590' },
        grid: { color: '#21262d' }
      },
      x: {
        ticks: { color: '#e6edf3', font: { size: 18, weight: 'bold' } as any },
        grid: { display: false }
      }
    }
  };

  return (
    <div className="display-layout">
      <div style={{ position: 'absolute', top: 20, left: 20 }}>
        <div className="header-links">
          <Link to="/">← Back to Dashboard</Link>
        </div>
      </div>
      
      <div className="chart-container">
        <h2 style={{ textAlign: 'center', marginBottom: '2rem', color: state.scanning ? 'var(--green)' : 'var(--muted)' }}>
          {state.scanning ? 'Scanning in progress...' : state.revealed ? 'Results Revealed' : 'Paused'}
        </h2>
        
        {state.revealed ? (
          <Bar options={options} data={data} />
        ) : (
          <div style={{ textAlign: 'center', padding: '4rem 0', color: 'var(--muted)' }}>
            <div style={{ fontSize: '48px', fontWeight: 'bold', color: 'var(--text)' }}>
              {Object.keys(state.results).length}
            </div>
            <div>Cards Scanned</div>
          </div>
        )}
      </div>
    </div>
  );
}
