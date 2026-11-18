
import { useMemo, useState } from 'react';

import { Link } from 'react-router-dom';

import {
  Activity,
  Database,
  Download,
  FileDown,
  Layers,
  Play,
  ShieldAlert,
  Upload
} from 'lucide-react';

import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';

import './AnalyzeTraffic.css';

// ---------------------------------------------
// TYPES
// ---------------------------------------------

type ModelType = 'original' | 'pca';

type Metrics = {
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  roc_auc?: number;
  pr_auc?: number;
  confusion_matrix: number[][];
};

type TrafficRecord = {
  row: number;
  proto: string;
  service: string;
  state: string;
  duration: number;
  sbytes: number;
  dbytes: number;
  rate_bytes_s: number;
  pc1: number;
  pc2: number;
  raw_flag: boolean;
  pca_flag: boolean;
  raw_score: number;
  pca_score: number;
  actual_attack: number | null;
  attack_cat: string | null;
};

type AnalysisResult = {
  history_id: number;
  created_at: string;
  source: string;
  rows_analyzed: number;
  truncated: boolean;
  encoded_features: number;
  pca_features: number;
  flagged_original: number;
  flagged_pca: number;
  total_bytes: number;
  high_rate_count: number;
  has_labels: boolean;
  original_metrics: Metrics | null;
  pca_metrics: Metrics | null;
  protocol_distribution: {
    name: string;
    value: number;
  }[];
  recommendations: string[];
  rows: TrafficRecord[];
  note: string;
};

// ---------------------------------------------
// API
// ---------------------------------------------

async function analyzeRequest(
  endpoint: string,
  formData?: FormData
): Promise<AnalysisResult> {
  const response = await fetch(endpoint, {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    const errorBody = await response
      .json()
      .catch(() => ({}));

    const detail = errorBody.detail;

    throw new Error(
      typeof detail === 'string'
        ? detail
        : `Analysis failed: HTTP ${response.status}`
    );
  }

  return response.json() as Promise<AnalysisResult>;
}

// ---------------------------------------------
// UTILITIES
// ---------------------------------------------

function percentage(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}

function csvCell(value: unknown) {
  let text = value == null ? '' : String(value);

  // Prevent spreadsheet formula injection.
  if (/^\s*[=+\-@]/.test(text)) {
    text = `'${text}`;
  }

  return `"${text.replace(/"/g, '""')}"`;
}

function exportPredictions(
  records: TrafficRecord[],
  model: ModelType
) {
  const headings = [
    'row',
    'proto',
    'service',
    'state',
    'duration',
    'sbytes',
    'dbytes',
    'pc1',
    'pc2',
    'anomaly_score',
    'predicted_anomaly',
    'actual_attack',
    'attack_cat'
  ];

  const values = records.map((record) => {
    const score =
      model === 'pca'
        ? record.pca_score
        : record.raw_score;

    const flagged =
      model === 'pca'
        ? record.pca_flag
        : record.raw_flag;

    return [
      record.row,
      record.proto,
      record.service,
      record.state,
      record.duration,
      record.sbytes,
      record.dbytes,
      record.pc1,
      record.pc2,
      score,
      flagged ? 1 : 0,
      record.actual_attack,
      record.attack_cat
    ].map(csvCell).join(',');
  });

  const content = [
    headings.join(','),
    ...values
  ].join('\r\n');

  const blob = new Blob(
    [content],
    { type: 'text/csv;charset=utf-8' }
  );

  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');

  anchor.href = url;
  anchor.download =
    `CyberSentinel_${model}_predictions.csv`;

  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ---------------------------------------------
// COMPONENT
// ---------------------------------------------

export default function AnalyzeTraffic() {
  const [file, setFile] =
    useState<File | null>(null);

  const [result, setResult] =
    useState<AnalysisResult | null>(null);

  const [model, setModel] =
    useState<ModelType>('pca');

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState('');

  const [selectedRow, setSelectedRow] =
    useState<number | null>(null);

  const [onlyFlagged, setOnlyFlagged] =
    useState(false);

  const [search, setSearch] =
    useState('');

  const [page, setPage] =
    useState(0);

  // ---------------------------------------------
  // RUN ANALYSIS AND SAVE TO SQLITE
  // ---------------------------------------------

  async function runAnalysis(
    mode: 'sample' | 'upload'
  ) {
    if (mode === 'upload' && !file) {
      setError('Please select a CSV file.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      let output: AnalysisResult;

      if (mode === 'sample') {
        output = await analyzeRequest(
          '/api/history/sample?rows=1500'
        );
      } else {
        const body = new FormData();

        body.append('file', file as File);

        output = await analyzeRequest(
          '/api/history/upload',
          body
        );
      }

      setResult(output);

      setModel('pca');
      setSelectedRow(output.rows[0]?.row ?? null);
      setOnlyFlagged(false);
      setSearch('');
      setPage(0);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : String(err)
      );
    } finally {
      setLoading(false);
    }
  }

  // ---------------------------------------------
  // CURRENT MODEL
  // ---------------------------------------------

  const metrics =
    model === 'pca'
      ? result?.pca_metrics
      : result?.original_metrics;

  const flaggedCount =
    model === 'pca'
      ? result?.flagged_pca ?? 0
      : result?.flagged_original ?? 0;

  function isAnomaly(record: TrafficRecord) {
    return model === 'pca'
      ? record.pca_flag
      : record.raw_flag;
  }

  function anomalyScore(record: TrafficRecord) {
    return model === 'pca'
      ? record.pca_score
      : record.raw_score;
  }

  // ---------------------------------------------
  // RECORD FILTERING
  // ---------------------------------------------

  const filteredRecords = useMemo(() => {
    if (!result) return [];

    const query = search.trim().toLowerCase();

    return result.rows.filter((record) => {
      const flagged =
        model === 'pca'
          ? record.pca_flag
          : record.raw_flag;

      const matchesSearch =
        !query ||
        [
          record.row,
          record.proto,
          record.service,
          record.state,
          record.attack_cat
        ].some((value) =>
          String(value ?? '')
            .toLowerCase()
            .includes(query)
        );

      return (
        (!onlyFlagged || flagged) &&
        matchesSearch
      );
    });
  }, [result, model, onlyFlagged, search]);

  const recordsPerPage = 20;

  const pageCount = Math.max(
    1,
    Math.ceil(filteredRecords.length / recordsPerPage)
  );

  const visibleRecords = filteredRecords.slice(
    page * recordsPerPage,
    (page + 1) * recordsPerPage
  );

  const selected = result?.rows.find(
    (record) => record.row === selectedRow
  );

  // ---------------------------------------------
  // PCA VISUALIZATION DATA
  // ---------------------------------------------

  const plotRecords = useMemo(() => {
    if (!result) return [];

    const step = Math.max(
      1,
      Math.ceil(result.rows.length / 600)
    );

    return result.rows.filter(
      (_, index) => index % step === 0
    );
  }, [result]);

  const normalPoints = plotRecords.filter(
    (record) => !isAnomaly(record)
  );

  const anomalyPoints = plotRecords.filter(
    (record) => isAnomaly(record)
  );

  // ---------------------------------------------
  // UI
  // ---------------------------------------------

  return (
    <div className="cs-analysis">
      <div className="page-intro">
        <div>
          <div className="eyebrow">
            CYBERSENTINEL / MACHINE LEARNING
          </div>

          <h1>Analyze Network Traffic</h1>

          <p>
            Upload network traffic data, run
            anomaly detection and save analysis
            results automatically.
          </p>
        </div>

        <span className="data-pill">
          REAL DATASET ANALYSIS
        </span>
      </div>

      {/* DATASET SELECTION */}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>1. Select Network Dataset</h2>

            <p>
              Choose an UNSW-NB15 CSV or use
              the built-in testing dataset.
            </p>
          </div>
        </div>

        <div className="cs-analysis-actions">
          <label className="cs-analysis-upload">
            <Upload size={18} />

            <span>
              {file
                ? file.name
                : 'Choose CSV File'}
            </span>

            <input
              type="file"
              accept=".csv"
              onChange={(event) =>
                setFile(
                  event.target.files?.[0] ?? null
                )
              }
            />
          </label>

          <button
            type="button"
            className="cs-analysis-button primary"
            disabled={loading || !file}
            onClick={() => void runAnalysis('upload')}
          >
            <Play size={16} />
            Analyze Uploaded CSV
          </button>

          <button
            type="button"
            className="cs-analysis-button"
            disabled={loading}
            onClick={() => void runAnalysis('sample')}
          >
            <Database size={16} />
            Analyze Built-in Sample
          </button>
        </div>

        {loading && (
          <p className="cs-analysis-status">
            Processing network traffic, applying
            PCA, running anomaly detection and
            saving the analysis...
          </p>
        )}

        {error && (
          <div
            className="cs-analysis-error"
            role="alert"
          >
            {error}
          </div>
        )}

        <p className="cs-analysis-note">
          Uses your saved trained models.
          Up to 5,000 records can be analyzed
          per request. Only compatible
          UNSW-NB15 features are supported.
        </p>
      </section>

      {/* EMPTY STATE */}

      {!result ? (
        <section className="panel cs-analysis-empty">
          <Activity size={36} />

          <h2>Ready to Analyze Network Traffic</h2>

          <p>
            Click <strong>Analyze Built-in Sample</strong>
            {' '}to run your machine learning models
            on real network traffic data.
          </p>
        </section>
      ) : (
        <>
          {/* SAVED ANALYSIS */}

          <section className="panel cs-analysis-success">
            <div>
              <strong>
                Analysis Completed and Saved
              </strong>

              <p>
                Analysis #{result.history_id}
                {' · '}
                {result.source}
                {' · '}
                {result.rows_analyzed.toLocaleString()}
                {' '}records
              </p>
            </div>

            <div className="cs-analysis-actions">
              <Link
                className="cs-analysis-button"
                to="/history"
              >
                View History
              </Link>

              <a
                className="cs-analysis-button primary"
                href={
                  `/api/history/runs/` +
                  `${result.history_id}/report.pdf`
                }
              >
                <Download size={16} />
                Download PDF
              </a>
            </div>
          </section>

          {/* SUMMARY */}

          <div className="cs-analysis-metrics">
            <div className="panel cs-analysis-metric">
              <Database size={20} />

              <span>Records Analyzed</span>

              <strong>
                {result.rows_analyzed.toLocaleString()}
              </strong>
            </div>

            <div className="panel cs-analysis-metric">
              <Layers size={20} />

              <span>PCA Dimensions</span>

              <strong>
                {result.encoded_features}
                {' → '}
                {result.pca_features}
              </strong>
            </div>

            <div className="panel cs-analysis-metric">
              <ShieldAlert size={20} />

              <span>Flagged Anomalies</span>

              <strong>
                {flaggedCount.toLocaleString()}
              </strong>
            </div>

            <div className="panel cs-analysis-metric">
              <Activity size={20} />

              <span>Traffic Volume</span>

              <strong>
                {(
                  result.total_bytes / 1_000_000
                ).toFixed(2)} MB
              </strong>
            </div>
          </div>

          {/* MODEL COMPARISON */}

          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>2. Machine Learning Analysis</h2>

                <p>
                  Compare original Isolation Forest
                  with PCA-based anomaly detection.
                </p>
              </div>
            </div>

            <div className="cs-analysis-models">
              <button
                type="button"
                className={
                  model === 'original'
                    ? 'selected'
                    : ''
                }
                onClick={() => {
                  setModel('original');
                  setPage(0);
                }}
              >
                Original Isolation Forest
              </button>

              <button
                type="button"
                className={
                  model === 'pca'
                    ? 'selected'
                    : ''
                }
                onClick={() => {
                  setModel('pca');
                  setPage(0);
                }}
              >
                PCA + Isolation Forest
              </button>
            </div>

            {metrics ? (
              <div className="cs-analysis-metrics">
                {[
                  {
                    label: 'Accuracy',
                    value: metrics.accuracy
                  },
                  {
                    label: 'Precision',
                    value: metrics.precision
                  },
                  {
                    label: 'Recall',
                    value: metrics.recall
                  },
                  {
                    label: 'F1-score',
                    value: metrics.f1
                  }
                ].map((item) => (
                  <div
                    key={item.label}
                    className="cs-analysis-metric-small"
                  >
                    <span>{item.label}</span>
                    <strong>
                      {percentage(item.value)}
                    </strong>
                  </div>
                ))}
              </div>
            ) : (
              <p className="cs-analysis-note">
                No valid ground-truth labels were
                supplied. Anomaly predictions are
                available, but classification
                metrics cannot be computed.
              </p>
            )}
          </section>

          {/* PCA VISUALIZATION */}

          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>3. PCA Anomaly Visualization</h2>

                <p>
                  Two-dimensional network traffic
                  representation.
                </p>
              </div>
            </div>

            <div className="cs-analysis-chart">
              <ResponsiveContainer
                width="100%"
                height="100%"
              >
                <ScatterChart>
                  <CartesianGrid
                    stroke="#e5e7eb"
                  />

                  <XAxis
                    type="number"
                    dataKey="pc1"
                    name="PC1"
                  />

                  <YAxis
                    type="number"
                    dataKey="pc2"
                    name="PC2"
                  />

                  <Tooltip />

                  <Scatter
                    name="Not Flagged"
                    data={normalPoints}
                    fill="#238d8b"
                    fillOpacity={0.55}
                  />

                  <Scatter
                    name="Flagged Anomaly"
                    data={anomalyPoints}
                    fill="#dd7965"
                  />
                </ScatterChart>
              </ResponsiveContainer>
            </div>

            <div className="cs-analysis-legend">
              <span>
                <i className="cs-dot normal" />
                Not Flagged
              </span>

              <span>
                <i className="cs-dot anomaly" />
                Flagged Anomaly
              </span>
            </div>

            <p className="cs-analysis-note">
              Predictions are made by the selected
              model. Flagged observations are not
              automatically confirmed attacks.
            </p>
          </section>

          {/* RECORDS */}

          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>4. Network Record Investigation</h2>

                <p>
                  Select a network record to inspect
                  its features and anomaly score.
                </p>
              </div>

              <button
                type="button"
                className="cs-analysis-button"
                onClick={() =>
                  exportPredictions(result.rows, model)
                }
              >
                <FileDown size={16} />
                Export CSV
              </button>
            </div>

            <div className="cs-analysis-filters">
              <label>
                <input
                  type="checkbox"
                  checked={onlyFlagged}
                  onChange={(event) => {
                    setOnlyFlagged(
                      event.target.checked
                    );
                    setPage(0);
                  }}
                />

                Only flagged records
              </label>

              <input
                type="search"
                value={search}
                placeholder="Search protocol, service, row..."
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(0);
                }}
              />
            </div>

            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Row</th>
                    <th>Protocol</th>
                    <th>Service</th>
                    <th>State</th>
                    <th>Duration</th>
                    <th>Score</th>
                    <th>Prediction</th>
                  </tr>
                </thead>

                <tbody>
                  {visibleRecords.map((record) => (
                    <tr
                      key={record.row}
                      className={
                        selectedRow === record.row
                          ? 'cs-selected-row'
                          : ''
                      }
                      onClick={() =>
                        setSelectedRow(record.row)
                      }
                      style={{ cursor: 'pointer' }}
                    >
                      <td>#{record.row}</td>
                      <td>{record.proto}</td>
                      <td>{record.service}</td>
                      <td>{record.state}</td>

                      <td>
                        {record.duration.toFixed(3)}
                      </td>

                      <td>
                        {anomalyScore(record).toFixed(4)}
                      </td>

                      <td>
                        {isAnomaly(record)
                          ? 'Flagged'
                          : 'Not Flagged'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="cs-analysis-pagination">
              <span>
                {filteredRecords.length} matching records
              </span>

              <button
                type="button"
                disabled={page === 0}
                onClick={() =>
                  setPage((current) => current - 1)
                }
              >
                Previous
              </button>

              <span>
                {page + 1} / {pageCount}
              </span>

              <button
                type="button"
                disabled={page + 1 >= pageCount}
                onClick={() =>
                  setPage((current) => current + 1)
                }
              >
                Next
              </button>
            </div>
          </section>

          {/* SELECTED RECORD */}

          {selected && (
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>
                    Selected Record #{selected.row}
                  </h2>

                  <p>
                    Detailed network traffic features.
                  </p>
                </div>
              </div>

              <div className="cs-analysis-detail">
                {[
                  ['Protocol', selected.proto],
                  ['Service', selected.service],
                  ['Connection State', selected.state],
                  ['Duration', `${selected.duration} s`],
                  [
                    'Source Bytes',
                    selected.sbytes.toLocaleString()
                  ],
                  [
                    'Destination Bytes',
                    selected.dbytes.toLocaleString()
                  ],
                  [
                    'Anomaly Score',
                    anomalyScore(selected).toFixed(6)
                  ],
                  [
                    'Prediction',
                    isAnomaly(selected)
                      ? 'Flagged'
                      : 'Not Flagged'
                  ],
                  [
                    'Dataset Label',
                    selected.actual_attack === null
                      ? 'Not Available'
                      : selected.actual_attack === 1
                        ? 'Attack'
                        : 'Normal'
                  ],
                  [
                    'Attack Category',
                    selected.attack_cat ?? 'Not Available'
                  ]
                ].map(([label, value]) => (
                  <div key={label}>
                    <span>{label}</span>
                    <strong>{value}</strong>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* RECOMMENDATIONS */}

          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>5. Analysis Recommendations</h2>

                <p>
                  Network investigation guidance.
                </p>
              </div>
            </div>

            <ul className="cs-analysis-recommendations">
              {result.recommendations.map(
                (recommendation, index) => (
                  <li key={index}>
                    {recommendation}
                  </li>
                )
              )}
            </ul>

            <p className="cs-analysis-note">
              {result.note}
            </p>
          </section>
        </>
      )}
    </div>
  );
}
