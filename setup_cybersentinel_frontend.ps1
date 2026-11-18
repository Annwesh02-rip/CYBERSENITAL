# Apply CyberSentinel frontend source AFTER `npm create vite@latest frontend -- --template react-ts`.
# Only touches frontend/src files, frontend/index.html and frontend/vite.config.ts; does NOT touch npm scaffold package.json/lockfiles.
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not (Test-Path (Join-Path $ProjectRoot "frontend\package.json"))) { throw "Run npm create vite@latest frontend -- --template react-ts in CyberSentinel first." }
$Files = @{}

$Files['frontend\src\App.tsx'] = @'
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Overview from './pages/Overview';
import Security from './pages/Security';
import TrafficAnalysis from './pages/TrafficAnalysis';
import Optimization from './pages/Optimization';

export default function App() {
  return <Routes><Route element={<Layout />}><Route index element={<Overview />}/><Route path="security" element={<Security />}/><Route path="traffic" element={<TrafficAnalysis />}/><Route path="optimization" element={<Optimization />}/></Route></Routes>;
}
'@

$Files['frontend\src\components\Layout.tsx'] = @'
import { NavLink, Outlet } from 'react-router-dom';
import { Activity, ChartNoAxesCombined, Gauge, ShieldCheck, Radar, Github } from 'lucide-react';

const links = [
  { to: '/', label: 'Overview', icon: Gauge },
  { to: '/security', label: 'Security', icon: ShieldCheck },
  { to: '/traffic', label: 'Traffic Analysis', icon: Activity },
  { to: '/optimization', label: 'Optimization', icon: ChartNoAxesCombined },
];

export default function Layout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-icon"><Radar size={25} /></div><div><strong>CyberSentinel</strong><small>NETWORK INTELLIGENCE</small></div></div>
        <div className="sidebar-section">WORKSPACE</div>
        <nav className="nav-links">
          {links.map(({to, label, icon: Icon}) => (
            <NavLink key={to} to={to} end={to === '/'} className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
              <Icon size={18} /><span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom"><div className="sidebar-tag">DEMO MODE</div><p>Offline, synthetic network flows. No live capture is active.</p><span><Github size={14} /> Mini project · v1.0</span></div>
      </aside>
      <div className="main-area">
        <header className="topbar"><span className="breadcrumb">CyberSentinel <span>/</span> Analysis Workspace</span><span className="status"><i /> Offline demo workspace</span></header>
        <main className="page"><Outlet /></main>
      </div>
    </div>
  );
}
'@

$Files['frontend\src\components\MetricCard.tsx'] = @'
import type { ReactNode } from 'react';

export default function MetricCard({ label, value, detail, icon }: {
  label: string; value: string | number; detail: string; icon: ReactNode;
}) {
  return <section className="metric-card"><div className="metric-top"><span>{label}</span><span className="metric-icon">{icon}</span></div><div className="metric-value">{value}</div><p>{detail}</p></section>;
}
'@

$Files['frontend\src\components\StateMessage.tsx'] = @'
export default function StateMessage({ message }: { message: string }) {
  return <div className="state-message">{message}<small>Run preprocessing and training, then start the FastAPI server on port 8000.</small></div>;
}
'@

$Files['frontend\src\index.css'] = @'
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root{font-family:'DM Sans',Arial,sans-serif;color:#223345;background:#f6f8f9;font-synthesis:none;text-rendering:optimizeLegibility}*{box-sizing:border-box}body{margin:0}h1,h2,h3,p{margin-top:0}h1,h2{font-family:Manrope,Arial,sans-serif}a{text-decoration:none;color:inherit}.app-shell{min-height:100vh;display:flex}.sidebar{width:258px;min-width:258px;background:#fff;border-right:1px solid #e7ecee;display:flex;flex-direction:column;padding:28px 18px 18px}.brand{display:flex;align-items:center;gap:12px;padding:0 12px 44px}.brand-icon{width:42px;height:42px;border-radius:13px;color:white;background:#176d78;display:grid;place-items:center}.brand strong{display:block;letter-spacing:-.6px;font:800 17px Manrope}.brand small{display:block;color:#94a1ab;letter-spacing:1.5px;font-size:8px;margin-top:3px;font-weight:800}.sidebar-section{color:#98a2ac;letter-spacing:1.8px;font-size:10px;font-weight:800;padding:0 16px 15px}.nav-links{display:grid;gap:6px}.nav-link{display:flex;align-items:center;gap:12px;padding:13px 15px;color:#6f7f8b;font-weight:700;font-size:13px;border-radius:11px;transition:.15s}.nav-link:hover,.nav-link.active{color:#176d78;background:#eaf4f3}.sidebar-bottom{margin-top:auto;background:#f4f7f7;border:1px solid #e8efef;border-radius:12px;padding:15px}.sidebar-tag{font-size:9px;letter-spacing:1.3px;font-weight:800;color:#196d76}.sidebar-bottom p{font-size:12px;line-height:1.55;color:#819099;margin:10px 0 14px}.sidebar-bottom span{display:flex;align-items:center;gap:6px;color:#90a0aa;font-size:10px}.main-area{flex:1;min-width:0}.topbar{height:75px;display:flex;align-items:center;justify-content:space-between;background:white;border-bottom:1px solid #e7ecee;padding:0 42px}.breadcrumb{font-size:12px;color:#6d7a87;font-weight:700}.breadcrumb span{padding:0 10px;color:#b7c0c8}.status{font-weight:700;color:#637482;font-size:12px;display:flex;align-items:center;gap:8px}.status i{width:8px;height:8px;border-radius:50%;background:#3cb192}.page{max-width:1500px;padding:38px 42px 70px;margin:auto}.page-intro{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:28px}.eyebrow{color:#187d85;letter-spacing:1.9px;font-size:10px;font-weight:800;margin-bottom:9px}.page-intro h1{font-size:30px;letter-spacing:-1.1px;margin:0 0 8px}.page-intro p{color:#83919b;font-size:13px;margin:0}.data-pill{border:1px solid #d6e7e5;background:#ebf5f3;border-radius:18px;padding:9px 13px;color:#207880;font-size:11px;font-weight:800;white-space:nowrap}.metrics-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px;margin-bottom:22px}.metric-card,.panel{background:white;border:1px solid #e6ebee;border-radius:15px;box-shadow:0 5px 18px rgba(28,53,68,.025)}.metric-card{padding:22px}.metric-top{display:flex;align-items:center;justify-content:space-between;color:#7f909b;font-size:12px;font-weight:700}.metric-icon{color:#2c8890;background:#eef7f6;border-radius:11px;width:35px;height:35px;display:grid;place-items:center}.metric-value{font-family:Manrope;font-size:30px;font-weight:800;color:#27394c;letter-spacing:-1.3px;margin:11px 0 6px}.metric-card p{color:#9aa6ad;font-size:11px;margin:0}.content-grid{display:grid;grid-template-columns:minmax(0,1.75fr) minmax(275px,1fr);gap:20px}.panel{padding:22px 24px;margin-bottom:20px;min-width:0}.panel-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:24px}.panel-heading h2{font-size:16px;letter-spacing:-.4px;margin:0 0 7px}.panel-heading p{color:#92a0a8;font-size:11px;margin:0}.tag{color:#8d9da7;border:1px solid #e6edee;padding:6px 9px;border-radius:6px;font-size:9px;letter-spacing:1px;font-weight:800;white-space:nowrap}.alert-tag{color:#c27165;border-color:#f3d9d3;background:#fcf4f2}.chart-area{height:275px;min-width:0}.chart-area.tall{height:360px}.pie-area{height:215px}.legend{display:grid;gap:10px;margin-top:6px}.legend>div{display:flex;align-items:center;gap:8px;color:#7d8c97;font-size:12px}.legend i{width:9px;height:9px;border-radius:50%}.legend strong{margin-left:auto;color:#32485a}.footnote{font-size:11px;color:#9daab2;line-height:1.6;margin:14px 2px}.table-scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;text-align:left;font-size:12px;white-space:nowrap}th{color:#90a0aa;background:#f8fafb;text-transform:uppercase;font-size:10px;letter-spacing:.6px}th,td{padding:13px 14px;border-bottom:1px solid #edf1f3}td{color:#506272}tbody tr:hover{background:#fbfcfc}.mono{font-family:ui-monospace,Consolas,monospace}.status-chip{background:#fdf0ec;color:#b96150;padding:5px 8px;border-radius:7px;font-size:10px;font-weight:800}.empty{color:#93a2ac;font-size:12px;padding:12px}.state-message{margin:30px auto;background:white;border:1px solid #e8edef;border-radius:12px;padding:24px;max-width:640px;color:#556b78}.state-message small{display:block;color:#8a99a4;margin-top:10px}.insight-banner{display:flex;gap:16px;background:#eaf4f2;border:1px solid #cfebe5;border-radius:15px;padding:22px;color:#176c73;margin-bottom:24px}.insight-banner h2{font-size:16px;margin:0 0 7px}.insight-banner p{font-size:12px;line-height:1.6;margin:0;color:#648b8e}.recommendations{display:grid;gap:14px}.recommendation{display:flex;gap:17px;background:white;border:1px solid #e7ecee;padding:20px;border-radius:13px}.rec-icon{flex:none;display:grid;place-items:center;border-radius:10px;width:42px;height:42px;background:#eaf4f3;color:#1d7b80}.rec-icon.high{background:#fff0ed;color:#c66d61}.rec-icon.medium{background:#fff5e7;color:#b78645}.rec-heading{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.rec-heading h2{font-size:14px;margin:0}.recommendation p{margin:9px 0 0;color:#83929d;line-height:1.6;font-size:12px}.priority{font-size:10px;font-weight:800;padding:4px 8px;border-radius:6px;background:#edf4f4;color:#19747b}.priority.high{color:#bc695e;background:#fff1ee}.priority.medium{color:#ad7b3e;background:#fff6ea}@media(max-width:1150px){.metrics-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.content-grid{grid-template-columns:1fr}}@media(max-width:720px){.app-shell{display:block}.sidebar{width:auto;min-width:0;padding:15px}.brand{padding:0 5px 14px}.nav-links{display:flex;gap:4px;overflow-x:auto}.nav-link{padding:11px;white-space:nowrap}.nav-link span{font-size:11px}.sidebar-section,.sidebar-bottom{display:none}.topbar{padding:0 18px;height:55px}.page{padding:25px 16px}.page-intro{align-items:flex-start;flex-direction:column}.metrics-grid{gap:10px}.metric-card{padding:15px}.metric-value{font-size:24px}.panel{padding:15px}.data-pill{font-size:10px}}
'@

$Files['frontend\src\main.tsx'] = @'
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><BrowserRouter><App/></BrowserRouter></React.StrictMode>);
'@

$Files['frontend\src\pages\Optimization.tsx'] = @'
import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, Info, Lightbulb } from 'lucide-react';
import StateMessage from '../components/StateMessage';
import { apiGet, type Recommendation } from '../services/api';

export default function Optimization() {
  const [items, setItems] = useState<Recommendation[]>([]);
  const [error, setError] = useState('');
  useEffect(()=>{apiGet<Recommendation[]>('/api/analysis/optimization').then(setItems).catch(e=>setError(String(e)));},[]);
  if (error) return <StateMessage message={error} />;
  return <><div className="page-intro"><div><div className="eyebrow">RECOMMENDATIONS</div><h1>Optimization Insights</h1><p>Practical follow-up actions derived from the analyzed dataset.</p></div><span className="data-pill">Advisory only</span></div>
    <section className="insight-banner"><Lightbulb size={25}/><div><h2>Evidence first, changes second.</h2><p>These are review suggestions, not automated firewall or router actions. Validate with actual telemetry and an authorized administrator.</p></div></section>
    <div className="recommendations">{items.map((item,i)=><article className="recommendation" key={i}><span className={`rec-icon ${item.priority.toLowerCase()}`}>{item.priority==='High'?<AlertTriangle size={20}/>:item.priority==='Medium'?<Info size={20}/>:<CheckCircle2 size={20}/>}</span><div><div className="rec-heading"><h2>{item.title}</h2><span className={`priority ${item.priority.toLowerCase()}`}>{item.priority}</span></div><p>{item.detail}</p></div></article>)}</div>
  </>;
}
'@

$Files['frontend\src\pages\Overview.tsx'] = @'
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
  if (!summary) return <StateMessage message="Loading dashboard…" />;
  return <>
    <div className="page-intro"><div><div className="eyebrow">DASHBOARD / OVERVIEW</div><h1>Network Overview</h1><p>Explore traffic patterns and unsupervised anomaly signals.</p></div><span className="data-pill">{summary.data_mode.startsWith("Synthetic") ? "● Synthetic demo data" : "● Imported dataset"}</span></div>
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
'@

$Files['frontend\src\pages\Security.tsx'] = @'
import { useEffect, useState } from 'react';
import { CartesianGrid, Scatter, ScatterChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import StateMessage from '../components/StateMessage';
import { apiGet, type Flow, type ProjectionPoint } from '../services/api';

export default function Security() {
  const [flows, setFlows] = useState<Flow[]>([]);
  const [points, setPoints] = useState<ProjectionPoint[]>([]);
  const [error, setError] = useState('');
  useEffect(() => { Promise.all([apiGet<Flow[]>('/api/traffic/flows?limit=1000&anomalies_only=true'),apiGet<ProjectionPoint[]>('/api/analysis/projection')]).then(([a,b])=>{setFlows(a);setPoints(b);}).catch(e=>setError(String(e))); }, []);
  if (error) return <StateMessage message={error} />;
  const normal = points.filter(p=>!p.anomaly), anomalies = points.filter(p=>p.anomaly);
  return <>
    <div className="page-intro"><div><div className="eyebrow">ANOMALY DETECTION</div><h1>Security Analysis</h1><p>Inspect flow-level outliers generated by the PCA + Isolation Forest pipeline.</p></div><span className="data-pill">Unsupervised detection</span></div>
    <section className="panel"><div className="panel-heading"><div><h2>PCA projection</h2><p>Each point represents a flow. Red points were flagged as anomalous.</p></div><span className="tag">2 COMPONENTS</span></div><div className="chart-area tall"><ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{top:10,right:20,bottom:10,left:0}}><CartesianGrid stroke="#edf1f4"/><XAxis type="number" dataKey="x" name="PC1" tick={{fontSize:11}}/><YAxis type="number" dataKey="y" name="PC2" tick={{fontSize:11}}/><Tooltip cursor={{strokeDasharray:'3 3'}}/><Scatter name="Normal" data={normal} fill="#2b8e91" fillOpacity={0.55}/><Scatter name="Anomaly" data={anomalies} fill="#d17765" fillOpacity={0.9}/></ScatterChart></ResponsiveContainer></div></section>
    <section className="panel"><div className="panel-heading"><div><h2>Flagged flows</h2><p>Latest {flows.length} flagged records (click-free local inspection)</p></div><span className="tag alert-tag">REVIEW REQUIRED</span></div><div className="table-scroll"><table><thead><tr><th>Time</th><th>Source IP</th><th>Destination IP</th><th>Protocol</th><th>Port</th><th>Packets</th><th>Score</th><th>Status</th></tr></thead><tbody>{flows.map(f=><tr key={f.id}><td>{new Date(f.timestamp).toLocaleString()}</td><td className="mono">{f.src_ip}</td><td className="mono">{f.dst_ip}</td><td>{f.protocol}</td><td>{f.dst_port}</td><td>{f.packets.toLocaleString()}</td><td>{f.anomaly_score.toFixed(3)}</td><td><span className="status-chip">Flagged</span></td></tr>)}</tbody></table></div>{flows.length===0&&<p className="empty">No flagged flows. Run the training script if data is missing.</p>}</section>
  </>;
}
'@

$Files['frontend\src\pages\TrafficAnalysis.tsx'] = @'
import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import StateMessage from '../components/StateMessage';
import { apiGet, type Congestion, type Trend } from '../services/api';

export default function TrafficAnalysis() {
  const [congestion, setCongestion] = useState<Congestion | null>(null);
  const [trends, setTrends] = useState<Trend[]>([]);
  const [error, setError] = useState('');
  useEffect(()=>{Promise.all([apiGet<Congestion>('/api/analysis/congestion'),apiGet<Trend[]>('/api/traffic/trends')]).then(([a,b])=>{setCongestion(a);setTrends(b);}).catch(e=>setError(String(e)));},[]);
  if (error) return <StateMessage message={error} />;
  if (!congestion) return <StateMessage message="Loading traffic analysis…" />;
  return <><div className="page-intro"><div><div className="eyebrow">TRAFFIC OBSERVABILITY</div><h1>Traffic Analysis</h1><p>Analyze volume trends and identify high-throughput flow bursts.</p></div><span className="data-pill">Flow-derived estimates</span></div>
    <section className="panel"><div className="panel-heading"><div><h2>Hourly traffic volume</h2><p>Summed bytes observed in the demonstration flow dataset</p></div></div><div className="chart-area"><ResponsiveContainer width="100%" height="100%"><BarChart data={trends}><CartesianGrid stroke="#edf1f4" vertical={false}/><XAxis dataKey="hour" tick={{fontSize:11}} minTickGap={20}/><YAxis tickFormatter={(v:number)=>`${(v/1e6).toFixed(0)}M`} tick={{fontSize:11}}/><Tooltip formatter={(v)=>`${(Number(v)/1e6).toFixed(2)} MB`}/><Bar dataKey="bytes" fill="#217985" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></div></section>
    <section className="panel"><div className="panel-heading"><div><h2>High-throughput flow indicators</h2><p>Top-decile threshold: {congestion.threshold_bytes_per_second.toLocaleString()} bytes/s</p></div><span className="tag">NOT CONFIRMED CONGESTION</span></div><div className="table-scroll"><table><thead><tr><th>ID</th><th>Source</th><th>Destination</th><th>Rate (bytes/s)</th><th>Anomaly</th></tr></thead><tbody>{congestion.high_throughput_flows.map(f=><tr key={f.id}><td>#{f.id}</td><td className="mono">{f.src_ip}</td><td className="mono">{f.dst_ip}</td><td>{f.bytes_per_second.toLocaleString()}</td><td>{f.is_anomaly?'Flagged':'No'}</td></tr>)}</tbody></table></div><p className="footnote">{congestion.note}</p></section>
  </>;
}
'@

$Files['frontend\src\services\api.ts'] = @'
export type Summary = {
  total_flows: number;
  anomaly_count: number;
  anomaly_rate: number;
  total_bytes: number;
  protocol_distribution: { name: string; value: number }[];
  top_anomalous_sources: { ip: string; count: number }[];
  latest_timestamp: string | null;
  data_mode: string;
};
export type Flow = {
  id: number; timestamp: string; src_ip: string; dst_ip: string;
  protocol: string; src_port: number; dst_port: number;
  duration: number; packets: number; bytes: number;
  anomaly_score: number; is_anomaly: boolean; pc1: number; pc2: number;
};
export type Trend = { hour: string; flows: number; anomalies: number; bytes: number };
export type ProjectionPoint = { id: number; x: number; y: number; anomaly: boolean };
export type Congestion = {
  threshold_bytes_per_second: number;
  high_throughput_flows: {
    id: number; src_ip: string; dst_ip: string;
    bytes_per_second: number; is_anomaly: boolean;
  }[];
  note: string;
};
export type Recommendation = { priority: string; title: string; detail: string };

export async function apiGet<T>(route: string): Promise<T> {
  const response = await fetch(route);
  if (!response.ok) throw new Error(`API error ${response.status}: ${route}`);
  return response.json() as Promise<T>;
}
'@

$Files['frontend\vite.config.ts'] = @'
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:8000', '/health': 'http://127.0.0.1:8000' },
  },
});
'@

$Files['frontend\index.html'] = @'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CyberSentinel — Network Intelligence</title>
    <meta name="description" content="Unsupervised network-flow anomaly detection dashboard" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
'@

foreach ($Relative in $Files.Keys) {
  $Path = Join-Path $ProjectRoot $Relative
  $Parent = Split-Path -Parent $Path
  if (-not (Test-Path $Parent)) { New-Item -ItemType Directory -Force -Path $Parent | Out-Null }
  [System.IO.File]::WriteAllText($Path, $Files[$Relative] + "`n", (New-Object System.Text.UTF8Encoding($false)))
  Write-Host "Wrote $Relative"
}
Write-Host "Frontend source ready. Now run: cd frontend; npm install react-router-dom recharts lucide-react; npm run dev"
