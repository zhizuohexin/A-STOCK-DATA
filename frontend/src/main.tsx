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
import Sectors from './pages/Sectors';
import Rankings from './pages/Rankings';
import Intraday from './pages/Intraday';
import Jobs from './pages/Jobs';

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'stocks', element: <Stocks /> },
      { path: 'quotes', element: <Quotes /> },
      { path: 'limit-up', element: <LimitUp /> },
      { path: 'sectors', element: <Sectors /> },
      { path: 'rankings', element: <Rankings /> },
      { path: 'intraday', element: <Intraday /> },
      { path: 'jobs', element: <Jobs /> },
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
