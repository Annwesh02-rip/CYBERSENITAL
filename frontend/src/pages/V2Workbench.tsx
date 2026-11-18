
import {
  useEffect,
  useMemo,
  useState
} from 'react';

import { Link } from 'react-router-dom';

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';

import './V2Workbench.css';


type Metrics = {
  accuracy: number;
  balanced_accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  f2: number;
  mcc: number;
  false_positive_rate: number;
  roc_auc?: number;
  pr_auc?: number;
  confusion_matrix: number[][];
};


type TrainingReport = {
  training_rows_normal_only: number;
  validation_rows: number;
  test_rows: number;
  selected_model: string;
  encoded_features: number;
  pca_95_dimensions: number;
  final_test_metrics: Metrics;
};


type Prediction = {
  row: number;
  proto: string;
  service: string;
  state: string;
  pc1: number;
  pc2: number;
  anomaly_score: number;
  predicted_anomaly: boolean;
  actual_attack: number | null;
};


type Result = {
  history_id?: number;
  report_url?: string;
  csv_url?: string;
  source: string;
  selected_model: string;
  rows_analyzed: number;
  flagged: number;
  truncated: boolean;
  model_input_dimensions: number;
  metrics: Metrics | null;
  rows: Prediction[];
};


type Props = {
  mode?: 'analysis' | 'overview';
};


async function json<T>(
  url: string,
  options?: RequestInit
): Promise<T> {

  const response = await fetch(
    url,
    options
  );

  const data = await response
    .json()
    .catch(() => ({}));

  if (!response.ok) {

    throw new Error(
      typeof data.detail === 'string'
        ? data.detail
        : `HTTP ${response.status}`
    );
  }

  return data as T;
}


const pct = (
  n: number | undefined
) => n == null
  ? 'N/A'
  : `${(n * 100).toFixed(2)}%`;


function MetricTable({
  metrics
}: {
  metrics: Metrics
}) {

  const items: [string, string][] = [
    [
      'Accuracy',
      pct(metrics.accuracy)
    ],

    [
      'Balanced accuracy',
      pct(metrics.balanced_accuracy)
    ],

    [
      'Precision',
      pct(metrics.precision)
    ],

    [
      'Recall',
      pct(metrics.recall)
    ],

    [
      'F1-score',
      pct(metrics.f1)
    ],

    [
      'F2-score',
      pct(metrics.f2)
    ],

    [
      'ROC-AUC',
      metrics.roc_auc?.toFixed(4) ?? 'N/A'
    ],

    [
      'PR-AUC',
      metrics.pr_auc?.toFixed(4) ?? 'N/A'
    ],

    [
      'MCC',
      metrics.mcc.toFixed(4)
    ],

    [
      'False-positive rate',
      pct(metrics.false_positive_rate)
    ],
  ];

  return (
    <div className="table-scroll">
      <table>

        <thead>
          <tr>
            <th>Metric</th>
            <th>Result</th>
          </tr>
        </thead>

        <tbody>
          {items.map(([key, value]) => (
            <tr key={key}>
              <td>{key}</td>
              <td>{value}</td>
            </tr>
          ))}
        </tbody>

      </table>
    </div>
  );
}


export default function V2Workbench({
  mode = 'analysis'
}: Props) {

  const [training, setTraining] =
    useState<TrainingReport | null>(null);

  const [result, setResult] =
    useState<Result | null>(null);

  const [file, setFile] =
    useState<File | null>(null);

  const [error, setError] =
    useState('');

  const [running, setRunning] =
    useState(false);

  const [onlyFlagged, setOnlyFlagged] =
    useState(false);

  const [search, setSearch] =
    useState('');


  // ------------------------------------------
  // LOAD SAVED V2 TRAINING RESULTS
  // ------------------------------------------

  useEffect(() => {

    let active = true;

    json<TrainingReport>(
      '/api/model-v2/report'
    )
      .then(value => {

        if (active) {
          setTraining(value);
        }

      })
      .catch(issue => {

        if (active) {
          setError(String(issue));
        }

      });

    return () => {
      active = false;
    };

  }, []);


  // ------------------------------------------
  // ANALYZE AND AUTOMATICALLY SAVE
  // ------------------------------------------

  async function analyze(
    source: 'sample' | 'upload'
  ) {

    if (
      source === 'upload'
      && !file
    ) {

      setError('Select a CSV first.');
      return;
    }

    setRunning(true);
    setError('');
    setResult(null);

    try {

      let data: Result;

      if (source === 'sample') {

        data = await json<Result>(
          '/api/model-v2/sample?rows=1500&save=true',
          {
            method: 'POST'
          }
        );

      } else {

        const body = new FormData();

        body.append(
          'file',
          file as File
        );

        data = await json<Result>(
          '/api/model-v2/upload?save=true',
          {
            method: 'POST',
            body
          }
        );

      }

      setResult(data);
      setSearch('');
      setOnlyFlagged(false);

    } catch (issue) {

      setError(
        issue instanceof Error
          ? issue.message
          : String(issue)
      );

    } finally {

      setRunning(false);

    }
  }


  // ------------------------------------------
  // FILTER RECORDS
  // ------------------------------------------

  const filtered = useMemo(() => {

    return (result?.rows ?? []).filter(
      record => {

        const allowed = (
          !onlyFlagged
          || record.predicted_anomaly
        );

        const matches = (
          !search
          || (
            `${record.row} ` +
            `${record.proto} ` +
            `${record.service} ` +
            `${record.state}`
          )
            .toLowerCase()
            .includes(
              search.toLowerCase()
            )
        );

        return allowed && matches;
      }
    );

  }, [
    result,
    onlyFlagged,
    search
  ]);


  const plotted = (
    result?.rows ?? []
  ).filter(
    (_, index) => {

      const total = (
        result?.rows.length ?? 0
      );

      const step = Math.max(
        1,
        Math.ceil(total / 800)
      );

      return index % step === 0;
    }
  );


  const scoreChart = training
    ? [
        {
          name: 'Accuracy',
          score:
            training.final_test_metrics.accuracy * 100
        },
        {
          name: 'Precision',
          score:
            training.final_test_metrics.precision * 100
        },
        {
          name: 'Recall',
          score:
            training.final_test_metrics.recall * 100
        },
        {
          name: 'F1',
          score:
            training.final_test_metrics.f1 * 100
        }
      ]
    : [];


  return (
    <div className="v2-workbench">

      {/* V2 TRAINING RESULTS */}

      <section className="panel">

        <div className="panel-heading">

          <div>

            <div className="eyebrow">
              CYBERSENTINEL / ACTIVE MODEL
            </div>

            <h2>
              {mode === 'analysis'
                ? 'Network Anomaly Analysis'
                : 'Model Evaluation'}
            </h2>

            <p>
              V2 only — normal-only Isolation
              Forest with validation-calibrated
              threshold.
            </p>

          </div>

          <span className="data-pill">
            V2 ACTIVE
          </span>

        </div>


        {error && (
          <p
            className="v2-error"
            role="alert"
          >
            {error}
          </p>
        )}


        {training ? (

          <>

            <div className="v2-stat-grid">

              <div>
                <span>
                  Normal training records
                </span>
                <strong>
                  {training.training_rows_normal_only
                    .toLocaleString()}
                </strong>
              </div>

              <div>
                <span>
                  Selected feature view
                </span>
                <strong>
                  {training.selected_model}
                </strong>
              </div>

              <div>
                <span>
                  Encoded features
                </span>
                <strong>
                  {training.encoded_features}
                </strong>
              </div>

              <div>
                <span>
                  Validation records
                </span>
                <strong>
                  {training.validation_rows
                    .toLocaleString()}
                </strong>
              </div>

            </div>


            <h3>
              Saved V2 test performance
            </h3>


            <div className="v2-chart">

              <ResponsiveContainer
                width="100%"
                height="100%"
              >

                <BarChart data={scoreChart}>

                  <CartesianGrid
                    strokeDasharray="3 3"
                  />

                  <XAxis
                    dataKey="name"
                  />

                  <YAxis
                    domain={[0, 100]}
                  />

                  <Tooltip />

                  <Bar
                    dataKey="score"
                    fill="#23848b"
                    name="Score (%)"
                  />

                </BarChart>

              </ResponsiveContainer>

            </div>


            <MetricTable
              metrics={training.final_test_metrics}
            />


            <p className="v2-note">
              PCA was evaluated as an alternative
              feature representation and remains
              available for visualization. Model
              selection used validation data;
              these metrics belong to the saved
              test experiment.
            </p>

          </>

        ) : (

          <p className="v2-note">
            Loading the saved V2 evaluation...
          </p>

        )}

      </section>


      {/* DATASET ANALYSIS */}

      {mode === 'analysis' && (

        <>

          <section className="panel">

            <div className="panel-heading">

              <div>
                <h2>
                  Analyze CSV using V2
                </h2>

                <p>
                  Every completed analysis is
                  automatically saved to SQLite
                  with its own PDF and CSV report.
                </p>
              </div>

            </div>


            <div className="v2-controls">

              <label className="v2-upload">

                {file?.name ??
                  'Choose UNSW-NB15 CSV'}

                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={event =>
                    setFile(
                      event.target.files?.[0]
                      ?? null
                    )
                  }
                />

              </label>


              <button
                type="button"
                disabled={running || !file}
                onClick={() =>
                  void analyze('upload')
                }
              >
                Analyze Uploaded CSV
              </button>


              <button
                type="button"
                disabled={running}
                onClick={() =>
                  void analyze('sample')
                }
              >
                Analyze Built-in Test Sample
              </button>

            </div>


            {running && (
              <p className="v2-note">
                Running V2 inference
                and saving report...
              </p>
            )}

          </section>


          {result && (

            <>

              {/* SAVED ANALYSIS RESULTS */}

              <section className="panel">

                <div className="panel-heading">

                  <div>
                    <h2>
                      Analysis #{result.history_id ?? '-'} saved
                    </h2>

                    <p>
                      {result.source}
                    </p>
                  </div>

                </div>


                <div className="v2-controls">

                  {result.report_url && (

                    <a
                      className="v2-export"
                      href={result.report_url}
                    >
                      Download Graphical PDF
                    </a>

                  )}


                  {result.csv_url && (

                    <a
                      className="v2-export"
                      href={result.csv_url}
                    >
                      Download Predictions CSV
                    </a>

                  )}


                  <Link
                    className="v2-export"
                    to="/history"
                  >
                    Open History
                  </Link>

                </div>


                <div className="v2-stat-grid">

                  <div>
                    <span>
                      Analyzed records
                    </span>

                    <strong>
                      {result.rows_analyzed
                        .toLocaleString()}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Outliers flagged
                    </span>

                    <strong>
                      {result.flagged
                        .toLocaleString()}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Model input dimensions
                    </span>

                    <strong>
                      {result.model_input_dimensions}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Detector
                    </span>

                    <strong>
                      {result.selected_model}
                    </strong>
                  </div>

                </div>


                {result.metrics ? (

                  <>

                    <h3>
                      Metrics on this dataset
                    </h3>

                    <MetricTable
                      metrics={result.metrics}
                    />


                    <h3>
                      Confusion matrix
                    </h3>

                    <div className="table-scroll">

                      <table>

                        <thead>
                          <tr>
                            <th>
                              Actual / Predicted
                            </th>
                            <th>Normal</th>
                            <th>Attack</th>
                          </tr>
                        </thead>

                        <tbody>

                          <tr>
                            <td>Normal</td>

                            <td>
                              {result.metrics
                                .confusion_matrix[0][0]}
                            </td>

                            <td>
                              {result.metrics
                                .confusion_matrix[0][1]}
                            </td>
                          </tr>

                          <tr>
                            <td>Attack</td>

                            <td>
                              {result.metrics
                                .confusion_matrix[1][0]}
                            </td>

                            <td>
                              {result.metrics
                                .confusion_matrix[1][1]}
                            </td>
                          </tr>

                        </tbody>

                      </table>

                    </div>

                  </>

                ) : (

                  <p className="v2-note">
                    No verified labels were
                    supplied. Predictions are
                    available, but accuracy
                    cannot be calculated.
                  </p>

                )}


                {result.truncated && (

                  <p className="v2-note">
                    Only the first 5,000 uploaded
                    records were analyzed.
                  </p>

                )}

              </section>


              {/* PCA VISUALIZATION */}

              <section className="panel">

                <h2>
                  2D PCA Visualization
                </h2>

                <div className="v2-chart tall">

                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >

                    <ScatterChart>

                      <CartesianGrid />

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
                        name="Not flagged"
                        data={plotted.filter(
                          item =>
                            !item.predicted_anomaly
                        )}
                        fill="#23848b"
                        fillOpacity={0.6}
                      />

                      <Scatter
                        name="Flagged"
                        data={plotted.filter(
                          item =>
                            item.predicted_anomaly
                        )}
                        fill="#d47762"
                      />

                    </ScatterChart>

                  </ResponsiveContainer>

                </div>


                <p className="v2-note">
                  PCA displays traffic structure.
                  The selected numerical-feature
                  detector does not use these
                  plotted coordinates for predictions.
                </p>

              </section>


              {/* RECORD PREDICTIONS */}

              <section className="panel">

                <h2>
                  Record-Level Predictions
                </h2>


                <div className="v2-filters">

                  <label>

                    <input
                      type="checkbox"
                      checked={onlyFlagged}
                      onChange={event =>
                        setOnlyFlagged(
                          event.target.checked
                        )
                      }
                    />

                    Flagged only

                  </label>


                  <input
                    type="search"
                    placeholder="Search records"
                    value={search}
                    onChange={event =>
                      setSearch(
                        event.target.value
                      )
                    }
                  />


                  <span>
                    {filtered.length}
                    {' '}matching records
                  </span>

                </div>


                <div className="table-scroll">

                  <table>

                    <thead>
                      <tr>
                        <th>Row</th>
                        <th>Protocol</th>
                        <th>Service</th>
                        <th>State</th>
                        <th>Score</th>
                        <th>Prediction</th>
                        <th>Actual</th>
                      </tr>
                    </thead>


                    <tbody>

                      {filtered
                        .slice(0, 100)
                        .map(record => (

                          <tr key={record.row}>

                            <td>{record.row}</td>
                            <td>{record.proto}</td>
                            <td>{record.service}</td>
                            <td>{record.state}</td>

                            <td>
                              {record.anomaly_score
                                .toFixed(5)}
                            </td>

                            <td>
                              {record.predicted_anomaly
                                ? 'Flagged'
                                : 'Not flagged'}
                            </td>

                            <td>
                              {record.actual_attack == null
                                ? 'Unknown'
                                : record.actual_attack
                                  ? 'Attack'
                                  : 'Normal'}
                            </td>

                          </tr>

                        ))}

                    </tbody>

                  </table>

                </div>


                <p className="v2-note">
                  The first 100 matching rows
                  are displayed. Download the
                  predictions CSV for all
                  analyzed records.
                </p>

              </section>

            </>

          )}

        </>

      )}

    </div>
  );
}
