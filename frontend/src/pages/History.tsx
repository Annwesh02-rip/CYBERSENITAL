
import {
  useEffect,
  useState
} from 'react';

import { Link } from 'react-router-dom';

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';

import './History.css';
import './V2Workbench.css';


type Entry = {
  id: number;
  source: string;
  created_at: string;
  rows_analyzed: number;
};


type Metrics = {
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  false_positive_rate: number;
  confusion_matrix: number[][];
};


type HistoryRecord = {
  history_id: number;
  source: string;
  created_at: string;
  analysis_type?: string;
  rows_analyzed: number;

  flagged?: number;
  selected_model?: string;
  metrics?: Metrics | null;

  protocol_distribution?: {
    name: string;
    value: number;
  }[];

  live?: {
    interface?: string;
    total_packets?: number;
    total_bytes?: number;
    elapsed_seconds?: number;
    average_packets_per_second?: number;

    protocols?: {
      name: string;
      packets: number;
    }[];

    flows?: {
      source: string;
      destination: string;
      protocol: string;
      packets: number;
      bytes: number;
    }[];

    ml?: {
      state?: string;
      scored_flows?: number;
      flagged_flows?: number;
    };
  };
};


type ListResponse = {
  runs: Entry[];
  total: number;
};


async function fetchJson<T>(
  url: string
): Promise<T> {

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(
      `History request failed: HTTP ${response.status}`
    );
  }

  return response.json() as Promise<T>;
}


export default function History() {

  const [runs, setRuns] =
    useState<Entry[]>([]);

  const [selected, setSelected] =
    useState<HistoryRecord | null>(null);

  const [busy, setBusy] =
    useState(false);

  const [error, setError] =
    useState('');


  // ------------------------------------------
  // OPEN SAVED ANALYSIS
  // ------------------------------------------

  async function openEntry(id: number) {

    try {

      const record =
        await fetchJson<HistoryRecord>(
          `/api/history/runs/${id}`
        );

      setSelected(record);

    } catch (issue) {

      setError(String(issue));

    }
  }


  // ------------------------------------------
  // RELOAD ANALYSIS HISTORY
  // ------------------------------------------

  async function reload() {

    setBusy(true);
    setError('');

    try {

      const data =
        await fetchJson<ListResponse>(
          '/api/history/runs?limit=100'
        );

      // Preserve older history in SQLite.
      // Display only V2 and live sessions.

      const visible = data.runs.filter(
        run => (

          run.source?.startsWith(
            'UNSW-NB15 V2 - '
          )

          ||

          run.source?.startsWith(
            'Live Capture - '
          )

        )
      );

      setRuns(visible);

      if (visible.length) {

        await openEntry(
          visible[0].id
        );

      } else {

        setSelected(null);

      }

    } catch (issue) {

      setError(String(issue));

    } finally {

      setBusy(false);

    }
  }


  useEffect(() => {
    void reload();
  }, []);


  // ------------------------------------------
  // DELETE SAVED ANALYSIS
  // ------------------------------------------

  async function remove(id: number) {

    if (!window.confirm(
      `Delete saved report #${id}?`
    )) {
      return;
    }

    setBusy(true);
    setError('');

    try {

      const response = await fetch(
        `/api/history/runs/${id}`,
        {
          method: 'DELETE'
        }
      );

      if (!response.ok) {
        throw new Error(
          `Delete failed (HTTP ${response.status})`
        );
      }

      await reload();

    } catch (issue) {

      setError(String(issue));

    } finally {

      setBusy(false);

    }
  }


  // ------------------------------------------
  // DETERMINE REPORT TYPE
  // ------------------------------------------

  const isV2 = (
    selected?.analysis_type === 'v2_dataset'
  );

  const isLive = (
    selected?.analysis_type === 'live_capture'
  );

  const id = selected?.history_id;


  const pdfUrl = id == null
    ? ''
    : isV2
      ? `/api/model-v2/history/${id}/report.pdf`
      : `/api/history/runs/${id}/report.pdf`;


  const csvUrl = id == null
    ? ''
    : isV2
      ? `/api/model-v2/history/${id}/predictions.csv`
      : `/api/history/runs/${id}/flows.csv`;


  const plot = isV2

    ? (
        selected?.protocol_distribution ?? []
      )

    : (
        selected?.live?.protocols ?? []
      ).map(
        protocol => ({
          name: protocol.name,
          value: protocol.packets
        })
      );


  return (
    <div className="v2-workbench">

      {/* HISTORY HEADER */}

      <section className="panel">

        <div className="eyebrow">
          CYBERSENTINEL / SAVED ANALYSES
        </div>

        <h1>
          History & Reports
        </h1>

        <p className="v2-note">
          View V2 dataset analyses and real live
          capture sessions. Earlier original-model
          records are retained in the database
          but hidden from the active view.
        </p>


        <div className="v2-controls">

          <Link
            className="v2-export"
            to="/analyze"
          >
            Analyze with V2
          </Link>

          <Link
            className="v2-export"
            to="/live"
          >
            Live Capture
          </Link>

          <button
            type="button"
            disabled={busy}
            onClick={() =>
              void reload()
            }
          >
            Refresh
          </button>

        </div>


        {error && (
          <p
            className="v2-error"
            role="alert"
          >
            {error}
          </p>
        )}

      </section>


      {/* SAVED RUNS */}

      <section className="panel">

        <h2>
          Saved Sessions ({runs.length} shown)
        </h2>


        <div className="table-scroll">

          <table>

            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>Saved</th>
                <th>Records / Packets</th>
                <th>Actions</th>
              </tr>
            </thead>


            <tbody>

              {runs.map(run => (

                <tr key={run.id}>

                  <td>#{run.id}</td>

                  <td>
                    {run.source.startsWith(
                      'Live Capture - '
                    )
                      ? 'Live Capture'
                      : 'V2 Dataset'}
                  </td>

                  <td>
                    {new Date(
                      run.created_at
                    ).toLocaleString()}
                  </td>

                  <td>
                    {run.rows_analyzed
                      .toLocaleString()}
                  </td>

                  <td>

                    <button
                      type="button"
                      disabled={busy}
                      onClick={() =>
                        void openEntry(run.id)
                      }
                    >
                      View
                    </button>

                  </td>

                </tr>

              ))}


              {!runs.length && (

                <tr>
                  <td colSpan={5}>
                    No saved V2 analyses or
                    live captures yet.
                  </td>
                </tr>

              )}

            </tbody>

          </table>

        </div>

      </section>


      {selected && (

        <>

          {/* SELECTED REPORT */}

          <section className="panel">

            <h2>
              Report #{selected.history_id}:
              {' '}
              {isV2
                ? 'V2 Dataset Analysis'
                : isLive
                  ? 'Live Capture'
                  : 'Saved Record'}
            </h2>


            <p className="v2-note">
              {selected.source}
            </p>


            <div className="v2-controls">

              <a
                className="v2-export"
                href={pdfUrl}
              >
                Download Graphical PDF
              </a>

              <a
                className="v2-export"
                href={csvUrl}
              >
                {isV2
                  ? 'Download Predictions CSV'
                  : 'Download Flow CSV'}
              </a>

              <button
                type="button"
                disabled={busy}
                onClick={() =>
                  void remove(
                    selected.history_id
                  )
                }
              >
                Delete Report
              </button>

            </div>


            {/* V2 METRICS */}

            {isV2 && (

              <>

                <div className="v2-stat-grid">

                  <div>
                    <span>
                      Analyzed records
                    </span>

                    <strong>
                      {selected.rows_analyzed
                        .toLocaleString()}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Flagged anomalies
                    </span>

                    <strong>
                      {(selected.flagged ?? 0)
                        .toLocaleString()}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Detector
                    </span>

                    <strong>
                      {selected.selected_model ?? 'V2'}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Threshold
                    </span>

                    <strong>
                      Validation-calibrated
                    </strong>
                  </div>

                </div>


                {selected.metrics ? (

                  <>

                    <h3>
                      Saved Evaluation Metrics
                    </h3>


                    <div className="v2-stat-grid">

                      <div>
                        <span>Accuracy</span>

                        <strong>
                          {(
                            selected.metrics.accuracy
                            * 100
                          ).toFixed(2)}%
                        </strong>
                      </div>

                      <div>
                        <span>Precision</span>

                        <strong>
                          {(
                            selected.metrics.precision
                            * 100
                          ).toFixed(2)}%
                        </strong>
                      </div>

                      <div>
                        <span>Recall</span>

                        <strong>
                          {(
                            selected.metrics.recall
                            * 100
                          ).toFixed(2)}%
                        </strong>
                      </div>

                      <div>
                        <span>F1-score</span>

                        <strong>
                          {(
                            selected.metrics.f1
                            * 100
                          ).toFixed(2)}%
                        </strong>
                      </div>

                    </div>


                    <p className="v2-note">
                      Confusion matrix:
                      {' '}
                      {JSON.stringify(
                        selected.metrics.confusion_matrix
                      )}
                    </p>

                  </>

                ) : (

                  <p className="v2-note">
                    No ground-truth labels were
                    provided. Accuracy is unavailable.
                  </p>

                )}

              </>

            )}


            {/* LIVE CAPTURE METRICS */}

            {isLive && selected.live && (

              <>

                <div className="v2-stat-grid">

                  <div>
                    <span>Captured packets</span>

                    <strong>
                      {selected.live.total_packets
                        ?.toLocaleString() ?? '-'}
                    </strong>
                  </div>

                  <div>
                    <span>Captured bytes</span>

                    <strong>
                      {selected.live.total_bytes
                        ?.toLocaleString() ?? '-'}
                    </strong>
                  </div>

                  <div>
                    <span>Duration</span>

                    <strong>
                      {selected.live.elapsed_seconds
                        ?? '-'} s
                    </strong>
                  </div>

                  <div>
                    <span>Live outliers</span>

                    <strong>
                      {selected.live.ml?.flagged_flows
                        ?? 'Not scored'}
                    </strong>
                  </div>

                </div>


                <p className="v2-note">
                  Live-flow baseline state:
                  {' '}
                  {selected.live.ml?.state
                    ?? 'not recorded'}.

                  This detector is separate
                  from UNSW-NB15 V2.
                </p>

              </>

            )}

          </section>


          {/* PROTOCOL GRAPH */}

          {plot.length > 0 && (

            <section className="panel">

              <h2>
                Saved Protocol Distribution
              </h2>

              <div className="v2-chart">

                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >

                  <BarChart data={plot}>

                    <CartesianGrid
                      strokeDasharray="3 3"
                    />

                    <XAxis
                      dataKey="name"
                    />

                    <YAxis
                      allowDecimals={false}
                    />

                    <Tooltip />

                    <Bar
                      dataKey="value"
                      name="Records / packets"
                      fill="#23848b"
                    />

                  </BarChart>

                </ResponsiveContainer>

              </div>

            </section>

          )}


          {/* LIVE FLOWS */}

          {isLive && (
            selected.live?.flows?.length ?? 0
          ) > 0 && (

            <section className="panel">

              <h2>
                Saved Network Flows
              </h2>


              <div className="table-scroll">

                <table>

                  <thead>
                    <tr>
                      <th>Source</th>
                      <th>Destination</th>
                      <th>Protocol</th>
                      <th>Packets</th>
                      <th>Bytes</th>
                    </tr>
                  </thead>


                  <tbody>

                    {selected.live?.flows
                      ?.slice(0, 30)
                      .map((flow, index) => (

                        <tr key={index}>

                          <td>{flow.source}</td>
                          <td>{flow.destination}</td>
                          <td>{flow.protocol}</td>
                          <td>{flow.packets}</td>
                          <td>{flow.bytes}</td>

                        </tr>

                      ))}

                  </tbody>

                </table>

              </div>

            </section>

          )}

        </>

      )}

    </div>
  );
}
