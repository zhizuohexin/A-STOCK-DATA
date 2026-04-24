import { Button, DatePicker, Space, Table, Tabs, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import dayjs, { type Dayjs } from 'dayjs';
import { api, type Sector, type SectorDaily } from '../api/client';

const { Title } = Typography;

export default function Sectors() {
  return (
    <div>
      <Title level={3}>板块</Title>
      <Tabs
        items={[
          { key: 'list', label: '板块列表', children: <SectorList /> },
          { key: 'daily', label: '板块日线', children: <SectorDailyView /> },
        ]}
      />
    </div>
  );
}

function SectorList() {
  const [data, setData] = useState<Sector[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get<Sector[]>('/sectors');
      setData(r.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const sync = async () => {
    const hide = message.loading('从 Tushare 同步板块...', 0);
    try {
      const r = await api.post('/sectors/sync');
      message.success(`同步 ${r.data.rows_upserted} 条`);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '失败');
    } finally { hide(); }
  };

  return (
    <>
      <Space style={{ marginBottom: 12 }}>
        <Button type="primary" onClick={sync}>从 Tushare 同步</Button>
      </Space>
      <Table<Sector>
        rowKey="ts_code"
        dataSource={data}
        loading={loading}
        size="small"
        pagination={{ pageSize: 20 }}
        columns={[
          { title: '代码', dataIndex: 'ts_code', width: 180 },
          { title: '名称', dataIndex: 'name', width: 240 },
          {
            title: '类型', dataIndex: 'type', width: 80,
            render: (v: string) => v === 'I' ? '行业' : v === 'C' ? '概念' : v,
          },
        ]}
      />
    </>
  );
}

function SectorDailyView() {
  const [data, setData] = useState<SectorDaily[]>([]);
  const [loading, setLoading] = useState(false);
  const [date, setDate] = useState<Dayjs | null>(dayjs());

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get<SectorDaily[]>('/sectors/daily', {
        params: { trade_date: date?.format('YYYY-MM-DD'), limit: 500 },
      });
      setData(r.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const backfill = async () => {
    if (!date) return;
    const hide = message.loading('拉取中...', 0);
    try {
      const r = await api.post('/sectors/daily/backfill', null, { params: { trade_date: date.format('YYYY-MM-DD') } });
      message.success(`入库 ${r.data.rows_upserted} 条`);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '失败');
    } finally { hide(); }
  };

  return (
    <>
      <Space style={{ marginBottom: 12 }}>
        <DatePicker value={date} onChange={setDate} />
        <Button onClick={load}>查询</Button>
        <Button type="primary" onClick={backfill}>回溯入库</Button>
      </Space>
      <Table<SectorDaily>
        rowKey={(r) => `${r.sector_code}-${r.trade_date}`}
        dataSource={data}
        loading={loading}
        size="small"
        pagination={{ pageSize: 30 }}
        columns={[
          { title: '日期', dataIndex: 'trade_date', width: 110 },
          { title: '板块代码', dataIndex: 'sector_code', width: 140 },
          { title: '名称', dataIndex: 'name', width: 200 },
          { title: '收盘', dataIndex: 'close', width: 100 },
          {
            title: '涨跌幅%', dataIndex: 'pct_chg', width: 100,
            render: (v: number | null) => v == null ? '-' : <span style={{ color: v >= 0 ? '#f5222d' : '#52c41a' }}>{v.toFixed(2)}</span>,
          },
          { title: '成交量', dataIndex: 'vol', width: 120 },
          { title: '成交额', dataIndex: 'amount', width: 120 },
        ]}
      />
    </>
  );
}
