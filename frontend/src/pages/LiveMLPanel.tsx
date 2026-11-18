
import { useEffect, useState } from 'react';

import {
  BrainCircuit,
  RefreshCw,
  ShieldAlert
} from 'lucide-react';

import './LiveMLPanel.css';


type Alert = {
  source: string;
  destination: string;
  source_port: number | null;
  destination_port: number | null;
  protocol: string;
  packets: number;
  bytes: number;
  score: number;
};


type LiveModel = {
  trained: boolean;
  state: string;
  training_flows: number;
  eligible_flows: number;
  scored_flows: number;
  flagged_flows: number;
  pca_dimensions: number | null;
  message: string;
  anomalies: Alert[];
};


type Status = {
  running: boolean;
  stopping: boolean;
  started_at: string | null;
  total_packets: number;
  average_packets_per_second: number;
  average_bytes_per_second: number;
  ml: LiveModel;
};


async function getStatus(): Promise<Status> {
  const response = await fetch(
    '/api/live/status'
  );

  if (!response.ok) {
    throw new Error(
      `Backend HTTP ${response.status}`
    );
  }

  return response.json() as Promise<Status>;
}


export default function LiveMLPanel() {
  const [status, setStatus] =
    useState<Status | null>(null);

  const [busy, setBusy] =
    useState(false);

  const [error, setError] =
    useState('');

  const [feedback, setFeedback] =
    useState('');


  // ------------------------------------------
  // LIVE UPDATES
  // ------------------------------------------

  useEffect(() => {
    let mounted = true;

    const refresh = async () => {
      try {
        const next = await getStatus();

        if (mounted) {
          setStatus(next);
        }

      } catch (problem) {
        if (mounted) {
          setError(String(problem));
        }
      }
    };

    void refresh();

    const interval = window.setInterval(
      () => void refresh(),
      2000
    );

    return () => {
      mounted = false;
      window.clearInterval(interval);
    };

  }, []);


  // ------------------------------------------
  // TRAIN LIVE MODEL
  // ------------------------------------------

  async function train() {
    setBusy(true);
    setError('');
    setFeedback('');

    try {
      const response = await fetch(
        '/api/live/model/train',
        {
          method: 'POST'
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.detail ??
          `HTTP ${response.status}`
        );
      }

      setFeedback(
        `Baseline trained on ${result.training_flows} ` +
        `flows (${result.pca_dimensions} PCA components). ` +
        'Start a NEW capture.'
      );

      setStatus(
        await getStatus()
      );

    } catch (problem) {
      setError(
        problem instanceof Error
          ? problem.message
          : String(problem)
      );

    } finally {
      setBusy(false);
    }
  }


  const ml = status?.ml;


  return (
    <section className="panel cs-live-ml">

      <div className="panel-heading">
        <div>
          <h2>
            <BrainCircuit size={19} />
            5. Live Flow Anomaly Screening
          </h2>

          <p>
            Separate local PCA + Isolation Forest model,
            trained using ordinary traffic from your
            own device.
          </p>
        </div>
      </div>


      <p className="cs-live-ml-guide">
        <strong>First use:</strong> capture ordinary
        browsing traffic, stop capture, then train
        the baseline. Start a <strong>new capture</strong>
        {' '}to classify new flows as unusual or not.
        A flagged flow is not a confirmed attack.
      </p>


      <div className="cs-live-ml-actions">

        <button
          type="button"
          disabled={
            busy ||
            !!status?.running ||
            !!status?.stopping ||
            !status?.started_at
          }
          onClick={() => void train()}
        >
          <BrainCircuit size={16} />
          {busy
            ? 'Training...'
            : 'Train / Replace Live Baseline'}
        </button>


        <button
          type="button"
          onClick={() => void getStatus()
            .then(setStatus)
            .catch((error) =>
              setError(String(error))
            )
          }
        >
          <RefreshCw size={16} />
          Refresh
        </button>

      </div>


      {error && (
        <p
          role="alert"
          className="cs-live-ml-error"
        >
          {error}
        </p>
      )}


      {feedback && (
        <p className="cs-live-ml-success">
          {feedback}
        </p>
      )}


      <p className="cs-live-ml-state">
        {ml?.message ?? 'Waiting for backend...'}
      </p>


      {/* MODEL METRICS */}

      <div className="cs-live-ml-grid">

        <div>
          <span>Baseline flows</span>
          <strong>
            {ml?.training_flows ?? 0}
          </strong>
        </div>

        <div>
          <span>New flows scored</span>
          <strong>
            {ml?.scored_flows ?? 0}
          </strong>
        </div>

        <div>
          <span>Unusual flows flagged</span>
          <strong>
            {ml?.flagged_flows ?? 0}
          </strong>
        </div>

        <div>
          <span>Average packet rate</span>
          <strong>
            {(
              status?.average_packets_per_second ?? 0
            ).toFixed(2)}/s
          </strong>
        </div>

      </div>


      {/* FLAGGED FLOW TABLE */}

      <h3>
        <ShieldAlert size={16} />
        Flagged Live Flows
      </h3>


      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Source</th>
              <th>Destination</th>
              <th>Protocol</th>
              <th>Packets</th>
              <th>Bytes</th>
              <th>Outlier Score</th>
            </tr>
          </thead>

          <tbody>

            {(ml?.anomalies ?? []).map(
              (item, index) => (

                <tr
                  key={
                    `${item.source}-${item.destination}-${index}`
                  }
                >

                  <td>
                    {item.source}
                    {item.source_port == null
                      ? ''
                      : `:${item.source_port}`}
                  </td>

                  <td>
                    {item.destination}
                    {item.destination_port == null
                      ? ''
                      : `:${item.destination_port}`}
                  </td>

                  <td>{item.protocol}</td>

                  <td>{item.packets}</td>

                  <td>
                    {item.bytes.toLocaleString()}
                  </td>

                  <td>
                    {item.score.toFixed(4)}
                  </td>

                </tr>

              )
            )}

            {!(ml?.anomalies.length) && (
              <tr>
                <td colSpan={6}>
                  No outlier results yet.
                  Train a baseline and start
                  another capture.
                </td>
              </tr>
            )}

          </tbody>
        </table>
      </div>


      <p className="cs-live-ml-guide">
        The live model is not the UNSW-NB15 classifier.
        It uses locally measured flow features;
        no attack labels or verified classification
        accuracy are available.

        After stopping the capture, use
        Save Capture to History below to include
        these results and graphs in the PDF report.
      </p>

    </section>
  );
}
