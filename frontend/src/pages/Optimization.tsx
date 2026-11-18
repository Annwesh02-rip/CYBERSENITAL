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
