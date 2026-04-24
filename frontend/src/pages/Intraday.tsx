import { Button, DatePicker, Input, Space, Table, Typography, message } from 'antd';
import { useState } from 'react';
import dayjs, { type Dayjs } from 'dayjs';
import { api, type IntradayBar } from '../api/client';

const { Title, Paragraph } = Typography;

export default function Intraday() {
  const [code, setCode] = useState('');
  const [date, setDate] = useState<Dayjs | null>(dayjs());
  const [data, setData] = useState<IntradayBar[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    if (!code) { message.warning('请输入 ts_code'); return; }
    setLoading(true);
    try {
      const r = await api.get<IntradayBar[]>('/intraday', {
        params: { code, trade_date: date?.format('YYYY-MM-DD'), limit: 500 },
      });
      setData(r.data);
    } finally { setLoading(false); }
  };

  const fetchNow = async () => {
    if (!code || !date) { message.warning('请填代码和日期'); return; }
    const hide = message.loading('从 Tushare 拉取分钟K线...', 0);
    try {
      const r = await api.post('/intraday/fetch', null, {
        params: { code, trade_date: date.format('YYYY-MM-DD'), freq: '1min' },
      });
      message.success(`入库 ${r.data.rows_upserted} 条`);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '失败');
    } finally { hide(); }
  };

  return (
    <div>
      <Title level={3}>盘中分时（1 分钟）</Title>
      <Paragraph type="secondary">分时数据只保留最新一天，每天凌晨会清理旧数据。Tushare 需 2000+ 积分。</Paragraph>
      <Space style={{ marginBottom: 12 }}>
        <Input placeholder="ts_code e.g. 000001.SZ" value={code} onChange={e => setCode(e.target.value)} style={{ width: 200 }} />
        <DatePicker value={date} onChange={setDate} />
        <Button onClick={load}>查询</Button>
        <Button type="primary" onClick={fetchNow}>拉取入库</Button>
      </Space>
      <Table<IntradayBar>
        rowKey={(r) => `${r.ts_code}-${r.bar_time}`}
        dataSource={data}
        loading={loading}
        size="small"
        pagination={{ pageSize: 30 }}
        columns={[
          { title: '时间', dataIndex: 'bar_time', width: 180 },
          { title: '开', dataIndex: 'open', width: 80 },
          { title: '高', dataIndex: 'high', width: 80 },
          { title: '低', dataIndex: 'low', width: 80 },
          { title: '收', dataIndex: 'close', width: 80 },
          { title: '成交量', dataIndex: 'vol', width: 120 },
          { title: '成交额', dataIndex: 'amount', width: 120 },
        ]}
      />
    </div>
  );
}
