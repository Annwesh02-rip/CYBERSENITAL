
import { useState } from 'react';

import AnalyzeTraffic from './AnalyzeTraffic';
import V2Workbench from './V2Workbench';

import './V2Workbench.css';


type Version = 'v1' | 'v2';


export default function AnalyzeWorkspace() {

  const [version, setVersion] =
    useState<Version>('v1');

  return (
    <div className="v2-workspace">

      <section className="panel v2-selector-panel">

        <div>
          <div className="eyebrow">
            CYBERSENTINEL / MODEL SELECTION
          </div>

          <h2>Choose Anomaly Detection Model</h2>

          <p>
            Select the original model or the
            improved normal-only V2 detector.
          </p>
        </div>


        <div className="v2-version-switch">

          <button
            type="button"
            className={
              version === 'v1' ? 'active' : ''
            }
            onClick={() => setVersion('v1')}
          >
            V1 — Original Model
          </button>

          <button
            type="button"
            className={
              version === 'v2' ? 'active' : ''
            }
            onClick={() => setVersion('v2')}
          >
            V2 — Improved Model
          </button>

        </div>

        <p className="v2-note">
          V1 includes the original Isolation Forest
          and PCA comparison. V2 uses its independently
          trained detector and validation-selected
          threshold.
        </p>

      </section>


      {version === 'v1' ? (
        <AnalyzeTraffic />
      ) : (
        <V2Workbench mode="analysis" />
      )}

    </div>
  );
}
