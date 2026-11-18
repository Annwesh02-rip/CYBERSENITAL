
import { NavLink, Outlet } from 'react-router-dom';

import {
  Activity,
  ChartNoAxesCombined,
  Clock3,
  Code2,
  Database,
  Gauge,
  Radio,
  Radar,
  ShieldCheck,
  Upload
} from 'lucide-react';


const links = [
  {
    to: '/',
    label: 'Overview',
    icon: Gauge
  },
  {
    to: '/analyze',
    label: 'Analyze Traffic',
    icon: Upload
  },
  {
    to: '/live',
    label: 'Live Monitoring',
    icon: Radio
  },
  {
    to: '/history',
    label: 'Analysis History',
    icon: Clock3
  },
  {
    to: '/security',
    label: 'Security',
    icon: ShieldCheck
  },
  {
    to: '/traffic',
    label: 'Traffic Analysis',
    icon: Activity
  },
  {
    to: '/optimization',
    label: 'Optimization',
    icon: ChartNoAxesCombined
  },
  {
    to: '/dataset',
    label: 'Real Dataset Lab',
    icon: Database
  }
];


export default function Layout() {

  return (
    <div className="app-shell">

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-icon">
            <Radar size={25} />
          </div>

          <div>
            <strong>CyberSentinel</strong>
            <small>NETWORK INTELLIGENCE</small>
          </div>

        </div>


        <div className="sidebar-section">
          WORKSPACE
        </div>


        <nav className="nav-links">

          {links.map(
            ({ to, label, icon: Icon }) => (

              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `nav-link ${
                    isActive ? 'active' : ''
                  }`
                }
              >

                <Icon size={18} />

                <span>{label}</span>

              </NavLink>

            )
          )}

        </nav>


        <div className="sidebar-bottom">

          <div className="sidebar-tag">
            NETWORK INTELLIGENCE
          </div>

          <p>
            Offline machine learning analysis
            and authorized live network monitoring.
          </p>

          <span>
            <Code2 size={14} />
            Mini Project · v1.4
          </span>

        </div>

      </aside>


      <div className="main-area">

        <header className="topbar">

          <span className="breadcrumb">
            CyberSentinel
            <span>/</span>
            Network Analysis Workspace
          </span>

          <span className="status">
            <i />
            Research Prototype
          </span>

        </header>


        <main className="page">
          <Outlet />
        </main>

      </div>

    </div>
  );
}
