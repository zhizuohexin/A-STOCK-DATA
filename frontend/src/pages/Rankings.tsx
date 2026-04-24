import { Card, DatePicker, InputNumber, Select, Space, Table, Tabs, Tag, Typography } from 'antd';
import { useEffect, useState } from 'react';
import type { Dayjs } from 'dayjs';
import { api, type GainerItem, type RankingResponse, type SectorGainerItem } from '../api/client';
import { PctCell, numSorter, strSorter } from '../components/PctCell';
import { formatYi } from '../components/format';

const { Title } = Typography;

export default function Rankings() {
  return (
    <div>
      <Title level={3}>排行榜</Title>
      <Tabs
        size="large"
        items={[
          { key: 'stocks', label: 'N 日涨幅（个股）', children: <NDayStockGainers /> },
          { key: 'sectors', label: 'N 日累计涨幅（板块）', children: <NDaySectorGainers /> },
          { key: 'freq', label: '妖股榜（N 日涨停次数）', children: <LimitUpFrequency /> },
        ]}
      />
    </div>
  );
}

function NDayStockGainers() {
  const [days, setDays] = useState(5);
  const [top, setTop] = useState(20);
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
    <Card>
      <Space style={{ marginBottom: 12 }}>
        <Select
          value={days} onChange={setDays}
          options={[5, 10, 20, 30, 60].map(v => ({ value: v, label: `${v} 日` }))}
          style={{ width: 100 }}
        />
        <InputNumber value={top} onChange={(v) => setTop((v as number) || 20)} min={1} max={100} />
        <DatePicker value={endDate} onChange={setEndDate} placeholder="基准日期（默认最新）" />
      </Space>
      <Table<GainerItem>
        rowKey="ts_code"
        dataSource={data}
        loading={loading}
        size="small"
        pagination={{ pageSize: 50 }}
        columns={[
          { title: '排名', width: 60, render: (_, __, i) => i + 1 },
          { title: '代码', dataIndex: 'ts_code', width: 110, sorter: strSorter('ts_code') },
          { title: '简称', dataIndex: 'name', width: 110 },
          { title: '行业', dataIndex: 'industry', width: 130, sorter: strSorter('industry') },
          { title: '基准日', dataIndex: 'base_date', width: 110, sorter: strSorter('base_date') },
          { title: '基准价', dataIndex: 'base_close', width: 90, sorter: numSorter('base_close') },
          { title: '当前价', dataIndex: 'end_close', width: 90, sorter: numSorter('end_close') },
          {
            title: '涨幅%', dataIndex: 'pct_chg', width: 110,
            sorter: numSorter('pct_chg'),
            defaultSortOrder: 'descend',
            render: (v: number) => <PctCell value={v} />,
          },
        ]}
      />
    </Card>
  );
}

function NDaySectorGainers() {
  const [days, setDays] = useState(1);
  const [top, setTop] = useState(10);
  const [date, setDate] = useState<Dayjs | null>(null);
  const [type, setType] = useState<string | undefined>();
  const [data, setData] = useState<SectorGainerItem[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get<RankingResponse<SectorGainerItem>>('/rankings/sectors', {
        params: { days, top, type, trade_date: date?.format('YYYY-MM-DD') },
      });
      setData(r.data.items || []);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [days, top, type, date]);

  return (
    <Card>
      <Space style={{ marginBottom: 12 }}>
        <Select
          value={days} onChange={setDays}
          options={[1, 3, 5, 10, 20, 30].map(v => ({ value: v, label: v === 1 ? '当日' : `${v} 日累计` }))}
          style={{ width: 110 }}
        />
        <InputNumber value={top} onChange={(v) => setTop((v as number) || 10)} min={1} max={50} />
        <DatePicker value={date} onChange={setDate} placeholder="基准日期" />
        <Select
          value={type} onChange={setType} allowClear placeholder="类型"
          style={{ width: 100 }}
          options={[{ value: 'I', label: '行业' }, { value: 'C', label: '概念' }]}
        />
      </Space>
      <Table<SectorGainerItem>
        rowKey="sector_code"
        dataSource={data}
        loading={loading}
        size="small"
        pagination={{ pageSize: 50 }}
        columns={[
          { title: '排名', width: 60, render: (_: unknown, __: SectorGainerItem, i: number) => i + 1 },
          { title: '板块', dataIndex: 'name', width: 180 },
          { title: '类型', dataIndex: 'type', width: 80, render: (v: string | null) => v === 'I' ? '行业' : v === 'C' ? '概念' : v },
          {
            title: '涨幅%', dataIndex: 'pct_chg', width: 110,
            sorter: numSorter('pct_chg'),
            defaultSortOrder: 'descend' as const,
            render: (v: number | null) => <PctCell value={v} />,
          },
          {
            title: '成交额(亿)', dataIndex: 'amount', width: 120,
            sorter: numSorter('amount'),
            render: (v: number | null) => v == null ? (days === 1 ? '-' : '—') : formatYi(v, 'yuan', '亿'),
          },
        ]}
      />
    </Card>
  );
}

type FreqItem = {
  ts_code: string;
  name: string | null;
  industry: string | null;
  limit_up_count: number;
  max_consecutive: number | null;
  dates: string;
};

function LimitUpFrequency() {
  const [days, setDays] = useState(10);
  const [top, setTop] = useState(30);
  const [endDate, setEndDate] = useState<Dayjs | null>(null);
  const [data, setData] = useState<FreqItem[]>([]);
  const [range, setRange] = useState<{ start: string | null; end: string | null }>({ start: null, end: null });
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get('/rankings/limit-up-frequency', {
        params: { days, top, end_date: endDate?.format('YYYY-MM-DD') },
      });
      setData(r.data.items || []);
      setRange({ start: r.data.start_date, end: r.data.end_date });
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [days, top, endDate]);

  return (
    <Card>
      <Space style={{ marginBottom: 12 }}>
        <Select
          value={days} onChange={setDays}
          options={[5, 10, 20, 30, 60].map(v => ({ value: v, label: `近 ${v} 日` }))}
          style={{ width: 110 }}
        />
        <InputNumber value={top} onChange={(v) => setTop((v as number) || 30)} min={1} max={100} />
        <DatePicker value={endDate} onChange={setEndDate} placeholder="基准日期" />
        <span style={{ color: '#888', fontSize: 12 }}>
          {range.start && range.end ? `实际区间：${range.start} ~ ${range.end}` : ''}
        </span>
      </Space>
      <Table<FreqItem>
        rowKey="ts_code"
        dataSource={data}
        loading={loading}
        size="small"
        pagination={{ pageSize: 50 }}
        columns={[
          { title: '排名', width: 60, render: (_, __, i) => i + 1 },
          { title: '代码', dataIndex: 'ts_code', width: 110, sorter: strSorter('ts_code') },
          { title: '简称', dataIndex: 'name', width: 110 },
          { title: '行业', dataIndex: 'industry', width: 140, sorter: strSorter('industry') },
          {
            title: '涨停次数', dataIndex: 'limit_up_count', width: 100,
            sorter: numSorter('limit_up_count'),
            defaultSortOrder: 'descend',
            render: (v: number) => <Tag color="red" style={{ fontSize: 13 }}>{v} 次</Tag>,
          },
          {
            title: '最高连板', dataIndex: 'max_consecutive', width: 100,
            sorter: numSorter('max_consecutive'),
            render: (v: number | null) =>
              v == null ? '-' :
                <Tag color={v >= 3 ? 'magenta' : 'volcano'}>{v} 连板</Tag>,
          },
          { title: '涨停日期', dataIndex: 'dates', ellipsis: true },
        ]}
      />
    </Card>
  );
}
