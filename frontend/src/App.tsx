
import {
  Routes,
  Route
} from 'react-router-dom';

import Layout from './components/Layout';

import V2Workbench from './pages/V2Workbench';

import V2ProjectPages from './pages/V2ProjectPages';

import History from './pages/History';

import LiveMonitoring from './pages/LiveMonitoring';

import LiveMLPanel from './pages/LiveMLPanel';

import LiveCaptureReports from './pages/LiveCaptureReports';


export default function App() {

  return (
    <Routes>

      <Route element={<Layout />}>

        <Route
          index
          element={
            <V2ProjectPages mode="overview" />
          }
        />

        <Route
          path="analyze"
          element={
            <V2Workbench mode="analysis" />
          }
        />

        <Route
          path="dataset"
          element={
            <V2Workbench mode="overview" />
          }
        />

        <Route
          path="security"
          element={
            <V2ProjectPages mode="security" />
          }
        />

        <Route
          path="traffic"
          element={
            <V2ProjectPages mode="traffic" />
          }
        />

        <Route
          path="optimization"
          element={
            <V2ProjectPages mode="optimization" />
          }
        />

        <Route
          path="history"
          element={<History />}
        />

        <Route
          path="live"
          element={
            <>
              <LiveMonitoring />
              <LiveMLPanel />
              <LiveCaptureReports />
            </>
          }
        />

      </Route>

    </Routes>
  );
}
