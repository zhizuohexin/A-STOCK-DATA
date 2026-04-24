import { Layout, Menu, theme } from 'antd';
import { Link, Outlet, useLocation } from 'react-router-dom';
import {
  BookOutlined,
  DashboardOutlined,
  EditOutlined,
  FallOutlined,
  FundOutlined,
  LineChartOutlined,
  RiseOutlined,
  SettingOutlined,
  StockOutlined,
  TagsOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  HistoryOutlined,
  WalletOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';

const { Header, Content, Sider } = Layout;

const menu: MenuProps['items'] = [
  { key: '/', icon: <DashboardOutlined />, label: <Link to="/">复盘首页</Link> },
  { key: '/quotes', icon: <LineChartOutlined />, label: <Link to="/quotes">日线行情</Link> },
  { key: '/top-amount', icon: <FundOutlined />, label: <Link to="/top-amount">成交额榜</Link> },
  { key: '/limit-up', icon: <ThunderboltOutlined />, label: <Link to="/limit-up">涨停/连板</Link> },
  { key: '/limit-down', icon: <FallOutlined />, label: <Link to="/limit-down">跌停</Link> },
  { key: '/limit-by-sector', icon: <TagsOutlined />, label: <Link to="/limit-by-sector">涨停板块热度</Link> },
  { key: '/sectors', icon: <TagsOutlined />, label: <Link to="/sectors">板块</Link> },
  { key: '/rankings', icon: <RiseOutlined />, label: <Link to="/rankings">排行榜</Link> },
  {
    key: 'journal',
    icon: <EditOutlined />,
    label: '我的笔记',
    children: [
      { key: '/journal/trading', icon: <WalletOutlined />, label: <Link to="/journal/trading">交易记录</Link> },
      { key: '/journal/review', icon: <BookOutlined />, label: <Link to="/journal/review">复盘参考</Link> },
      { key: '/journal/master', icon: <TeamOutlined />, label: <Link to="/journal/master">高手跟踪</Link> },
    ],
  },
  {
    key: 'admin',
    icon: <SettingOutlined />,
    label: '数据管理',
    children: [
      { key: '/stocks', icon: <StockOutlined />, label: <Link to="/stocks">股票基础信息</Link> },
      { key: '/jobs', icon: <HistoryOutlined />, label: <Link to="/jobs">任务日志</Link> },
    ],
  },
];

export default function App() {
  const location = useLocation();
  const { token } = theme.useToken();
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', color: '#fff', fontSize: 18, fontWeight: 600 }}>
        A-Stock Data · 复盘工作台
      </Header>
      <Layout>
        <Sider width={220} style={{ background: token.colorBgContainer }}>
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            defaultOpenKeys={['journal', 'admin']}
            style={{ height: '100%' }}
            items={menu}
          />
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
