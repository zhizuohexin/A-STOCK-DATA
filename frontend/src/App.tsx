import { Layout, Menu, theme } from 'antd';
import { Link, Outlet, useLocation } from 'react-router-dom';
import {
  DashboardOutlined,
  FireOutlined,
  LineChartOutlined,
  RiseOutlined,
  StockOutlined,
  TagsOutlined,
  ThunderboltOutlined,
  HistoryOutlined,
} from '@ant-design/icons';

const { Header, Content, Sider } = Layout;

const menu = [
  { key: '/', icon: <DashboardOutlined />, label: <Link to="/">Dashboard</Link> },
  { key: '/stocks', icon: <StockOutlined />, label: <Link to="/stocks">股票列表</Link> },
  { key: '/quotes', icon: <LineChartOutlined />, label: <Link to="/quotes">日线行情</Link> },
  { key: '/limit-up', icon: <ThunderboltOutlined />, label: <Link to="/limit-up">涨停/连板</Link> },
  { key: '/sectors', icon: <TagsOutlined />, label: <Link to="/sectors">板块</Link> },
  { key: '/rankings', icon: <RiseOutlined />, label: <Link to="/rankings">涨幅排行</Link> },
  { key: '/intraday', icon: <FireOutlined />, label: <Link to="/intraday">盘中分时</Link> },
  { key: '/jobs', icon: <HistoryOutlined />, label: <Link to="/jobs">任务日志</Link> },
];

export default function App() {
  const location = useLocation();
  const { token } = theme.useToken();
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', color: '#fff', fontSize: 18, fontWeight: 600 }}>
        A-Stock Data
      </Header>
      <Layout>
        <Sider width={200} style={{ background: token.colorBgContainer }}>
          <Menu mode="inline" selectedKeys={[location.pathname]} style={{ height: '100%' }} items={menu} />
        </Sider>
        <Layout style={{ padding: '16px 24px' }}>
          <Content style={{ background: token.colorBgContainer, padding: 16, minHeight: 280, borderRadius: 8 }}>
            <Outlet />
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
}
