import { Card, DatePicker, InputNumber, Select, Space, Table, Typography } from 'antd';
import { useEffect, useState } from 'react';
import dayjs, { type Dayjs } from 'dayjs';
import { api, type GainerItem, type RankingResponse, type SectorGainerItem } from '../api/client';

const { Title } = Typography;

export default function Rankings() {
  return (
    <div>
      <Title level={3}>涨幅排行</Title>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <NDayGainers />
        <SectorGainers />
      </Space>
    </div>
  );
}

function NDayGainers() {
  const [days, setDays] = useState(5);
  const [top, setTop] = useState(10);
  const [endDate, setEndDate] = useState<Dayjs | null>(null);
  const [data, setData] = useState<GainerItem[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get<RankingResponse<GainerItem>>('/rankings/gainers', {
        params: { days, top, end_date: endDate?.format('YYYY-MM-DD') },
      });
      setData(r.data.items || []);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [days, top, endDate]);

  return (
    <Card title="N 日涨幅前 Top">
      <Space style={{ marginBottom: 12 }}>
        <Select value={days} onChange={setDays} options={[5, 10, 20, 30, 60].map(v => ({ value: v, label: `${v} 日` }))} style={{ width: 100 }} />
        <InputNumber value={top} onChange={(v) => setTop((v as number) || 10)} min={1} max={100} />
        <DatePicker value={endDate} onChange={setEndDate} placeholder="基准日期（默认最新）" />
      </Space>
      <Table<GainerItem>
        rowKey="ts_code"
        dataSource={data}
        loading={loading}
        size="small"
        pagination={false}
        columns={[
          { title: '代码', dataIndex: 'ts_code', width: 110 },
          { title: '简称', dataIndex: 'name', width: 120 },
          { title: '行业', dataIndex: 'industry', width: 140 },
          { title: '基准日', dataIndex: 'base_date', width: 110 },
          { title: '基准价', dataIndex: 'base_close', width: 100 },
          { title: '当前价', dataIndex: 'end_close', width: 100 },
          {
            title: '涨幅%', dataIndex: 'pct_chg', width: 100,
            render: (v: number) => <span style={{ color: v >= 0 ? '#f5222d' : '#52c41a', fontWeight: 600 }}>{v?.toFixed(2)}</span>,
          },
        ]}
      />
    </Card>
  );
}

function SectorGainers() {
  const [top, setTop] = useState(5);
  const [type, setType] = useState<string | undefined>();
  const [date, setDate] = useState<Dayjs | null>(dayjs());
  const [data, setData] = useState<SectorGainerItem[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get<RankingResponse<SectorGainerItem>>('/rankings/sectors', {
        params: { top, type, trade_date: date?.format('YYYY-MM-DD') },
      });
      setData(r.data.items || []);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [top, type, date]);

  return (
    <Card title="板块涨幅前 Top">
      <Space style={{ marginBottom: 12 }}>
        <DatePicker value={date} onChange={setDate} />
        <InputNumber value={top} onChange={(v) => setTop((v as number) || 5)} min={1} max={50} />
        <Select
          value={type}
          onChange={setType}
          allowClear
          placeholder="类型"
          style={{ width: 100 }}
          options={[{ value: 'I', label: '行业' }, { value: 'C', label: '概念' }]}
        />
      </Space>
      <Table<SectorGainerItem>
        rowKey="sector_code"
        dataSource={data}
        loading={loading}
        size="small"
        pagination={false}
        columns={[
          { title: '代码', dataIndex: 'sector_code', width: 160 },
          { title: '名称', dataIndex: 'name', width: 200 },
          { title: '类型', dataIndex: 'type', width: 80, render: (v) => v === 'I' ? '行业' : v === 'C' ? '概念' : v },
          { title: '收盘', dataIndex: 'close', width: 100 },
          {
            title: '涨幅%', dataIndex: 'pct_chg', width: 100,
            render: (v: number) => <span style={{ color: v >= 0 ? '#f5222d' : '#52c41a', fontWeight: 600 }}>{v?.toFixed(2)}</span>,
          },
          { title: '成交额', dataIndex: 'amount', width: 120 },
        ]}
      />
    </Card>
  );
}
