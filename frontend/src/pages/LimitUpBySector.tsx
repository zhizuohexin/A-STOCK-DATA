import { Card, Collapse, DatePicker, Empty, Space, Table, Tag, Typography } from 'antd';
import { useEffect, useState } from 'react';
import type { Dayjs } from 'dayjs';
import { api } from '../api/client';
import { PctCell, numSorter } from '../components/PctCell';
import { formatYi } from '../components/format';

const { Title, Text } = Typography;

type Stock = {
  ts_code: string;
  name: string | null;
  close: number | null;
  pct_chg: number | null;
  limit_times: number | null;
  first_time: string | null;
  last_time: string | null;
  fd_amount: number | null;
  amount: number | null;
  open_times: number | null;
};
type SectorGroup = {
  industry: string;
  count: number;
  max_consecutive: number;
  stocks: Stock[];
};
type Resp = {
  trade_date: string | null;
  sectors: SectorGroup[];
};

export default function LimitUpBySector() {
  const [date, setDate] = useState<Dayjs | null>(null);
  const [data, setData] = useState<Resp | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get<Resp>('/limit-up/by-sector', {
        params: { trade_date: date?.format('YYYY-MM-DD') },
      });
      setData(r.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [date]);

  const sectors = data?.sectors || [];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>涨停板块热度</Title>
        <DatePicker value={date} onChange={setDate} placeholder={data?.trade_date ? `默认：${data.trade_date}` : '选日期'} />
        <Text type="secondary">
          共 {sectors.length} 个板块有涨停，总计 {sectors.reduce((s, x) => s + x.count, 0)} 只涨停
        </Text>
      </Space>

      {sectors.length === 0 ? (
        <Card><Empty description="该日期无涨停数据（需要先回溯涨停池）" /></Card>
      ) : (
        <Collapse
          size="small"
          defaultActiveKey={sectors.slice(0, 3).map(s => s.industry)}
          items={sectors.map(sec => ({
            key: sec.industry,
            label: (
              <Space>
                <Tag color="red" style={{ fontSize: 14, padding: '2px 8px' }}>
                  {sec.count} 家涨停
                </Tag>
                <span style={{ fontWeight: 600, fontSize: 15 }}>{sec.industry}</span>
                {sec.max_consecutive > 1 && (
                  <Tag color="magenta">最高 {sec.max_consecutive} 连板</Tag>
                )}
              </Space>
            ),
            children: (
              <Table<Stock>
                rowKey="ts_code"
                dataSource={sec.stocks}
                loading={loading}
                size="small"
                pagination={false}
                columns={[
                  { title: '代码', dataIndex: 'ts_code', width: 100 },
                  { title: '简称', dataIndex: 'name', width: 110 },
                  { title: '现价', dataIndex: 'close', width: 80, sorter: numSorter('close') },
                  {
                    title: '涨跌幅', dataIndex: 'pct_chg', width: 90,
                    sorter: numSorter('pct_chg'),
                    render: (v: number | null) => <PctCell value={v} />,
                  },
                  {
                    title: '连板',
                    dataIndex: 'limit_times',
                    width: 80,
                    sorter: numSorter('limit_times'),
                    defaultSortOrder: 'descend',
                    render: (v: number | null) =>
                      v == null ? '-' :
                        <Tag color={v >= 3 ? 'magenta' : v >= 2 ? 'volcano' : 'orange'}>
                          {v}板
                        </Tag>,
                  },
                  { title: '首次封板', dataIndex: 'first_time', width: 100 },
                  { title: '最后封板', dataIndex: 'last_time', width: 100 },
                  {
                    title: '封单(亿)', dataIndex: 'fd_amount', width: 100,
                    sorter: numSorter('fd_amount'),
                    render: (v) => formatYi(v, 'yuan', '亿'),
                  },
                  {
                    title: '成交额(亿)', dataIndex: 'amount', width: 110,
                    sorter: numSorter('amount'),
                    render: (v) => formatYi(v, 'yuan', '亿'),
                  },
                  { title: '炸板', dataIndex: 'open_times', width: 70, sorter: numSorter('open_times') },
                ]}
              />
            ),
          }))}
        />
      )}
    </div>
  );
}
