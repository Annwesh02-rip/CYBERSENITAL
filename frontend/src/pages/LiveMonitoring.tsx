
import { useEffect, useState } from 'react';

import {
  Activity,
  Network,
  Play,
  Radio,
  RefreshCw,
  Square,
  Wifi
} from 'lucide-react';

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';

import './LiveMonitoring.css';


type NetworkInterface = {
  name: string;
  is_default: boolean;
};

type InterfaceResponse = {
  default: string;
  interfaces: NetworkInterface[];
};

type Flow = {
  source: string;
  destination: string;
  source_port: number | null;
  destination_port: number | null;
  protocol: string;
  packets: number;
  bytes: number;
  last_seen: string;
};

type LiveStatus = {
  running: boolean;
  stopping: boolean;
  interface: string | null;
  started_at: string | null;
  elapsed_seconds: number;
  error: string | null;

  total_packets: number;
  total_bytes: number;
  packets_per_second: number;
  bytes_per_second: number;
  active_flows: number;

  protocols: {
    name: string;
    packets: number;
  }[];

  timeline: {
    time: string;
    packets: number;
    kbps: number;
  }[];

  flows: Flow[];
  notice: string;
};


async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {

  const response = await fetch(
    endpoint,
    options
  );

  if (!response.ok) {
    const payload = await response
      .json()
      .catch(() => ({}));

    throw new Error(
      typeof payload.detail === 'string'
        ? payload.detail
        : `HTTP ${response.status}`
    );
  }

  return response.json() as Promise<T>;
}


function formatBytes(value: number) {

  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(2)} GB`;
  }

  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(2)} MB`;
  }

  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(2)} KB`;
  }

  return `${value.toFixed(0)} B`;
}


function formatPort(port: number | null) {
  return port === null ? '—' : String(port);
}


export default function LiveMonitoring() {

  const [interfaces, setInterfaces] =
    useState<NetworkInterface[]>([]);

  const [selectedInterface, setSelectedInterface] =
    useState('');

  const [status, setStatus] =
    useState<LiveStatus | null>(null);

  const [busy, setBusy] =
    useState(false);

  const [error, setError] =
    useState('');


  async function refreshStatus() {

    const result = await apiRequest<LiveStatus>(
      '/api/live/status'
    );

    setStatus(result);
  }


  async function loadInterfaces() {

    try {
      const result = await apiRequest<InterfaceResponse>(
        '/api/live/interfaces'
      );

      setInterfaces(result.interfaces);

    } catch (issue) {
      setError(
        issue instanceof Error
          ? issue.message
          : String(issue)
      );
    }
  }


  // -------------------------------------------
  // AUTOMATIC LIVE UPDATES
  // -------------------------------------------

  useEffect(() => {

    void loadInterfaces();

    void refreshStatus().catch((issue) => {
      setError(String(issue));
    });

    const timer = window.setInterval(() => {

      void refreshStatus().catch((issue) => {
        setError(String(issue));
      });

    }, 1500);

    return () => {
      window.clearInterval(timer);
    };

  }, []);


  // -------------------------------------------
  // START MONITORING
  // -------------------------------------------

  async function startCapture() {

    setBusy(true);
    setError('');

    try {

      const response = await apiRequest<LiveStatus>(
        '/api/live/start',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            interface: selectedInterface || null
          })
        }
      );

      setStatus(response);

    } catch (issue) {
      setError(
        issue instanceof Error
          ? issue.message
          : String(issue)
      );
    } finally {
      setBusy(false);
    }
  }


  // -------------------------------------------
  // STOP MONITORING
  // -------------------------------------------

  async function stopCapture() {

    setBusy(true);
    setError('');

    try {

      const response = await apiRequest<LiveStatus>(
        '/api/live/stop',
        { method: 'POST' }
      );

      setStatus(response);

    } catch (issue) {
      setError(
        issue instanceof Error
          ? issue.message
          : String(issue)
      );
    } finally {
      setBusy(false);
    }
  }


  const running = status?.running ?? false;
  const stopping = status?.stopping ?? false;

  const protocols = status?.protocols ?? [];
  const flows = status?.flows ?? [];
  const timeline = status?.timeline ?? [];

  const maximumProtocol = Math.max(
    1,
    ...protocols.map((item) => item.packets)
  );


  return (
    <div className="cs-live">

      {/* HEADING */}

      <div className="page-intro">

        <div>
          <div className="eyebrow">
            CYBERSENTINEL / NETWORK CAPTURE
          </div>

          <h1>Live Network Monitoring</h1>

          <p>
            Capture authorized traffic and view
            network activity in real time.
          </p>
        </div>

        <span
          className={
            `cs-live-badge ${
              running ? 'running' : ''
            }`
          }
        >
          <Radio size={14} />
          {running
            ? 'CAPTURING'
            : stopping
              ? 'STOPPING'
              : 'NOT CAPTURING'}
        </span>

      </div>


      {/* CAPTURE CONTROLS */}

      <section className="panel">

        <div className="panel-heading">
          <div>
            <h2>1. Network Capture Controls</h2>

            <p>
              Select a network adapter and start
              monitoring packet metadata.
            </p>
          </div>
        </div>

        <div className="cs-live-controls">

          <label className="cs-live-select">

            Network Interface

            <select
              value={selectedInterface}
              disabled={running || stopping || busy}
              onChange={(event) =>
                setSelectedInterface(
                  event.target.value
                )
              }
            >

              <option value="">
                Default network adapter
              </option>

              {interfaces.map((network) => (

                <option
                  value={network.name}
                  key={network.name}
                >
                  {network.name}
                  {network.is_default
                    ? ' (default)'
                    : ''}
                </option>

              ))}

            </select>

          </label>


          <button
            type="button"
            className="cs-live-button start"
            disabled={running || stopping || busy}
            onClick={() => void startCapture()}
          >
            <Play size={16} />
            Start Capture
          </button>


          <button
            type="button"
            className="cs-live-button stop"
            disabled={!running || busy}
            onClick={() => void stopCapture()}
          >
            <Square size={15} />
            Stop Capture
          </button>


          <button
            type="button"
            className="cs-live-button"
            disabled={busy}
            onClick={() => {
              void loadInterfaces();
              void refreshStatus();
            }}
          >
            <RefreshCw size={16} />
            Refresh
          </button>

        </div>


        {error && (
          <div
            className="cs-live-error"
            role="alert"
          >
            {error}
          </div>
        )}


        {status?.error && (
          <div
            className="cs-live-error"
            role="alert"
          >
            {status.error}
          </div>
        )}


        <p className="cs-live-note">
          Captures traffic on the selected local
          interface. Npcap and appropriate capture
          permissions are required on Windows.
          No packet payloads are stored.
        </p>

        {status?.interface && (
          <p className="cs-live-note">
            Selected capture interface:
            {' '}
            <strong>{status.interface}</strong>
          </p>
        )}

      </section>


      {/* LIVE METRICS */}

      <div className="cs-live-metrics">

        {[
          {
            label: 'Captured Packets',
            value: (
              status?.total_packets ?? 0
            ).toLocaleString(),
            icon: <Network size={20} />
          },
          {
            label: 'Captured Data',
            value: formatBytes(
              status?.total_bytes ?? 0
            ),
            icon: <Wifi size={20} />
          },
          {
            label: 'Packet Rate',
            value: (
              status?.packets_per_second ?? 0
            ).toFixed(1) + ' pkt/s',
            icon: <Activity size={20} />
          },
          {
            label: 'Active Flows',
            value: String(
              status?.active_flows ?? 0
            ),
            icon: <Radio size={20} />
          }
        ].map((metric) => (

          <div
            key={metric.label}
            className="panel cs-live-metric"
          >

            {metric.icon}

            <span>{metric.label}</span>

            <strong>{metric.value}</strong>

          </div>

        ))}

      </div>


      {/* LIVE TRAFFIC CHART */}

      <section className="panel">

        <div className="panel-heading">
          <div>
            <h2>2. Real-Time Traffic Activity</h2>

            <p>
              Captured traffic volume over
              the last 30 seconds.
            </p>
          </div>

          <span className="cs-live-rate">
            {formatBytes(
              status?.bytes_per_second ?? 0
            )}/s
          </span>
        </div>


        <div className="cs-live-chart">

          <ResponsiveContainer
            width="100%"
            height="100%"
          >

            <LineChart data={timeline}>

              <CartesianGrid
                stroke="#e4e9ec"
                strokeDasharray="3 3"
              />

              <XAxis
                dataKey="time"
                tick={{ fontSize: 10 }}
                interval={5}
              />

              <YAxis
                tick={{ fontSize: 11 }}
              />

              <Tooltip />

              <Line
                type="monotone"
                dataKey="kbps"
                name="Captured KB/s"
                stroke="#1a7b85"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />

            </LineChart>

          </ResponsiveContainer>

        </div>

      </section>


      {/* PROTOCOL DISTRIBUTION */}

      <section className="panel">

        <div className="panel-heading">
          <div>
            <h2>3. Protocol Distribution</h2>

            <p>
              Observed packet counts by protocol.
            </p>
          </div>
        </div>


        {protocols.length === 0 ? (

          <p className="cs-live-note">
            No IP or ARP traffic has been
            captured yet.
          </p>

        ) : (

          <div className="cs-live-protocols">

            {protocols.map((protocol) => (

              <div
                className="cs-live-protocol"
                key={protocol.name}
              >

                <div className="cs-live-protocol-top">

                  <strong>{protocol.name}</strong>

                  <span>
                    {protocol.packets.toLocaleString()}
                    {' '}packets
                  </span>

                </div>

                <div className="cs-live-track">

                  <div
                    style={{
                      width: `${
                        100 * protocol.packets /
                        maximumProtocol
                      }%`
                    }}
                  />

                </div>

              </div>

            ))}

          </div>

        )}

      </section>


      {/* NETWORK FLOWS */}

      <section className="panel">

        <div className="panel-heading">
          <div>
            <h2>4. Observed Network Flows</h2>

            <p>
              Top captured flows by traffic volume.
            </p>
          </div>
        </div>


        <div className="table-scroll">

          <table>

            <thead>
              <tr>
                <th>Source</th>
                <th>Destination</th>
                <th>Protocol</th>
                <th>Packets</th>
                <th>Bytes</th>
                <th>Last Seen</th>
              </tr>
            </thead>

            <tbody>

              {flows.map((flow, index) => (

                <tr key={
                  `${flow.source}-${flow.destination}-` +
                  `${flow.source_port}-${flow.destination_port}-` +
                  `${flow.protocol}-${index}`
                }>

                  <td>
                    {flow.source}:
                    {formatPort(flow.source_port)}
                  </td>

                  <td>
                    {flow.destination}:
                    {formatPort(flow.destination_port)}
                  </td>

                  <td>{flow.protocol}</td>

                  <td>
                    {flow.packets.toLocaleString()}
                  </td>

                  <td>
                    {formatBytes(flow.bytes)}
                  </td>

                  <td>{flow.last_seen}</td>

                </tr>

              ))}

              {flows.length === 0 && (

                <tr>
                  <td colSpan={6}>
                    No network flows captured yet.
                  </td>
                </tr>

              )}

            </tbody>

          </table>

        </div>

      </section>


      {/* MONITORING LIMITATIONS */}

      <section className="panel">

        <h2>Monitoring Information</h2>

        <p className="cs-live-note">
          {status?.notice ??
            'Start capture to monitor network metadata.'}
        </p>

        <p className="cs-live-note">
          Monitoring is local and session-based.
          Starting a new session resets the
          live counters. This module does not
          yet classify live flows with the
          UNSW-NB15 machine learning models.
        </p>

      </section>

    </div>
  );
}
