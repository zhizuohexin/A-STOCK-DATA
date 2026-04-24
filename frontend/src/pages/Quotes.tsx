import { Button, DatePicker, Divider, Input, Modal, Popconfirm, Popover, Space, Table, Tag, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import dayjs, { type Dayjs } from 'dayjs';
import { api, type DailyQuote } from '../api/client';
import { PctCell, numSorter, strSorter } from '../components/PctCell';
import { formatYi } from '../components/format';

const { Title } = Typography;

export default function Quotes() {
  const [data, setData] = useState<DailyQuote[]>([]);
  const [loading, setLoading] = useState(false);
  const [code, setCode] = useState('');
  const [queryDate, setQueryDate] = useState<Dayjs | null>(dayjs());
  const [concept, setConcept] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const d = queryDate?.format('YYYY-MM-DD');
      const r = await api.get<DailyQuote[]>('/quotes', {
        params: {
          code: code || undefined,
          start: d,
          end: d,
          concept: concept || undefined,
          limit: 2000,
        },
      });
      setData(r.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  // --- 批量操作：回溯 / 删除（单独 Modal 管理日期区间） ---
  const [batchOpen, setBatchOpen] = useState<'backfill' | 'delete' | null>(null);
  const [batchRange, setBatchRange] = useState<[Dayjs | null, Dayjs | null]>([dayjs().subtract(7, 'day'), dayjs()]);
  const [batchCode, setBatchCode] = useState('');

  const runBackfill = async () => {
    if (!batchRange[0] || !batchRange[1]) { message.warning('请选日期范围'); return; }
    if (batchRange[1].diff(batchRange[0], 'day') > 31) { message.warning('回溯最多 31 天'); return; }
    const hide = message.loading('回溯中...', 0);
    try {
      const r = await api.post('/quotes/backfill', {
        start_date: batchRange[0].format('YYYY-MM-DD'),
        end_date: batchRange[1].format('YYYY-MM-DD'),
      });
      message.success(`回溯完成：${r.data.days_processed} 天，${r.data.rows_upserted} 条`);
      setBatchOpen(null);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '回溯失败');
    } finally { hide(); }
  };

  const runDelete = async () => {
    if (!batchCode && !batchRange[0] && !batchRange[1]) {
      message.warning('code 或日期范围至少填一个');
      return;
    }
    try {
      const r = await api.delete('/quotes', {
        params: {
          code: batchCode || undefined,
          start: batchRange[0]?.format('YYYY-MM-DD'),
          end: batchRange[1]?.format('YYYY-MM-DD'),
        },
      });
      message.success(`已删除 ${r.data.rows_deleted} 条`);
      setBatchOpen(null);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '删除失败');
    }
  };

  return (
    <div>
      <Title level={3}>日线行情</Title>
      <Space wrap style={{ marginBottom: 12 }}>
        <Input
          placeholder="ts_code e.g. 000001.SZ（可空）"
          value={code}
          onChange={e => setCode(e.target.value)}
          style={{ width: 220 }}
          allowClear
        />
        <DatePicker value={queryDate} onChange={setQueryDate} placeholder="交易日" />
        <Input
          placeholder="题材筛选 e.g. 算力"
          value={concept}
          onChange={(e) => setConcept(e.target.value)}
          style={{ width: 180 }}
          allowClear
        />
        <Button type="primary" onClick={load}>查询</Button>
        <Divider type="vertical" />
        <Button onClick={() => setBatchOpen('backfill')}>回溯入库…</Button>
        <Button danger onClick={() => setBatchOpen('delete')}>批量删除…</Button>
      </Space>
      <div style={{ color: '#888', marginBottom: 8, fontSize: 12 }}>
        查询按<b>单日</b>展示（可带 code 过滤）；回溯/删除在弹窗里用<b>区间</b>操作。
      </div>
      <Table<DailyQuote>
        rowKey={(r) => `${r.ts_code}-${r.trade_date}`}
        dataSource={data}
        loading={loading}
        size="small"
        pagination={{ pageSize: 50 }}
        columns={[
          { title: '日期', dataIndex: 'trade_date', width: 110, sorter: strSorter('trade_date') },
          { title: '代码', dataIndex: 'ts_code', width: 110, sorter: strSorter('ts_code') },
          { title: '简称', dataIndex: 'name', width: 110, sorter: strSorter('name') },
          { title: '行业', dataIndex: 'industry', width: 120, sorter: strSorter('industry') },
          {
            title: '题材', dataIndex: 'concepts', width: 260,
            render: (concepts: string[]) => {
              if (!concepts || concepts.length === 0) return <span style={{ color: '#ccc' }}>-</span>;
              const shown = concepts.slice(0, 3);
              const rest = concepts.slice(3);
              return (
                <Space size={2} wrap>
                  {shown.map((c) => (
                    <Tag key={c} color="blue" style={{ margin: 0, cursor: 'pointer' }} onClick={() => setConcept(c)}>{c}</Tag>
                  ))}
                  {rest.length > 0 && (
                    <Popover
                      title={`全部 ${concepts.length} 个题材`}
                      content={
                        <Space wrap style={{ maxWidth: 400 }}>
                          {concepts.map((c) => (
                            <Tag key={c} color="blue" style={{ cursor: 'pointer' }} onClick={() => setConcept(c)}>{c}</Tag>
                          ))}
                        </Space>
                      }
                    >
                      <Tag style={{ margin: 0, cursor: 'pointer' }}>+{rest.length}</Tag>
                    </Popover>
                  )}
                </Space>
              );
            },
          },
          { title: '开盘', dataIndex: 'open', width: 80, sorter: numSorter('open') },
          { title: '最高', dataIndex: 'high', width: 80, sorter: numSorter('high') },
          { title: '最低', dataIndex: 'low', width: 80, sorter: numSorter('low') },
          { title: '收盘', dataIndex: 'close', width: 80, sorter: numSorter('close') },
          {
            title: '涨跌幅%', dataIndex: 'pct_chg', width: 100,
            sorter: numSorter('pct_chg'),
            defaultSortOrder: 'descend',
            render: (v: number | null) => <PctCell value={v} />,
          },
          { title: '成交量(亿手)', dataIndex: 'vol', width: 110, sorter: numSorter('vol'), render: (v) => formatYi(v, 'shou', '亿手') },
          { title: '成交额(亿)', dataIndex: 'amount', width: 110, sorter: numSorter('amount'), render: (v) => formatYi(v, 'qianyuan', '亿') },
          { title: '换手率%', dataIndex: 'turnover_rate', width: 100, sorter: numSorter('turnover_rate') },
        ]}
      />

      <Modal
        title={batchOpen === 'backfill' ? '回溯日线入库' : '批量删除日线'}
        open={batchOpen !== null}
        onCancel={() => setBatchOpen(null)}
        footer={
          batchOpen === 'backfill' ? (
            <Button type="primary" onClick={runBackfill}>确认回溯</Button>
          ) : (
            <Popconfirm title="确认删除？不可恢复" onConfirm={runDelete}>
              <Button danger type="primary">确认删除</Button>
            </Popconfirm>
          )
        }
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <div style={{ marginBottom: 4 }}>日期范围{batchOpen === 'backfill' ? '（≤31 天）' : '（可选）'}</div>
            <DatePicker.RangePicker
              value={batchRange}
              onChange={(v) => setBatchRange((v as [Dayjs, Dayjs]) || [null, null])}
              style={{ width: '100%' }}
            />
          </div>
          {batchOpen === 'delete' && (
            <div>
              <div style={{ marginBottom: 4 }}>ts_code（可选，不填删指定范围全部）</div>
              <Input placeholder="e.g. 000001.SZ" value={batchCode} onChange={(e) => setBatchCode(e.target.value)} />
            </div>
          )}
          {batchOpen === 'backfill' && (
            <div style={{ color: '#888', fontSize: 12 }}>
              将调用 Tushare 的 <code>daily</code> 接口，区间内每个工作日都会拉取并 upsert。
            </div>
          )}
        </Space>
      </Modal>
    </div>
  );
}
