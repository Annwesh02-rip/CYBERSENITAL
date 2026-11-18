
import { useEffect, useState } from 'react';

import {
  Activity,
  Database,
  Layers,
  ShieldAlert
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

import MetricCard from '../components/MetricCard';
import StateMessage from '../components/StateMessage';
import { apiGet } from '../services/api';


type Metrics = {
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  roc_auc?: number;
  pr_auc?: number;
  flagged: number;
  confusion_matrix: number[][];
};


type Report = {
  dataset: string;
  train_rows_used: number;
  test_rows_used: number;
  input_features: number;
  pca_components_95pct: number;
  pca_retained_variance: number;
  test_attacks: number;
  test_normal: number;
  contamination: number;
  raw_isolation_forest: Metrics;
  pca_isolation_forest: Metrics;
  dbscan: {
    sample_size: number;
    clusters: number;
    noise_points: number;
    note: string;
  };
  notice: string;
};


type Sample = {
  pc1: number;
  pc2: number;
  predicted_anomaly: boolean;
  actual_attack: boolean;
  anomaly_score: number;
  proto: string;
  service: string;
  attack_cat: string;
};


const percent = (value: number) =>
  `${(value * 100).toFixed(2)}%`;


export default function DatasetLab() {

  const [report, setReport] =
    useState<Report | null>(null);

  const [samples, setSamples] =
    useState<Sample[]>([]);

  const [error, setError] = useState('');


  useEffect(() => {

    Promise.all([
      apiGet<Report>('/api/dataset/report'),
      apiGet<Sample[]>('/api/dataset/samples?limit=700')
    ])
      .then(([result, points]) => {
        setReport(result);
        setSamples(points);
      })
      .catch((err) => {
        setError(String(err));
      });

  }, []);


  if (error) {
    return (
      <StateMessage
        message={`Dataset Lab error: ${error}`}
      />
    );
  }


  if (!report) {
    return (
      <StateMessage
        message="Loading UNSW-NB15 analysis..."
      />
    );
  }


  const normal = samples.filter(
    (sample) => !sample.predicted_anomaly
  );

  const flagged = samples.filter(
    (sample) => sample.predicted_anomaly
  );


  const models = [
    {
      name: 'Isolation Forest',
      metrics: report.raw_isolation_forest
    },
    {
      name: 'PCA + Isolation Forest',
      metrics: report.pca_isolation_forest
    }
  ];


  const matrix =
    report.pca_isolation_forest.confusion_matrix;


  return (
    <>

      {/* PAGE HEADER */}

      <div className="page-intro">

        <div>
          <div className="eyebrow">
            REAL DATASET / UNSUPERVISED ML
          </div>

          <h1>UNSW-NB15 Dataset Lab</h1>

          <p>
            Network anomaly detection using
            Isolation Forest, PCA and DBSCAN.
          </p>
        </div>

        <span className="data-pill">
          OFFLINE DATASET ANALYSIS
        </span>

      </div>


      {/* SUMMARY CARDS */}

      <div className="metrics-grid">

        <MetricCard
          label="Training Records"
          value={report.train_rows_used.toLocaleString()}
          detail="Unsupervised model training"
          icon={<Database size={19} />}
        />

        <MetricCard
          label="Testing Records"
          value={report.test_rows_used.toLocaleString()}
          detail="Held-out testing data"
          icon={<Activity size={19} />}
        />

        <MetricCard
          label="PCA Dimensions"
          value={
            `${report.input_features} → ${report.pca_components_95pct}`
          }
          detail={
            `${percent(report.pca_retained_variance)} variance retained`
          }
          icon={<Layers size={19} />}
        />

        <MetricCard
          label="PCA Model Recall"
          value={percent(
            report.pca_isolation_forest.recall
          )}
          detail="Correctly detected attacks"
          icon={<ShieldAlert size={19} />}
        />

      </div>


      {/* MODEL COMPARISON */}

      <section className="panel">

        <div className="panel-heading">
          <div>
            <h2>Machine Learning Model Comparison</h2>
            <p>
              Evaluation on held-out UNSW-NB15 records.
            </p>
          </div>
        </div>

        <div className="table-scroll">

          <table>

            <thead>
              <tr>
                <th>Model</th>
                <th>Accuracy</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>F1</th>
                <th>ROC-AUC</th>
                <th>PR-AUC</th>
              </tr>
            </thead>

            <tbody>

              {models.map((model) => (

                <tr key={model.name}>

                  <td>{model.name}</td>

                  <td>
                    {percent(model.metrics.accuracy)}
                  </td>

                  <td>
                    {percent(model.metrics.precision)}
                  </td>

                  <td>
                    {percent(model.metrics.recall)}
                  </td>

                  <td>
                    {percent(model.metrics.f1)}
                  </td>

                  <td>
                    {model.metrics.roc_auc?.toFixed(4) ?? 'N/A'}
                  </td>

                  <td>
                    {model.metrics.pr_auc?.toFixed(4) ?? 'N/A'}
                  </td>

                </tr>

              ))}

            </tbody>

          </table>

        </div>

      </section>


      {/* PCA SCATTER PLOT */}

      <section className="panel">

        <div className="panel-heading">

          <div>
            <h2>PCA Network Traffic Visualization</h2>

            <p>
              Two-dimensional representation of
              network traffic with anomaly predictions.
            </p>
          </div>

        </div>

        <div className="chart-area tall">

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
                name="Principal Component 1"
              />

              <YAxis
                type="number"
                dataKey="pc2"
                name="Principal Component 2"
              />

              <Tooltip
                cursor={{
                  strokeDasharray: '3 3'
                }}
              />

              <Scatter
                name="Not Flagged"
                data={normal}
                fill="#2b8e91"
                fillOpacity={0.5}
              />

              <Scatter
                name="Flagged Anomaly"
                data={flagged}
                fill="#d17765"
              />

            </ScatterChart>

          </ResponsiveContainer>

        </div>

        <p className="footnote">
          Colours represent model predictions,
          not ground-truth attack labels.
        </p>

      </section>


      {/* CONFUSION MATRIX AND DBSCAN */}

      <div className="content-grid">

        <section className="panel">

          <div className="panel-heading">
            <div>
              <h2>Confusion Matrix</h2>
              <p>PCA + Isolation Forest</p>
            </div>
          </div>

          <div className="table-scroll">

            <table>

              <thead>
                <tr>
                  <th>Actual / Predicted</th>
                  <th>Normal</th>
                  <th>Attack</th>
                </tr>
              </thead>

              <tbody>

                <tr>
                  <td>Normal</td>

                  <td>
                    {matrix[0][0].toLocaleString()}
                  </td>

                  <td>
                    {matrix[0][1].toLocaleString()}
                  </td>
                </tr>

                <tr>
                  <td>Attack</td>

                  <td>
                    {matrix[1][0].toLocaleString()}
                  </td>

                  <td>
                    {matrix[1][1].toLocaleString()}
                  </td>
                </tr>

              </tbody>

            </table>

          </div>

        </section>


        <section className="panel">

          <div className="panel-heading">
            <div>
              <h2>DBSCAN Clustering</h2>
              <p>Exploratory unsupervised analysis</p>
            </div>
          </div>

          <p>
            <strong>
              {report.dbscan.clusters}
            </strong>
            {' '}clusters identified.
          </p>

          <p>
            <strong>
              {report.dbscan.noise_points}
            </strong>
            {' '}noise points found.
          </p>

          <p>
            Sample size:
            {' '}
            {report.dbscan.sample_size.toLocaleString()}
          </p>

          <p className="footnote">
            {report.dbscan.note}
          </p>

        </section>

      </div>


      {/* EXPERIMENT NOTICE */}

      <p className="footnote">
        {report.notice}
      </p>

    </>
  );
}
