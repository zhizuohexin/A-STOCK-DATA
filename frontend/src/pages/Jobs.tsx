import { Button, Select, Space, Table, Tag, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { api, type JobRun } from '../api/client';

const { Title } = Typography;

export default function Jobs() {
  const [data, setData] = useState<JobRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [jobName, setJobName] = useState<string | undefined>();

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get<JobRun[]>('/jobs/runs', { params: { job_name: jobName, limit: 100 } });
      setData(r.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [jobName]);

  return (
    <div>
      <Title level={3}>任务日志</Title>
      <Space style={{ marginBottom: 12 }}>
        <Select
          allowClear
          placeholder="任务名过滤"
          value={jobName}
          onChange={setJobName}
          style={{ width: 220 }}
          options={[
            { value: 'daily_job', label: 'daily_job' },
            { value: 'cleanup_intraday', label: 'cleanup_intraday' },
            { value: 'backfill_quotes', label: 'backfill_quotes' },
            { value: 'backfill_limit_up', label: 'backfill_limit_up' },
            { value: 'backfill_sector_daily', label: 'backfill_sector_daily' },
            { value: 'sync_stock_list', label: 'sync_stock_list' },
            { value: 'sync_sectors', label: 'sync_sectors' },
            { value: 'fetch_intraday', label: 'fetch_intraday' },
          ]}
        />
        <Button onClick={load}>刷新</Button>
      </Space>
      <Table<JobRun>
        rowKey="id"
        dataSource={data}
        loading={loading}
        size="small"
        pagination={{ pageSize: 20 }}
        columns={[
          { title: '任务', dataIndex: 'job_name', width: 200 },
          {
            title: '状态', dataIndex: 'status', width: 100,
            render: (v) => <Tag color={v === 'success' ? 'green' : v === 'partial' ? 'orange' : 'red'}>{v}</Tag>,
          },
          { title: '信息', dataIndex: 'message', ellipsis: true },
          { title: '行数', dataIndex: 'rows_affected', width: 100 },
          { title: '开始时间', dataIndex: 'started_at', width: 180 },
          { title: '结束时间', dataIndex: 'finished_at', width: 180 },
        ]}
      />
    </div>
  );
}
