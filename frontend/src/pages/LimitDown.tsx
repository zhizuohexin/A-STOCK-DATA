import { Button, DatePicker, Space, Table, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import dayjs, { type Dayjs } from 'dayjs';
import { api, type LimitUp as LimitRow } from '../api/client';
import { PctCell, numSorter, strSorter } from '../components/PctCell';
import { formatYi } from '../components/format';

const { Title } = Typography;

export default function LimitDown() {
  const [data, setData] = useState<LimitRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [date, setDate] = useState<Dayjs | null>(dayjs());

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get<LimitRow[]>('/limit-down', {
        params: { trade_date: date?.format('YYYY-MM-DD'), limit: 500 },
      });
      setData(r.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const backfill = async () => {
    if (!date) { message.warning('请选日期'); return; }
    const hide = message.loading('拉取中...', 0);
    try {
      const r = await api.post('/limit-down/backfill', null, { params: { trade_date: date.format('YYYY-MM-DD') } });
      message.success(`入库 ${r.data.rows_upserted} 条`);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '失败');
    } finally { hide(); }
  };

  return (
    <div>
      <Title level={3}>今日跌停</Title>
      <Space wrap style={{ marginBottom: 12 }}>
        <DatePicker value={date} onChange={setDate} />
        <Button onClick={load}>查询</Button>
        <Button type="primary" onClick={backfill}>回溯入库</Button>
      </Space>
      <Table<LimitRow>
        rowKey={(r) => `${r.ts_code}-${r.trade_date}`}
        dataSource={data}
        loading={loading}
        size="small"
        pagination={{ pageSize: 50 }}
        columns={[
          { title: '日期', dataIndex: 'trade_date', width: 110, sorter: strSorter('trade_date') },
          { title: '代码', dataIndex: 'ts_code', width: 120, sorter: strSorter('ts_code') },
          { title: '简称', dataIndex: 'name', width: 120 },
          { title: '收盘', dataIndex: 'close', width: 90, sorter: numSorter('close') },
          {
            title: '涨跌幅%', dataIndex: 'pct_chg', width: 110,
            sorter: numSorter('pct_chg'),
            defaultSortOrder: 'ascend',  // 跌停默认跌幅从大到小（最负在前）
            render: (v: number | null) => <PctCell value={v} />,
          },
          { title: '首次封板', dataIndex: 'first_time', width: 110 },
          { title: '最后封板', dataIndex: 'last_time', width: 110 },
          { title: '封单金额(亿)', dataIndex: 'fd_amount', width: 120, sorter: numSorter('fd_amount'), render: (v) => formatYi(v, 'yuan', '亿') },
          { title: '炸板次数', dataIndex: 'open_times', width: 100, sorter: numSorter('open_times') },
          { title: '成交额(亿)', dataIndex: 'amount', width: 120, sorter: numSorter('amount'), render: (v) => formatYi(v, 'yuan', '亿') },
        ]}
      />
    </div>
  );
}
