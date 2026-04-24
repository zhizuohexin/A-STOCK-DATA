import { Card, Col, DatePicker, Row, Space, Statistic, Table, Tag, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import type { Dayjs } from 'dayjs';
import { api } from '../api/client';
import { PctCell } from '../components/PctCell';
import { formatYi } from '../components/format';

const { Title, Paragraph, Text } = Typography;

type ConsecutiveBucket = { level: string; count: number };
type MarketDist = { up: number; flat: number; down: number; total: number };
type StockItem = {
  ts_code: string;
  name: string | null;
  industry: string | null;
  close: number | null;
  pct_chg: number | null;
  amount: number | null;
};
type SectorItem = {
  sector_code: string;
  name: string | null;
  pct_chg: number | null;
  amount: number | null;
  type: string | null;
};

type Summary = {
  trade_date: string | null;
  limit_up_count: number;
  limit_down_count: number;
  broken_limit_count: number;
  consecutive_breakdown: ConsecutiveBucket[];
  market_distribution: MarketDist;
  top_gainers: StockItem[];
  top_losers: StockItem[];
  top_amount: StockItem[];
  top_sectors: SectorItem[];
};

const stockCols = (amountUnit: 'qianyuan' | 'yuan' = 'qianyuan') => [
  { title: '代码', dataIndex: 'ts_code', width: 100 },
  { title: '简称', dataIndex: 'name', width: 90 },
  { title: '行业', dataIndex: 'industry', width: 100, ellipsis: true },
  { title: '现价', dataIndex: 'close', width: 70 },
  {
    title: '涨跌幅',
    dataIndex: 'pct_chg',
    width: 80,
    render: (v: number | null) => <PctCell value={v} />,
  },
  {
    title: '成交额',
    dataIndex: 'amount',
    width: 90,
    render: (v: number | null) => formatYi(v, amountUnit, '亿'),
  },
];

export default function Dashboard() {
  const [date, setDate] = useState<Dayjs | null>(null);
  const [data, setData] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get<Summary>('/dashboard/summary', {
        params: { trade_date: date?.format('YYYY-MM-DD') },
      });
      setData(r.data);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '加载失败');
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [date]);

  const md = data?.market_distribution;
  const consec = data?.consecutive_breakdown || [];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>复盘首页</Title>
        <DatePicker value={date} onChange={setDate} placeholder={data?.trade_date ? `默认：${data.trade_date}` : '选日期'} />
        <Text type="secondary">
          {data?.trade_date ? `当前数据日期：${data.trade_date}` : '—'}
        </Text>
      </Space>

      {/* 核心指标 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="涨停家数"
              value={data?.limit_up_count ?? 0}
              valueStyle={{ color: '#f5222d' }}
              suffix="家"
            />
            <div style={{ fontSize: 12, color: '#888', marginTop: 8 }}>
              {consec.map(b => `${b.level}:${b.count}`).join('  ')}
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="跌停家数"
              value={data?.limit_down_count ?? 0}
              valueStyle={{ color: '#52c41a' }}
              suffix="家"
            />
            <div style={{ fontSize: 12, color: '#888', marginTop: 8 }}>
              涨停炸板：{data?.broken_limit_count ?? 0} 家
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic title="上涨家数" value={md?.up ?? 0} valueStyle={{ color: '#f5222d' }} suffix="家" />
            <div style={{ fontSize: 12, color: '#888', marginTop: 8 }}>
              平：{md?.flat ?? 0}  跌：{md?.down ?? 0}
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic title="涨跌比" value={
              md && md.down > 0 ? ((md.up / md.down).toFixed(2)) : '-'
            } />
            <div style={{ fontSize: 12, color: '#888', marginTop: 8 }}>
              总家数：{md?.total ?? 0}
            </div>
          </Card>
        </Col>
      </Row>

      {/* 榜单 */}
      <Row gutter={16}>
        <Col span={12}>
          <Card title="今日板块 Top 10" loading={loading} size="small" style={{ marginBottom: 16 }}>
            <Table
              rowKey="sector_code"
              dataSource={data?.top_sectors || []}
              pagination={false}
              size="small"
              columns={[
                { title: '板块', dataIndex: 'name', width: 140 },
                {
                  title: '类型', dataIndex: 'type', width: 60,
                  render: (v) => v === 'I' ? <Tag>行业</Tag> : v === 'C' ? <Tag color="blue">概念</Tag> : v,
                },
                {
                  title: '涨幅', dataIndex: 'pct_chg', width: 90,
                  render: (v: number | null) => <PctCell value={v} />,
                },
                {
                  title: '成交额', dataIndex: 'amount', width: 100,
                  render: (v: number | null) => formatYi(v, 'yuan', '亿'),
                },
              ]}
            />
          </Card>
          <Card title="今日成交额 Top 10" loading={loading} size="small">
            <Table<StockItem>
              rowKey="ts_code"
              dataSource={data?.top_amount || []}
              pagination={false}
              size="small"
              columns={stockCols('qianyuan')}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="今日涨幅 Top 10" loading={loading} size="small" style={{ marginBottom: 16 }}>
            <Table<StockItem>
              rowKey="ts_code"
              dataSource={data?.top_gainers || []}
              pagination={false}
              size="small"
              columns={stockCols('qianyuan')}
            />
          </Card>
          <Card title="今日跌幅 Top 10" loading={loading} size="small">
            <Table<StockItem>
              rowKey="ts_code"
              dataSource={data?.top_losers || []}
              pagination={false}
              size="small"
              columns={stockCols('qianyuan')}
            />
          </Card>
        </Col>
      </Row>

      {(!data || data.top_sectors.length === 0 || data.limit_up_count === 0) && (
        <Card style={{ marginTop: 16 }} size="small">
          <Paragraph type="warning" style={{ margin: 0 }}>
            ⚠️ 有些数据为空。原因通常是该日期的涨停池 / 板块日线还没入库。去对应页点「回溯入库」即可。
          </Paragraph>
        </Card>
      )}
    </div>
  );
}
