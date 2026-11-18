
import { useState } from 'react';

import { Link } from 'react-router-dom';

import {
  Database,
  Download,
  FileDown,
  Save
} from 'lucide-react';

import './LiveMonitoring.css';


type CaptureStatus = {
  started_at: string | null;
  total_packets: number;
  total_bytes: number;
  running: boolean;
};


type SavedCapture = {
  history_id: number;
  created_at: string;
  source: string;
  captured_packets: number;
  captured_bytes: number;
  report_url: string;
  csv_url: string;
};


async function getError(response: Response) {
  const body = await response
    .json()
    .catch(() => ({}));

  return typeof body.detail === 'string'
    ? body.detail
    : `Request failed (HTTP ${response.status})`;
}


export default function LiveCaptureReports() {

  const [saving, setSaving] = useState(false);

  const [error, setError] = useState('');

  const [saved, setSaved] =
    useState<SavedCapture | null>(null);


  async function saveCapture() {

    setSaving(true);
    setError('');

    try {

      // Check whether real packets have been
      // captured before saving a report.

      const statusResponse = await fetch(
        '/api/live/status'
      );

      if (!statusResponse.ok) {
        throw new Error(
          await getError(statusResponse)
        );
      }

      const status =
        await statusResponse.json() as CaptureStatus;

      if (!status.started_at) {
        throw new Error(
          'Start a live capture session first.'
        );
      }

      if (status.total_packets === 0) {
        throw new Error(
          'No packets captured yet. Generate some ' +
          'network traffic before saving.'
        );
      }

      // Save the current capture snapshot
      // to the existing SQLite history.

      const response = await fetch(
        '/api/live/save',
        {
          method: 'POST'
        }
      );

      if (!response.ok) {
        throw new Error(
          await getError(response)
        );
      }

      const result =
        await response.json() as SavedCapture;

      setSaved(result);

    } catch (issue) {

      setError(
        issue instanceof Error
          ? issue.message
          : String(issue)
      );

    } finally {

      setSaving(false);

    }
  }


  return (
    <section
      className="panel"
      style={{ marginTop: 20 }}
    >

      <div className="panel-heading">

        <div>
          <h2>
            5. Save Live Capture & Generate Report
          </h2>

          <p>
            Save the current traffic statistics,
            protocol information and flow metadata.
          </p>
        </div>

      </div>


      <div className="cs-live-controls">

        <button
          type="button"
          className="cs-live-button start"
          disabled={saving}
          onClick={() => void saveCapture()}
        >
          <Save size={16} />

          {saving
            ? 'Saving Capture...'
            : 'Save Capture to History'}
        </button>


        {saved && (

          <>

            <a
              className="cs-live-button"
              href={saved.report_url}
            >
              <Download size={16} />
              Download PDF Report
            </a>


            <a
              className="cs-live-button"
              href={saved.csv_url}
            >
              <FileDown size={16} />
              Download Flow CSV
            </a>


            <Link
              className="cs-live-button"
              to="/history"
            >
              <Database size={16} />
              View Analysis History
            </Link>

          </>

        )}

      </div>


      {saved && (

        <div
          style={{
            marginTop: 16,
            padding: 14,
            borderRadius: 9,
            background: '#eaf6f0',
            color: '#176a57'
          }}
        >

          <strong>
            Capture saved successfully!
          </strong>

          <p style={{ marginTop: 6, fontSize: 13 }}>
            History ID: #{saved.history_id}
          </p>

          <p style={{ fontSize: 13 }}>
            Captured packets:
            {' '}
            {saved.captured_packets.toLocaleString()}
          </p>

          <p style={{ fontSize: 13 }}>
            Captured data:
            {' '}
            {(
              saved.captured_bytes / 1_000_000
            ).toFixed(2)}
            {' '}MB
          </p>

        </div>

      )}


      {error && (

        <div
          className="cs-live-error"
          role="alert"
        >
          {error}
        </div>

      )}


      <p className="cs-live-note">
        This saves a snapshot of the current capture
        session. For a final report, stop the capture
        first, then click Save Capture to History.
        The report contains traffic metadata, not
        machine learning attack predictions.
      </p>

    </section>
  );
}
