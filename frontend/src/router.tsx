import { createBrowserRouter } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import Layout from './components/Layout';

const Loading = () => (
  <div className="space-y-4 p-8 animate-fade-in">
    <div className="rc-skeleton h-8 w-64" />
    <div className="rc-skeleton h-4 w-96" />
    <div className="grid grid-cols-3 gap-4 mt-6">
      <div className="rc-skeleton h-32" /><div className="rc-skeleton h-32" /><div className="rc-skeleton h-32" />
    </div>
  </div>
);

const wrap = (C: React.LazyExoticComponent<() => JSX.Element>) => (
  <Suspense fallback={<Loading />}><C /></Suspense>
);

const Canvas = lazy(() => import('./pages/Canvas'));
const Builder = lazy(() => import('./pages/Builder'));
const Connection = lazy(() => import('./pages/Connection'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Studio = lazy(() => import('./pages/Studio'));
const Inspector = lazy(() => import('./pages/Inspector'));
const Explorer = lazy(() => import('./pages/Explorer'));
const Verification = lazy(() => import('./pages/Verification'));
const Simulation = lazy(() => import('./pages/Simulation'));
const Reports = lazy(() => import('./pages/Reports'));
const Evaluation = lazy(() => import('./pages/Evaluation'));

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: wrap(Canvas) },
      { path: 'builder', element: wrap(Builder) },
      { path: 'connection', element: wrap(Connection) },
      { path: 'dashboard', element: wrap(Dashboard) },
      { path: 'studio', element: wrap(Studio) },
      { path: 'inspector', element: wrap(Inspector) },
      { path: 'explorer', element: wrap(Explorer) },
      { path: 'verification', element: wrap(Verification) },
      { path: 'simulation', element: wrap(Simulation) },
      { path: 'reports', element: wrap(Reports) },
      { path: 'evaluation', element: wrap(Evaluation) },
    ],
  },
]);
