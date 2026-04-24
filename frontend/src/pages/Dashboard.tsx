import { Card, Col, Row, Statistic, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { api, type JobRun } from '../api/client';

const { Title, Paragraph } = Typography;

type Counts = {
  stocks?: number;
  daily_quotes?: number;
  limit_up?: number;
  sectors?: number;
  intraday?: number;
};

export default function Dashboard() {
  const [counts, setCounts] = useState<Counts>({});
  const [jobs, setJobs] = useState<JobRun[]>([]);
  const [health, setHealth] = useState<string>('...');

  useEffect(() => {
    api.get('/health').then(r => setHealth(r.data.status)).catch(() => setHealth('down'));
    api.get<JobRun[]>('/jobs/runs', { params: { limit: 5 } }).then(r => setJobs(r.data));
    // 各表 count 简单通过拉第 1 条估算，不做聚合接口
    Promise.all([
      api.get('/stocks', { params: { limit: 1 } }),
      api.get('/quotes', { params: { limit: 1 } }),
      api.get('/limit-up', { params: { limit: 1 } }),
      api.get('/sectors'),
    ]).then(([s, q, l, sec]) => {
      setCounts({
        stocks: Array.isArray(s.data) ? s.data.length : 0,
        daily_quotes: Array.isArray(q.data) ? q.data.length : 0,
        limit_up: Array.isArray(l.data) ? l.data.length : 0,
        sectors: Array.isArray(sec.data) ? sec.data.length : 0,
      });
    });
  }, []);

  return (
    <div>
      <Title level={3}>Dashboard</Title>
      <Paragraph type="secondary">
        后端状态：<b>{health}</b>
      </Paragraph>
      <Row gutter={16}>
        <Col span={6}><Card><Statistic title="股票（最近抽样）" value={counts.stocks ?? 0} /></Card></Col>
        <Col span={6}><Card><Statistic title="日线记录" value={counts.daily_quotes ?? 0} /></Card></Col>
        <Col span={6}><Card><Statistic title="涨停记录" value={counts.limit_up ?? 0} /></Card></Col>
        <Col span={6}><Card><Statistic title="板块" value={counts.sectors ?? 0} /></Card></Col>
      </Row>

      <Card title="最近任务" style={{ marginTop: 16 }}>
        {jobs.length === 0 ? <Paragraph type="secondary">暂无任务记录</Paragraph> : (
          <ul>
            {jobs.map(j => (
              <li key={j.id}>
                [{j.status}] <b>{j.job_name}</b> — {j.message || '-'} (rows={j.rows_affected ?? '-'}, {j.started_at})
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
