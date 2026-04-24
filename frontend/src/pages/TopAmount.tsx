import { Card, DatePicker, InputNumber, Space, Table, Typography } from 'antd';
import { useEffect, useState } from 'react';
import type { Dayjs } from 'dayjs';
import { api } from '../api/client';
import { PctCell, numSorter, strSorter } from '../components/PctCell';
import { formatYi } from '../components/format';

const { Title } = Typography;

type TopAmountItem = {
  ts_code: string;
  name: string | null;
  industry: string | null;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  pre_close: number | null;
  pct_chg: number | null;
  vol: number | null;
  amount: number | null;
  turnover_rate: number | null;
};

export default function TopAmount() {
  const [date, setDate] = useState<Dayjs | null>(null); // null → 后端用最新
  const [top, setTop] = useState(50);
  const [data, setData] = useState<TopAmountItem[]>([]);
  const [tradeDate, setTradeDate] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get('/quotes/top-amount', {
        params: { trade_date: date?.format('YYYY-MM-DD'), top },
      });
      setData(r.data.items || []);
      setTradeDate(r.data.trade_date);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [date, top]);

  return (
    <div>
      <Title level={3}>今日成交额前 N</Title>
      <Card>
        <Space style={{ marginBottom: 12 }}>
          <DatePicker value={date} onChange={setDate} placeholder={tradeDate ? `默认：${tradeDate}` : '默认最新'} />
          <InputNumber value={top} onChange={(v) => setTop((v as number) || 50)} min={1} max={500} />
          <span style={{ color: '#888' }}>
            {tradeDate && `当前数据日期：${tradeDate}`}
          </span>
        </Space>
        <Table<TopAmountItem>
          rowKey="ts_code"
          dataSource={data}
          loading={loading}
          size="small"
          pagination={{ pageSize: 50 }}
          columns={[
            { title: '排名', width: 60, render: (_, __, i) => i + 1 },
            { title: '代码', dataIndex: 'ts_code', width: 110, sorter: strSorter('ts_code') },
            { title: '简称', dataIndex: 'name', width: 120 },
            { title: '行业', dataIndex: 'industry', width: 140 },
            { title: '收盘', dataIndex: 'close', width: 90, sorter: numSorter('close') },
            {
              title: '涨跌幅%', dataIndex: 'pct_chg', width: 110,
              sorter: numSorter('pct_chg'),
              defaultSortOrder: 'descend',
              render: (v: number | null) => <PctCell value={v} />,
            },
            {
              title: '成交额(亿)', dataIndex: 'amount', width: 120,
              sorter: numSorter('amount'),
              defaultSortOrder: 'descend',
              render: (v) => formatYi(v, 'qianyuan', '亿'),
            },
            { title: '成交量(亿手)', dataIndex: 'vol', width: 120, sorter: numSorter('vol'), render: (v) => formatYi(v, 'shou', '亿手') },
            { title: '换手率%', dataIndex: 'turnover_rate', width: 100, sorter: numSorter('turnover_rate') },
          ]}
        />
      </Card>
    </div>
  );
}
