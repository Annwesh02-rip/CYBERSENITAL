
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
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';

import './V2Workbench.css';


type Mode =
  | 'overview'
  | 'security'
  | 'traffic'
  | 'optimization';


type Summary = {
  training_rows_normal_only: number;
  selected_model: string;

  final_test_metrics: {
    accuracy: number;
    precision: number;
    recall: number;
    f1: number;
    false_positive_rate: number;
  };
};


type Flow = {
  row: number;
  proto: string;
  service: string;
  state: string;
  anomaly_score: number;
  predicted_anomaly: boolean;
};


type Sample = {
  rows_analyzed: number;
  flagged: number;
  rows: Flow[];

  protocol_distribution: {
    name: string;
    value: number;
  }[];
};


const pct = (value: number) =>
  `${(value * 100).toFixed(2)}%`;


export default function V2ProjectPages({
  mode
}: {
  mode: Mode
}) {

  const [summary, setSummary] =
    useState<Summary | null>(null);

  const [sample, setSample] =
    useState<Sample | null>(null);

  const [error, setError] =
    useState('');

  const [loading, setLoading] =
    useState(true);


  useEffect(() => {

    let active = true;

    async function load() {

      setLoading(true);
      setError('');

      try {

        const [
          reportResponse,
          sampleResponse
        ] = await Promise.all([

          fetch(
            '/api/model-v2/report'
          ),

          fetch(
            '/api/model-v2/sample?rows=400&save=false',
            {
              method: 'POST'
            }
          ),

        ]);

        if (
          !reportResponse.ok
          || !sampleResponse.ok
        ) {

          throw new Error(
            "V2 API unavailable "
            + `(${reportResponse.status}/`
            + `${sampleResponse.status})`
          );

        }

        const nextSummary =
          await reportResponse.json() as Summary;

        const nextSample =
          await sampleResponse.json() as Sample;

        if (active) {

          setSummary(nextSummary);
          setSample(nextSample);

        }

      } catch (issue) {

        if (active) {
          setError(String(issue));
        }

      } finally {

        if (active) {
          setLoading(false);
        }

      }
    }

    void load();

    return () => {
      active = false;
    };

  }, [mode]);


  const titles: Record<Mode, string> = {
    overview: 'Overview',
    security: 'Security Insights',
    traffic: 'Traffic Analysis',
    optimization: 'Optimization Recommendations'
  };


  const latestFlags = useMemo(() => {

    return (sample?.rows ?? [])
      .filter(
        record =>
          record.predicted_anomaly
      )

      .sort(
        (a, b) =>
          b.anomaly_score -
          a.anomaly_score
      )

      .slice(0, 12);

  }, [sample]);


  return (
    <div className="v2-workbench">

      <section className="panel">

        <div className="eyebrow">
          CYBERSENTINEL / V2-ONLY WORKSPACE
        </div>

        <h1>
          {titles[mode]}
        </h1>

        <p className="v2-note">
          UNSW-NB15 analysis powered by the
          saved V2 Isolation Forest. Preview
          statistics below are from a
          400-record testing sample, not live
          network capture.
        </p>


        <div className="v2-controls">

          <Link
            className="v2-export"
            to="/analyze"
          >
            Analyze a Dataset
          </Link>

          <Link
            className="v2-export"
            to="/history"
          >
            Saved Reports
          </Link>

          <Link
            className="v2-export"
            to="/live"
          >
            Live Monitoring
          </Link>

        </div>


        {loading && (
          <p className="v2-note">
            Loading measured V2 data...
          </p>
        )}


        {error && (
          <p
            className="v2-error"
            role="alert"
          >
            {error}
          </p>
        )}

      </section>


      {summary && sample && (

        <>

          {/* MODEL PERFORMANCE */}

          <section className="panel">

            <h2>
              Saved Model and Sample Results
            </h2>


            <div className="v2-stat-grid">

              <div>
                <span>V2 test accuracy</span>
                <strong>
                  {pct(
                    summary.final_test_metrics.accuracy
                  )}
                </strong>
              </div>

              <div>
                <span>V2 test recall</span>
                <strong>
                  {pct(
                    summary.final_test_metrics.recall
                  )}
                </strong>
              </div>

              <div>
                <span>Preview records</span>
                <strong>
                  {sample.rows_analyzed}
                </strong>
              </div>

              <div>
                <span>Preview outliers</span>
                <strong>
                  {sample.flagged}
                </strong>
              </div>

            </div>


            <p className="v2-note">
              Training records:
              {' '}
              {summary.training_rows_normal_only
                .toLocaleString()}
              {' '}
              normal flows.

              Selected feature space:
              {' '}
              {summary.selected_model}.

              Saved model F1:
              {' '}
              {pct(
                summary.final_test_metrics.f1
              )}.
            </p>

          </section>


          {/* TRAFFIC DISTRIBUTION */}

          {(mode === 'overview' ||
            mode === 'traffic') && (

            <section className="panel">

              <h2>
                Observed Protocol Distribution
              </h2>


              <div className="v2-chart">

                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >

                  <BarChart
                    data={
                      sample.protocol_distribution
                    }
                  >

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
                      name="Records"
                      fill="#23848b"
                    />

                  </BarChart>

                </ResponsiveContainer>

              </div>


              <p className="v2-note">
                Protocol counts come from the
                sampled dataset, not the local
                Wi-Fi capture.
              </p>

            </section>

          )}


          {/* SECURITY INSIGHTS */}

          {(mode === 'security' ||
            mode === 'overview') && (

            <section className="panel">

              <h2>
                Highest-Scoring Flagged Records
              </h2>


              <div className="table-scroll">

                <table>

                  <thead>
                    <tr>
                      <th>Row</th>
                      <th>Protocol</th>
                      <th>Service</th>
                      <th>State</th>
                      <th>Anomaly Score</th>
                    </tr>
                  </thead>


                  <tbody>

                    {latestFlags.map(record => (

                      <tr key={record.row}>

                        <td>{record.row}</td>
                        <td>{record.proto}</td>
                        <td>{record.service}</td>
                        <td>{record.state}</td>

                        <td>
                          {record.anomaly_score
                            .toFixed(5)}
                        </td>

                      </tr>

                    ))}


                    {!latestFlags.length && (

                      <tr>
                        <td colSpan={5}>
                          No flagged records
                          in the preview.
                        </td>
                      </tr>

                    )}

                  </tbody>

                </table>

              </div>


              <p className="v2-note">
                Unsupervised flags indicate
                unusual patterns; they do not
                confirm attacks.
              </p>

            </section>

          )}


          {/* OPTIMIZATION */}

          {mode === 'optimization' && (

            <section className="panel">

              <h2>
                Evidence-Based Recommendations
              </h2>


              <p>
                <strong>
                  1. Reduce false alerts.
                </strong>
                {' '}
                The measured V2 test false-positive
                rate is
                {' '}
                {pct(
                  summary.final_test_metrics
                    .false_positive_rate
                )}.
                Review the validation-selected
                threshold before deploying alerts.
              </p>


              <p>
                <strong>
                  2. Prioritize missed attacks.
                </strong>
                {' '}
                The measured V2 test recall is
                {' '}
                {pct(
                  summary.final_test_metrics.recall
                )}.
                Inspect false negatives by protocol
                and attack category during
                further evaluation.
              </p>


              <p>
                <strong>
                  3. Review flagged flows.
                </strong>
                {' '}
                {sample.flagged}
                {' '}of{' '}
                {sample.rows_analyzed}
                {' '}preview records were flagged.
                Correlate findings with authorized
                network logs.
              </p>


              <p>
                <strong>
                  4. Validate congestion separately.
                </strong>
                {' '}
                Anomaly scores alone do not measure
                link utilization, latency or packet
                loss. No network setting is
                automatically changed.
              </p>

            </section>

          )}

        </>

      )}

    </div>
  );
}
