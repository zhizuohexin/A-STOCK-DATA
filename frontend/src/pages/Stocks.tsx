import { Button, Input, Space, Table, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { api, type Stock } from '../api/client';

const { Title } = Typography;

export default function Stocks() {
  const [data, setData] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get<Stock[]>('/stocks', { params: { q: q || undefined, limit: 500 } });
      setData(r.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const sync = async () => {
    const hide = message.loading('从 Tushare 拉取股票列表...', 0);
    try {
      const r = await api.post('/stocks/sync');
      message.success(`同步成功：${r.data.rows_upserted} 条`);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '同步失败');
    } finally { hide(); }
  };

  return (
    <div>
      <Title level={3}>股票列表</Title>
      <Space style={{ marginBottom: 12 }}>
        <Input.Search
          placeholder="代码/简称"
          value={q}
          onChange={e => setQ(e.target.value)}
          onSearch={load}
          style={{ width: 240 }}
        />
        <Button type="primary" onClick={sync}>从 Tushare 同步</Button>
      </Space>
      <Table<Stock>
        rowKey="ts_code"
        dataSource={data}
        loading={loading}
        size="small"
        pagination={{ pageSize: 20 }}
        columns={[
          { title: '代码', dataIndex: 'ts_code', width: 120 },
          { title: '简称', dataIndex: 'name', width: 120 },
          { title: '行业', dataIndex: 'industry', width: 140 },
          { title: '地区', dataIndex: 'area', width: 100 },
          { title: '市场', dataIndex: 'market', width: 100 },
          { title: '上市日期', dataIndex: 'list_date', width: 120 },
        ]}
      />
    </div>
  );
}
