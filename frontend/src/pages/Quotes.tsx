import { Button, DatePicker, Input, Popconfirm, Space, Table, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import dayjs, { type Dayjs } from 'dayjs';
import { api, type DailyQuote } from '../api/client';

const { Title } = Typography;

export default function Quotes() {
  const [data, setData] = useState<DailyQuote[]>([]);
  const [loading, setLoading] = useState(false);
  const [code, setCode] = useState('');
  const [range, setRange] = useState<[Dayjs | null, Dayjs | null]>([dayjs().subtract(7, 'day'), dayjs()]);

  const params = () => ({
    code: code || undefined,
    start: range[0]?.format('YYYY-MM-DD'),
    end: range[1]?.format('YYYY-MM-DD'),
    limit: 1000,
  });

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get<DailyQuote[]>('/quotes', { params: params() });
      setData(r.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const backfill = async () => {
    if (!range[0] || !range[1]) { message.warning('请选日期范围'); return; }
    if (range[1].diff(range[0], 'day') > 31) { message.warning('回溯最多 31 天'); return; }
    const hide = message.loading('回溯中...', 0);
    try {
      const r = await api.post('/quotes/backfill', {
        start_date: range[0].format('YYYY-MM-DD'),
        end_date: range[1].format('YYYY-MM-DD'),
      });
      message.success(`回溯完成：${r.data.days_processed} 天，${r.data.rows_upserted} 条`);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '回溯失败');
    } finally { hide(); }
  };

  const del = async () => {
    if (!code && !range[0] && !range[1]) {
      message.warning('code 或日期范围至少填一个');
      return;
    }
    try {
      const r = await api.delete('/quotes', { params: params() });
      message.success(`已删除 ${r.data.rows_deleted} 条`);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '删除失败');
    }
  };

  return (
    <div>
      <Title level={3}>日线行情</Title>
      <Space wrap style={{ marginBottom: 12 }}>
        <Input placeholder="ts_code e.g. 000001.SZ" value={code} onChange={e => setCode(e.target.value)} style={{ width: 200 }} />
        <DatePicker.RangePicker
          value={range}
          onChange={(v) => setRange((v as [Dayjs, Dayjs]) || [null, null])}
        />
        <Button onClick={load}>查询</Button>
        <Button type="primary" onClick={backfill}>回溯入库</Button>
        <Popconfirm title="确认删除这些记录？" onConfirm={del}>
          <Button danger>删除</Button>
        </Popconfirm>
      </Space>
      <Table<DailyQuote>
        rowKey={(r) => `${r.ts_code}-${r.trade_date}`}
        dataSource={data}
        loading={loading}
        size="small"
        pagination={{ pageSize: 30 }}
        columns={[
          { title: '日期', dataIndex: 'trade_date', width: 110 },
          { title: '代码', dataIndex: 'ts_code', width: 110 },
          { title: '开盘', dataIndex: 'open', width: 80 },
          { title: '最高', dataIndex: 'high', width: 80 },
          { title: '最低', dataIndex: 'low', width: 80 },
          { title: '收盘', dataIndex: 'close', width: 80 },
          {
            title: '涨跌幅%', dataIndex: 'pct_chg', width: 90,
            render: (v: number | null) => v == null ? '-' : <span style={{ color: v >= 0 ? '#f5222d' : '#52c41a' }}>{v.toFixed(2)}</span>,
          },
          { title: '成交量(手)', dataIndex: 'vol', width: 120 },
          { title: '成交额(千元)', dataIndex: 'amount', width: 120 },
          { title: '换手率%', dataIndex: 'turnover_rate', width: 100 },
        ]}
      />
    </div>
  );
}
