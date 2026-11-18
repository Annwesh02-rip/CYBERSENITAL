import { useEffect, useState } from 'react';
import { Activity, Database, ShieldAlert, HardDrive } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, PieChart, Pie, Cell } from 'recharts';
import MetricCard from '../components/MetricCard';
import StateMessage from '../components/StateMessage';
import { apiGet, type Summary, type Trend } from '../services/api';

const PALETTE = ['#166c75', '#8cb4ad', '#d9a36d', '#8c91b2'];
export default function Overview() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [trends, setTrends] = useState<Trend[]>([]);
  const [error, setError] = useState('');
  useEffect(() => { Promise.all([apiGet<Summary>('/api/dashboard/summary'), apiGet<Trend[]>('/api/traffic/trends')]).then(([a,b]) => {setSummary(a);setTrends(b);}).catch(e => setError(String(e))); }, []);
  if (error) return <StateMessage message={error} />;
  if (!summary) return <StateMessage message="Loading dashboardâ€¦" />;
  return <>
    <div className="page-intro"><div><div className="eyebrow">DASHBOARD / OVERVIEW</div><h1>Network Overview</h1><p>Explore traffic patterns and unsupervised anomaly signals.</p></div><span className="data-pill">{summary.data_mode.startsWith("Synthetic") ? "â— Synthetic demo data" : "â— Imported dataset"}</span></div>
    <div className="metrics-grid">
      <MetricCard label="Total flows" value={summary.total_flows.toLocaleString()} detail="Analyzed flow records" icon={<Database size={19}/>} />
      <MetricCard label="Flagged anomalies" value={summary.anomaly_count} detail="Isolation Forest predictions" icon={<ShieldAlert size={19}/>} />
      <MetricCard label="Anomaly rate" value={`${summary.anomaly_rate.toFixed(1)}%`} detail="Of analyzed flows" icon={<Activity size={19}/>} />
      <MetricCard label="Traffic volume" value={`${(summary.total_bytes/1_000_000).toFixed(1)} MB`} detail="Aggregate flow byte count" icon={<HardDrive size={19}/>} />
    </div>
    <div className="content-grid">
      <section className="panel wide"><div className="panel-heading"><div><h2>Network activity</h2><p>Hourly flow count and anomaly count</p></div><span className="tag">OFFLINE DATASET</span></div>
        <div className="chart-area"><ResponsiveContainer width="100%" height="100%"><AreaChart data={trends}><defs><linearGradient id="flowGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#217985" stopOpacity={0.22}/><stop offset="100%" stopColor="#217985" stopOpacity={0.01}/></linearGradient></defs><CartesianGrid stroke="#eef1f4" vertical={false}/><XAxis dataKey="hour" tick={{fontSize:11}} minTickGap={30}/><YAxis allowDecimals={false} tick={{fontSize:11}}/><Tooltip/><Area type="monotone" dataKey="flows" stroke="#217985" strokeWidth={3} fill="url(#flowGradient)"/><Area type="monotone" dataKey="anomalies" stroke="#d17864" strokeWidth={2} fill="none"/></AreaChart></ResponsiveContainer></div>
      </section>
      <section className="panel"><div className="panel-heading"><div><h2>Protocol mix</h2><p>Distribution across recorded flows</p></div></div>
        <div className="pie-area"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={summary.protocol_distribution} dataKey="value" nameKey="name" outerRadius={92} innerRadius={58} paddingAngle={3}>{summary.protocol_distribution.map((_, i) => <Cell key={i} fill={PALETTE[i%PALETTE.length]} />)}</Pie><Tooltip/></PieChart></ResponsiveContainer></div>
        <div className="legend">{summary.protocol_distribution.map((p,i)=><div key={p.name}><i style={{background: PALETTE[i%PALETTE.length]}} />{p.name}<strong>{p.value}</strong></div>)}</div>
      </section>
    </div>
    <div className="footnote">Showing offline flow records. The system is not inspecting your computer's network until live capture is explicitly integrated and authorized.</div>
  </>;
}
