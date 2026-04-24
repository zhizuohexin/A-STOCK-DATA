import { Button, DatePicker, InputNumber, Space, Table, Tag, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import dayjs, { type Dayjs } from 'dayjs';
import { api, type LimitUp as LimitUpRow } from '../api/client';

const { Title } = Typography;

export default function LimitUp() {
  const [data, setData] = useState<LimitUpRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [date, setDate] = useState<Dayjs | null>(dayjs());
  const [minLimit, setMinLimit] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get<LimitUpRow[]>('/limit-up', {
        params: {
          trade_date: date?.format('YYYY-MM-DD'),
          min_limit_times: minLimit ?? undefined,
          limit: 500,
        },
      });
      setData(r.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const backfill = async () => {
    if (!date) { message.warning('请选日期'); return; }
    const hide = message.loading('拉取中...', 0);
    try {
      const r = await api.post('/limit-up/backfill', null, { params: { trade_date: date.format('YYYY-MM-DD') } });
      message.success(`入库 ${r.data.rows_upserted} 条`);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '失败');
    } finally { hide(); }
  };

  return (
    <div>
      <Title level={3}>涨停 / 连板</Title>
      <Space wrap style={{ marginBottom: 12 }}>
        <DatePicker value={date} onChange={setDate} />
        <InputNumber placeholder="最少连板数" value={minLimit ?? undefined} onChange={(v) => setMinLimit((v as number) ?? null)} style={{ width: 140 }} />
        <Button onClick={load}>查询</Button>
        <Button type="primary" onClick={backfill}>回溯入库</Button>
      </Space>
      <Table<LimitUpRow>
        rowKey={(r) => `${r.ts_code}-${r.trade_date}`}
        dataSource={data}
        loading={loading}
        size="small"
        pagination={{ pageSize: 30 }}
        columns={[
          { title: '日期', dataIndex: 'trade_date', width: 110 },
          { title: '代码', dataIndex: 'ts_code', width: 110 },
          { title: '简称', dataIndex: 'name', width: 120 },
          { title: '收盘', dataIndex: 'close', width: 80 },
          {
            title: '涨跌幅%', dataIndex: 'pct_chg', width: 90,
            render: (v: number | null) => v == null ? '-' : <Tag color="red">{v.toFixed(2)}</Tag>,
          },
          {
            title: '连板数', dataIndex: 'limit_times', width: 80,
            render: (v: number | null) => v == null ? '-' : <Tag color={v >= 3 ? 'magenta' : 'volcano'}>{v}板</Tag>,
          },
          { title: '首次封板', dataIndex: 'first_time', width: 100 },
          { title: '最后封板', dataIndex: 'last_time', width: 100 },
          { title: '封单金额', dataIndex: 'fd_amount', width: 120 },
          { title: '炸板次数', dataIndex: 'open_times', width: 90 },
        ]}
      />
    </div>
  );
}
