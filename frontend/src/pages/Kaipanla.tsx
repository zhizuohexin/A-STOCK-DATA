import { Card, Col, DatePicker, Row, Space, Statistic, Table, Tag, Typography, message } from 'antd';
import type { Dayjs } from 'dayjs';
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { PctCell } from '../components/PctCell';

const { Title, Text } = Typography;

type Sentiment = {
  trade_date: string;
  limit_up: number; actual_limit_up: number;
  limit_down: number; actual_limit_down: number;
  up_count: number; down_count: number; flat_count: number;
};

type Ladder = {
  trade_date: string;
  first_board: number; second_board: number; third_board: number; high_board: number;
  rate: number | null; comment: string | null;
};

type ConsecRow = {
  ts_code: string; name: string | null;
  days: number | null; pct_chg: number | null;
  theme: string | null; board_desc: string | null; market_cap: number | null;
};

type BrokenRow = {
  ts_code: string; name: string | null; pct_chg: number | null; sector: string | null;
};

type LhbRow = {
  ts_code: string; name: string | null; pct_chg: number | null;
  reason: string | null; buy_in: number | null; net: number | null;
};

type SeatRow = {
  trade_date: string; side: string; rank: number | null;
  broker: string; buy_in: number | null; sell_out: number | null;
  net_buy: number | null; is_dy: number;
};

type HeatStock = { ts_code: string; name: string | null; td_type?: string | null; tips?: string | null; pct_chg?: number | null };
type HeatSqlRow = { sector_code: string; sector_name: string | null; limit_up_count: number; max_consecutive: number | null; stocks: HeatStock[] };
type HeatKplRow = { sector_code: string; sector_name: string | null; count: number | null; stocks: HeatStock[] };

type AuctionRow = {
  ts_code: string; name: string | null; tag: string | null;
  direction: number | null; themes: string | null;
  pct_chg: number | null; turnover: number | null;
  net_amount: number | null; big_order_buy: number | null; big_order_sell: number | null;
  score: number | null;
};

type DashboardData = {
  trade_date: string | null;
  board: any | null;
  tops: { direction: string; rank: number; ts_code: string; name: string | null; pct_chg: number | null; sector: string | null }[];
  sectors: { sector_code: string; sector_name: string | null; pct_chg: number | null }[];
};
type EmotionData = { up_count: number; down_count: number; limit_up: number; limit_down: number; today_vol: number | null; yest_vol: number | null; vol_ratio: number | null };
type HistoryAnalysisRow = { trade_date: string; limit_up: number | null; limit_down: number | null; broken: number | null; blown: number | null; blown_rate: number | null };
type YouziTrader = { trader_id: string; name: string | null };
type YouziTrade = { trade_date: string; trader_id: string; side: string; seat_name: string | null; ts_code: string; net_amount: number | null };
type NewsSelectedRow = { article_id: number; title: string; account: string | null; create_time: string | null; img_url: string | null; related: string | null };
type WithdrawalRow = { ts_code: string; name: string | null; pct_chg: number | null; withdrawal_pct: number | null; price: number | null };
type LadderGroup = { tip: string; stocks: { ts_code: string; name: string | null; tips: string | null }[] };
type NewsItem = { news_id: number; title: string; sector: string | null; keyword: string | null; news_time: string | null; stocks: { ts_code: string; name: string | null; pct_chg: number | null; is_top: boolean }[] };
type ConceptionEvent = { event_time: number; plate_text: string; plate_name: string | null; plate_zdf: string | null; event_type: string | null };
type HistoryStrengthDay = { trade_date: string; strength: number | null; limit_up_count: number | null; max_consecutive: number | null; big_drop_count: number | null };

const fmtYi = (v: number | null) =>
  v == null ? '-' : `${(v / 1e8).toFixed(2)}亿`;

export default function Kaipanla() {
  const [date, setDate] = useState<Dayjs | null>(null);
  const [loading, setLoading] = useState(false);
  const [sentiment, setSentiment] = useState<Sentiment | null>(null);
  const [ladder, setLadder] = useState<Ladder | null>(null);
  const [consec, setConsec] = useState<ConsecRow[]>([]);
  const [broken, setBroken] = useState<BrokenRow[]>([]);
  const [lhb, setLhb] = useState<LhbRow[]>([]);
  const [auction, setAuction] = useState<AuctionRow[]>([]);
  const [heatSql, setHeatSql] = useState<HeatSqlRow[]>([]);
  const [heatKpl, setHeatKpl] = useState<HeatKplRow[]>([]);
  const [seats, setSeats] = useState<Record<string, SeatRow[]>>({});
  const [withdrawal, setWithdrawal] = useState<WithdrawalRow[]>([]);
  const [marketLadder, setMarketLadder] = useState<LadderGroup[]>([]);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [conception, setConception] = useState<ConceptionEvent[]>([]);
  const [strength, setStrength] = useState<HistoryStrengthDay[]>([]);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [emotion, setEmotion] = useState<EmotionData | null>(null);
  const [historyAnalysis, setHistoryAnalysis] = useState<HistoryAnalysisRow[]>([]);
  const [youziTraders, setYouziTraders] = useState<YouziTrader[]>([]);
  const [youziTrades, setYouziTrades] = useState<YouziTrade[]>([]);
  const [newsSelected, setNewsSelected] = useState<NewsSelectedRow[]>([]);

  const td = date?.format('YYYY-MM-DD');

  const load = async () => {
    setLoading(true);
    try {
      const params = td ? { trade_date: td } : {};
      const [s, l, c, b, lh, a, h, w, ml, n, ch, hs, dash, em, ha, yt, ytr, nsel] = await Promise.all([
        api.get('/kpl/sentiment', { params }),
        api.get('/kpl/ladder', { params }),
        api.get('/kpl/consecutive', { params }),
        api.get('/kpl/broken', { params }),
        api.get('/kpl/lhb', { params }),
        api.get('/kpl/auction', { params }),
        api.get('/kpl/sectors-heat', { params }),
        api.get('/kpl/withdrawal', { params }),
        api.get('/kpl/market-ladder', { params }),
        api.get('/kpl/news', { params: { limit: 30 } }),
        api.get('/kpl/conception-history', { params }),
        api.get('/kpl/history-strength', { params: { days: 30 } }),
        api.get('/kpl/dashboard', { params }),
        api.get('/kpl/emotion', { params }),
        api.get('/kpl/history-analysis', { params: { days: 60 } }),
        api.get('/kpl/youzi/traders'),
        api.get('/kpl/youzi/trades', { params: { ...params, limit: 200 } }),
        api.get('/kpl/news-selected', { params: { limit: 20 } }),
      ]);
      setSentiment(s.data);
      setLadder(l.data);
      setConsec(c.data?.stocks || []);
      setBroken(b.data?.stocks || []);
      setLhb(lh.data?.stocks || []);
      setAuction(a.data?.stocks || []);
      setHeatSql(h.data?.sql || []);
      setHeatKpl(h.data?.kpl || []);
      setWithdrawal(w.data?.stocks || []);
      setMarketLadder(ml.data?.groups || []);
      setNews(n.data?.news || []);
      setConception(ch.data?.events || []);
      setStrength(hs.data?.days || []);
      setDashboard(dash.data);
      setEmotion(em.data);
      setHistoryAnalysis(ha.data?.days || []);
      setYouziTraders(ytr.data?.traders || []);
      setYouziTrades(yt.data?.trades || []);
      setNewsSelected(nsel.data?.articles || []);
      setSeats({});
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [td]);

  const loadSeats = async (ts_code: string) => {
    if (seats[ts_code]) return;
    try {
      const r = await api.get(`/kpl/lhb/seats/${ts_code}`, { params: td ? { trade_date: td } : {} });
      setSeats(prev => ({ ...prev, [ts_code]: r.data?.seats || [] }));
    } catch (e) {
      message.error('席位加载失败');
    }
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>开盘啦增强复盘</Title>
        <DatePicker value={date} onChange={setDate} placeholder={sentiment?.trade_date || '选日期'} />
        <Text type="secondary">{sentiment?.trade_date ? `数据日期：${sentiment.trade_date}` : '—'}</Text>
      </Space>

      {/* 大盘情绪 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="涨停 / 实际涨停"
              value={sentiment ? `${sentiment.limit_up} / ${sentiment.actual_limit_up}` : '-'}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="跌停 / 实际跌停"
              value={sentiment ? `${sentiment.limit_down} / ${sentiment.actual_limit_down}` : '-'}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="上涨 / 下跌 / 平盘"
              value={sentiment ? `${sentiment.up_count} / ${sentiment.down_count} / ${sentiment.flat_count}` : '-'}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading} title="连板梯队">
            {ladder ? (
              <>
                <div>
                  首板 <b>{ladder.first_board}</b> · 2连 <b>{ladder.second_board}</b>
                  {' · '}3连 <b>{ladder.third_board}</b> · 高度 <b>{ladder.high_board}</b>
                </div>
                <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
                  晋级率 {ladder.rate?.toFixed(1)}% · {ladder.comment}
                </div>
              </>
            ) : '-'}
          </Card>
        </Col>
      </Row>

      {/* 涨停板块热度：SQL vs KPL 对比，行可展开看成分股 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title={`涨停板块热度 · 自己 SQL 算（${heatSql.length}）`} loading={loading} size="small">
            <Table<HeatSqlRow>
              rowKey="sector_code"
              dataSource={heatSql}
              pagination={false}
              size="small"
              expandable={{
                expandedRowRender: (r) => r.stocks?.length ? (
                  <Space size={[6, 4]} wrap>
                    {r.stocks.map(st => (
                      <Tag key={st.ts_code} color="blue">
                        {st.name || st.ts_code}{st.pct_chg != null ? ` ${st.pct_chg.toFixed(1)}%` : ''}
                      </Tag>
                    ))}
                  </Space>
                ) : <Text type="secondary">无成分股数据</Text>,
                rowExpandable: (r) => (r.stocks?.length ?? 0) > 0,
              }}
              columns={[
                { title: '板块代码', dataIndex: 'sector_code', width: 100 },
                { title: '名称', dataIndex: 'sector_name', ellipsis: true, render: v => <Tag color="blue">{v}</Tag> },
                { title: '涨停数', dataIndex: 'limit_up_count', width: 80 },
                { title: '最大连板', dataIndex: 'max_consecutive', width: 80 },
              ]}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title={`涨停板块热度 · 开盘啦（${heatKpl.length}）`} loading={loading} size="small"
                extra={<Text type="secondary" style={{ fontSize: 12 }}>点击行展开看个股</Text>}>
            <Table<HeatKplRow>
              rowKey="sector_code"
              dataSource={heatKpl}
              pagination={false}
              size="small"
              expandable={{
                expandedRowRender: (r) => r.stocks?.length ? (
                  <Space size={[6, 4]} wrap>
                    {r.stocks.map(st => (
                      <Tag key={st.ts_code} color={st.td_type === '2' ? 'red' : st.td_type === '0' ? 'volcano' : 'orange'}>
                        {st.name || st.ts_code}
                        {st.td_type === '2' ? ' 龙头' : ''}
                        {st.tips ? ` ${st.tips}` : ''}
                      </Tag>
                    ))}
                  </Space>
                ) : <Text type="secondary">该板块开盘啦未给成分股</Text>,
                rowExpandable: (r) => (r.stocks?.length ?? 0) > 0,
              }}
              columns={[
                { title: '板块代码', dataIndex: 'sector_code', width: 100 },
                { title: '名称', dataIndex: 'sector_name', ellipsis: true, render: v => <Tag color="orange">{v}</Tag> },
                { title: '涨停数', dataIndex: 'count', width: 80 },
              ]}
            />
          </Card>
        </Col>
      </Row>

      {/* 连板个股 + 炸板池 */}
      <Row gutter={16}>
        <Col span={12}>
          <Card title={`今日涨停个股 KPL（${consec.length}，含首板与连板，含题材）`} loading={loading} size="small" style={{ marginBottom: 16 }}>
            <Table<ConsecRow>
              rowKey="ts_code"
              dataSource={consec}
              pagination={{ pageSize: 20 }}
              size="small"
              columns={[
                { title: '代码', dataIndex: 'ts_code', width: 100 },
                { title: '简称', dataIndex: 'name', width: 80 },
                { title: '连板', dataIndex: 'days', width: 60,
                  render: v => v && v > 1 ? <Tag color="red">{v}连</Tag> : <Tag>首板</Tag>,
                  sorter: (a, b) => (b.days || 0) - (a.days || 0), defaultSortOrder: 'ascend' },
                { title: '描述', dataIndex: 'board_desc', width: 80 },
                { title: '题材', dataIndex: 'theme', ellipsis: true, render: v => v ? <Tag color="orange">{v}</Tag> : '-' },
                { title: '涨幅', dataIndex: 'pct_chg', width: 80, render: v => <PctCell value={v} /> },
              ]}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title={`炸板池（${broken.length}）`} loading={loading} size="small" style={{ marginBottom: 16 }}>
            <Table<BrokenRow>
              rowKey="ts_code"
              dataSource={broken}
              pagination={false}
              size="small"
              columns={[
                { title: '代码', dataIndex: 'ts_code', width: 100 },
                { title: '简称', dataIndex: 'name', width: 80 },
                { title: '题材', dataIndex: 'sector', ellipsis: true, render: v => v ? <Tag>{v}</Tag> : '-' },
                { title: '涨幅', dataIndex: 'pct_chg', width: 80, render: v => <PctCell value={v} /> },
              ]}
            />
          </Card>
        </Col>
      </Row>

      {/* 龙虎榜 + 席位下钻 */}
      <Card title={`龙虎榜（${lhb.length}）— 点击行展开看席位穿透`} loading={loading} size="small" style={{ marginBottom: 16 }}>
        <Table<LhbRow>
          rowKey="ts_code"
          dataSource={lhb}
          pagination={{ pageSize: 20 }}
          size="small"
          expandable={{
            onExpand: (expanded, record) => { if (expanded) loadSeats(record.ts_code); },
            expandedRowRender: (record) => {
              const rows = seats[record.ts_code];
              if (!rows) return <Text type="secondary">加载中...</Text>;
              if (rows.length === 0) return <Text type="secondary">无席位数据</Text>;
              return (
                <Table<SeatRow>
                  rowKey={(r) => `${r.trade_date}-${r.side}-${r.rank}-${r.broker}`}
                  dataSource={rows}
                  pagination={false}
                  size="small"
                  columns={[
                    { title: '日期', dataIndex: 'trade_date', width: 100 },
                    { title: '方向', dataIndex: 'side', width: 60, render: v => v === 'B' ? <Tag color="red">买</Tag> : <Tag color="green">卖</Tag> },
                    { title: '名次', dataIndex: 'rank', width: 60 },
                    { title: '席位', dataIndex: 'broker', ellipsis: true,
                      render: (v, r) => <span>{v}{r.is_dy ? <Tag color="purple" style={{ marginLeft: 4 }}>游资</Tag> : null}</span>,
                    },
                    { title: '买入', dataIndex: 'buy_in', width: 100, render: v => fmtYi(v) },
                    { title: '卖出', dataIndex: 'sell_out', width: 100, render: v => fmtYi(v) },
                    { title: '净买入', dataIndex: 'net_buy', width: 100, render: v => fmtYi(v) },
                  ]}
                />
              );
            },
          }}
          columns={[
            { title: '代码', dataIndex: 'ts_code', width: 100 },
            { title: '简称', dataIndex: 'name', width: 90 },
            { title: '涨幅', dataIndex: 'pct_chg', width: 80, render: v => <PctCell value={v} /> },
            { title: '上榜原因', dataIndex: 'reason', ellipsis: true },
            { title: '净买入', dataIndex: 'buy_in', width: 110, render: v => fmtYi(v) },
          ]}
        />
      </Card>

      {/* 竞价异动 */}
      <Card title={`竞价异动 / 尾盘抢筹（${auction.length}）`} loading={loading} size="small">
        <Table<AuctionRow>
          rowKey="ts_code"
          dataSource={auction}
          pagination={{ pageSize: 20 }}
          size="small"
          columns={[
            { title: '代码', dataIndex: 'ts_code', width: 100 },
            { title: '简称', dataIndex: 'name', width: 80 },
            { title: '标签', dataIndex: 'tag', width: 70, render: v => v ? <Tag color="gold">{v}</Tag> : '-' },
            { title: '题材', dataIndex: 'themes', ellipsis: true, render: v => v ? <Tag color="orange">{v}</Tag> : '-' },
            { title: '涨幅', dataIndex: 'pct_chg', width: 80, render: v => <PctCell value={v} /> },
            { title: '主力净买入', dataIndex: 'net_amount', width: 110, render: v => fmtYi(v) },
            { title: '大单净', dataIndex: 'big_order_buy', width: 100, render: (v, r) => fmtYi((v || 0) + (r.big_order_sell || 0)) },
            { title: '抢筹分', dataIndex: 'score', width: 80, render: v => v?.toFixed(2) },
          ]}
        />
      </Card>

      {/* 大幅回撤池 + 空间板梯队 */}
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title={`大幅回撤池（${withdrawal.length}）— 高位跳水`} loading={loading} size="small">
            <Table<WithdrawalRow>
              rowKey="ts_code"
              dataSource={withdrawal}
              pagination={false}
              size="small"
              columns={[
                { title: '代码', dataIndex: 'ts_code', width: 100 },
                { title: '简称', dataIndex: 'name', width: 100 },
                { title: '现价', dataIndex: 'price', width: 70 },
                { title: '当日', dataIndex: 'pct_chg', width: 80, render: v => <PctCell value={v} /> },
                { title: '回撤', dataIndex: 'withdrawal_pct', width: 80, render: v => <PctCell value={v} /> },
              ]}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title={`空间板梯队（${marketLadder.reduce((s, g) => s + g.stocks.length, 0)} 股）`} loading={loading} size="small">
            {marketLadder.map(g => (
              <div key={g.tip} style={{ marginBottom: 8 }}>
                <Tag color="purple">阶 {g.tip}</Tag>
                <Space size={[4, 4]} wrap style={{ marginLeft: 4 }}>
                  {g.stocks.map(st => (
                    <Tag key={st.ts_code} color={st.tips ? 'red' : 'orange'}>
                      {st.name || st.ts_code}{st.tips ? ` ${st.tips}` : ''}
                    </Tag>
                  ))}
                </Space>
              </div>
            ))}
            {marketLadder.length === 0 && <Text type="secondary">无数据</Text>}
          </Card>
        </Col>
      </Row>

      {/* 题材新闻流（核心：每条带关联个股 + 龙头标记） */}
      <Card title={`题材新闻流（${news.length}）— 每条新闻关联 N 只股，关键词自动加到该股的题材库`}
            loading={loading} size="small" style={{ marginTop: 16 }}>
        <Table<NewsItem>
          rowKey="news_id"
          dataSource={news}
          pagination={{ pageSize: 10 }}
          size="small"
          expandable={{
            expandedRowRender: (r) => r.stocks?.length ? (
              <Space size={[6, 4]} wrap>
                {r.stocks.map(st => (
                  <Tag key={st.ts_code} color={st.is_top ? 'red' : 'default'}>
                    {st.name || st.ts_code}
                    {st.is_top ? ' 龙头' : ''}
                    {st.pct_chg != null ? ` ${st.pct_chg.toFixed(1)}%` : ''}
                  </Tag>
                ))}
              </Space>
            ) : <Text type="secondary">无关联个股</Text>,
            rowExpandable: (r) => (r.stocks?.length ?? 0) > 0,
          }}
          columns={[
            { title: '时间', dataIndex: 'news_time', width: 140,
              render: v => v ? new Date(v).toLocaleString('zh-CN', { hour12: false }) : '-' },
            { title: '关键词', dataIndex: 'keyword', width: 110,
              render: v => v ? <Tag color="orange">{v}</Tag> : <Text type="secondary">-</Text> },
            { title: '标题', dataIndex: 'title', ellipsis: true },
            { title: '股数', width: 60, align: 'center',
              render: (_, r) => <Tag>{r.stocks?.length ?? 0}</Tag> },
          ]}
        />
      </Card>

      {/* 盘中题材异动事件流 + 历史强度曲线 */}
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title={`盘中题材异动事件流（${conception.length}）`} loading={loading} size="small">
            <Table<ConceptionEvent>
              rowKey={(r) => `${r.event_time}-${r.plate_text}`}
              dataSource={conception}
              pagination={false}
              size="small"
              scroll={{ y: 320 }}
              columns={[
                { title: '时间', dataIndex: 'event_time', width: 80,
                  render: v => new Date(v * 1000).toLocaleTimeString('zh-CN', { hour12: false }) },
                { title: '事件', dataIndex: 'plate_text', ellipsis: true },
                { title: '板块', dataIndex: 'plate_name', width: 80,
                  render: v => v ? <Tag color="blue">{v}</Tag> : '-' },
                { title: '涨跌', dataIndex: 'plate_zdf', width: 70,
                  render: v => v ? <PctCell value={parseFloat(v)} /> : '-' },
              ]}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title={`历史 30 日市场强度`} loading={loading} size="small">
            <Table<HistoryStrengthDay>
              rowKey="trade_date"
              dataSource={strength}
              pagination={false}
              size="small"
              scroll={{ y: 320 }}
              columns={[
                { title: '日期', dataIndex: 'trade_date', width: 100 },
                { title: '强度', dataIndex: 'strength', width: 70 },
                { title: '涨停', dataIndex: 'limit_up_count', width: 60 },
                { title: '最大连板', dataIndex: 'max_consecutive', width: 80 },
                { title: '跳水', dataIndex: 'big_drop_count', width: 60 },
              ]}
            />
          </Card>
        </Col>
      </Row>

      {/* === Phase 3: 实时快照（每天 15:00 入库） === */}
      <Card title={`竞价/收盘快照 (15:00 拍照)${dashboard?.trade_date ? ` · ${dashboard.trade_date}` : ''}`}
            loading={loading} size="small" style={{ marginTop: 16 }}>
        {dashboard?.board ? (
          <>
            <Row gutter={16} style={{ marginBottom: 12 }}>
              <Col span={6}>
                <Statistic title="今日涨停 / 昨日"
                  value={`${dashboard.board.today_zhang_ting || 0} / ${dashboard.board.last_zhang_ting || 0}`}
                  valueStyle={{ color: '#f5222d' }} />
              </Col>
              <Col span={6}>
                <Statistic title="今日跌停 / 昨日"
                  value={`${dashboard.board.today_die_ting || 0} / ${dashboard.board.last_die_ting || 0}`}
                  valueStyle={{ color: '#52c41a' }} />
              </Col>
              <Col span={6}>
                <Statistic title="今日封板率 / 昨日"
                  value={dashboard.board.today_feng_ban != null
                    ? `${dashboard.board.today_feng_ban.toFixed(2)}% / ${(dashboard.board.last_feng_ban_rate || 0).toFixed(2)}%`
                    : '-'} />
              </Col>
              <Col span={6}>
                <Statistic title="市场强度 intensity"
                  value={dashboard.board.intensity ?? '-'}
                  valueStyle={{ color: (dashboard.board.intensity ?? 0) >= 50 ? '#f5222d' : '#52c41a' }} />
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Title level={5}>风向标 · 最强涨停</Title>
                <Space size={[4, 4]} wrap>
                  {dashboard.tops.filter(t => t.direction === 'up').map(t => (
                    <Tag key={t.ts_code} color="red">
                      #{t.rank} {t.name}{t.pct_chg != null ? ` ${t.pct_chg.toFixed(2)}%` : ''} · {t.sector || '-'}
                    </Tag>
                  ))}
                </Space>
                <Title level={5} style={{ marginTop: 12 }}>最弱跌停</Title>
                <Space size={[4, 4]} wrap>
                  {dashboard.tops.filter(t => t.direction === 'down').map(t => (
                    <Tag key={t.ts_code} color="green">
                      #{t.rank} {t.name}{t.pct_chg != null ? ` ${t.pct_chg.toFixed(2)}%` : ''} · {t.sector || '-'}
                    </Tag>
                  ))}
                </Space>
              </Col>
              <Col span={12}>
                <Title level={5}>板块涨跌面</Title>
                <Space size={[4, 4]} wrap>
                  {dashboard.sectors.map(s => (
                    <Tag key={s.sector_code} color={(s.pct_chg ?? 0) > 0 ? 'red' : 'green'}>
                      {s.sector_name} {s.pct_chg != null ? `${s.pct_chg.toFixed(2)}%` : ''}
                    </Tag>
                  ))}
                </Space>
              </Col>
            </Row>
            {emotion && (
              <Row gutter={16} style={{ marginTop: 12 }}>
                <Col span={6}>
                  <Statistic title="量比 vs 昨日"
                    value={emotion.vol_ratio != null ? `${emotion.vol_ratio.toFixed(2)}%` : '-'}
                    valueStyle={{ color: (emotion.vol_ratio ?? 0) > 0 ? '#f5222d' : '#52c41a' }} />
                </Col>
                <Col span={6}>
                  <Statistic title="今日成交"
                    value={emotion.today_vol ? `${(emotion.today_vol / 1e8).toFixed(0)}亿` : '-'} />
                </Col>
              </Row>
            )}
          </>
        ) : <Text type="secondary">暂无快照数据（每天 15:00 自动入库）</Text>}
      </Card>

      {/* 长周期 + 游资动向 */}
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title={`长周期涨跌停趋势（${historyAnalysis.length} 日，含炸板率）`} loading={loading} size="small">
            <Table<HistoryAnalysisRow>
              rowKey="trade_date"
              dataSource={historyAnalysis}
              pagination={false}
              size="small"
              scroll={{ y: 320 }}
              columns={[
                { title: '日期', dataIndex: 'trade_date', width: 100 },
                { title: '涨停', dataIndex: 'limit_up', width: 60 },
                { title: '跌停', dataIndex: 'limit_down', width: 60 },
                { title: '曾涨停', dataIndex: 'broken', width: 70 },
                { title: '炸板', dataIndex: 'blown', width: 60 },
                { title: '炸板率', dataIndex: 'blown_rate', width: 80,
                  render: v => v != null ? `${v.toFixed(1)}%` : '-' },
              ]}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title={`游资动向 · 今日操盘明细（${youziTrades.length} 条 / ${youziTraders.length} 个游资）`}
                loading={loading} size="small">
            <Table<YouziTrade>
              rowKey={(r) => `${r.trader_id}-${r.side}-${r.ts_code}-${r.seat_name}`}
              dataSource={youziTrades}
              pagination={{ pageSize: 10 }}
              size="small"
              columns={[
                { title: '游资', dataIndex: 'trader_id', width: 80,
                  render: (v) => <Tag color="purple">{youziTraders.find(t => t.trader_id === v)?.name || v}</Tag> },
                { title: '方向', dataIndex: 'side', width: 50,
                  render: v => v === 'B' ? <Tag color="red">买</Tag> : <Tag color="green">卖</Tag> },
                { title: '股票', dataIndex: 'ts_code', width: 100 },
                { title: '席位', dataIndex: 'seat_name', ellipsis: true },
                { title: '净额', dataIndex: 'net_amount', width: 100, render: v => fmtYi(v) },
              ]}
            />
          </Card>
        </Col>
      </Row>

      {/* 编辑精选 */}
      <Card title={`编辑精选深度文章（${newsSelected.length}）`} loading={loading} size="small" style={{ marginTop: 16 }}>
        <Table<NewsSelectedRow>
          rowKey="article_id"
          dataSource={newsSelected}
          pagination={{ pageSize: 10 }}
          size="small"
          columns={[
            { title: '时间', dataIndex: 'create_time', width: 140,
              render: v => v ? new Date(v).toLocaleString('zh-CN', { hour12: false }) : '-' },
            { title: '账号', dataIndex: 'account', width: 120 },
            { title: '标题', dataIndex: 'title', ellipsis: true },
            { title: '关联', dataIndex: 'related', width: 200,
              render: (v) => {
                if (!v) return '-';
                try {
                  const arr = JSON.parse(v) as any[][];
                  return <Space size={[2, 2]} wrap>
                    {arr.slice(0, 3).map(([code, name]) => <Tag key={code}>{name}</Tag>)}
                  </Space>;
                } catch { return '-'; }
              },
            },
          ]}
        />
      </Card>
    </div>
  );
}
