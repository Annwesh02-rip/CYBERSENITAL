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
  if (!congestion) return <StateMessage message="Loading traffic analysisâ€¦" />;
  return <><div className="page-intro"><div><div className="eyebrow">TRAFFIC OBSERVABILITY</div><h1>Traffic Analysis</h1><p>Analyze volume trends and identify high-throughput flow bursts.</p></div><span className="data-pill">Flow-derived estimates</span></div>
    <section className="panel"><div className="panel-heading"><div><h2>Hourly traffic volume</h2><p>Summed bytes observed in the demonstration flow dataset</p></div></div><div className="chart-area"><ResponsiveContainer width="100%" height="100%"><BarChart data={trends}><CartesianGrid stroke="#edf1f4" vertical={false}/><XAxis dataKey="hour" tick={{fontSize:11}} minTickGap={20}/><YAxis tickFormatter={(v:number)=>`${(v/1e6).toFixed(0)}M`} tick={{fontSize:11}}/><Tooltip formatter={(v)=>`${(Number(v)/1e6).toFixed(2)} MB`}/><Bar dataKey="bytes" fill="#217985" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></div></section>
    <section className="panel"><div className="panel-heading"><div><h2>High-throughput flow indicators</h2><p>Top-decile threshold: {congestion.threshold_bytes_per_second.toLocaleString()} bytes/s</p></div><span className="tag">NOT CONFIRMED CONGESTION</span></div><div className="table-scroll"><table><thead><tr><th>ID</th><th>Source</th><th>Destination</th><th>Rate (bytes/s)</th><th>Anomaly</th></tr></thead><tbody>{congestion.high_throughput_flows.map(f=><tr key={f.id}><td>#{f.id}</td><td className="mono">{f.src_ip}</td><td className="mono">{f.dst_ip}</td><td>{f.bytes_per_second.toLocaleString()}</td><td>{f.is_anomaly?'Flagged':'No'}</td></tr>)}</tbody></table></div><p className="footnote">{congestion.note}</p></section>
  </>;
}
