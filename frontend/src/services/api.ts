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
