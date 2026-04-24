import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { RouterProvider, createBrowserRouter } from 'react-router-dom';
import 'dayjs/locale/zh-cn';

import './index.css';
import App from './App';
import Dashboard from './pages/Dashboard';
import Stocks from './pages/Stocks';
import Quotes from './pages/Quotes';
import LimitUp from './pages/LimitUp';
import LimitDown from './pages/LimitDown';
import LimitUpBySector from './pages/LimitUpBySector';
import TopAmount from './pages/TopAmount';
import Sectors from './pages/Sectors';
import Rankings from './pages/Rankings';
import Jobs from './pages/Jobs';
import TradingRecords from './pages/TradingRecords';
import ReviewReferences from './pages/ReviewReferences';
import MasterTracking from './pages/MasterTracking';

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'stocks', element: <Stocks /> },
      { path: 'quotes', element: <Quotes /> },
      { path: 'limit-up', element: <LimitUp /> },
      { path: 'limit-down', element: <LimitDown /> },
      { path: 'limit-by-sector', element: <LimitUpBySector /> },
      { path: 'top-amount', element: <TopAmount /> },
      { path: 'sectors', element: <Sectors /> },
      { path: 'rankings', element: <Rankings /> },
      { path: 'jobs', element: <Jobs /> },
      { path: 'journal/trading', element: <TradingRecords /> },
      { path: 'journal/review', element: <ReviewReferences /> },
      { path: 'journal/master', element: <MasterTracking /> },
    ],
  },
]);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ConfigProvider locale={zhCN}>
      <RouterProvider router={router} />
    </ConfigProvider>
  </StrictMode>,
);
