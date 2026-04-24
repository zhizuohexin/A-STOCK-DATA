import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 30000,
});

export type Stock = {
  ts_code: string;
  symbol: string;
  name: string;
  area?: string;
  industry?: string;
  market?: string;
  list_date?: string;
};

export type DailyQuote = {
  ts_code: string;
  trade_date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  pre_close: number | null;
  change: number | null;
  pct_chg: number | null;
  vol: number | null;
  amount: number | null;
  turnover_rate: number | null;
};

export type LimitUp = {
  ts_code: string;
  trade_date: string;
  name: string | null;
  close: number | null;
  pct_chg: number | null;
  amount: number | null;
  fd_amount: number | null;
  first_time: string | null;
  last_time: string | null;
  open_times: number | null;
  limit_times: number | null;
};

export type Sector = { ts_code: string; name: string; type: string };

export type SectorDaily = {
  sector_code: string;
  trade_date: string;
  name: string | null;
  close: number | null;
  pct_chg: number | null;
  vol: number | null;
  amount: number | null;
};

export type IntradayBar = {
  ts_code: string;
  bar_time: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  vol: number | null;
  amount: number | null;
};

export type JobRun = {
  id: number;
  job_name: string;
  status: string;
  message: string | null;
  rows_affected: number | null;
  started_at: string;
  finished_at: string | null;
};

export type RankingResponse<T> = {
  days?: number;
  top: number;
  end_date?: string;
  trade_date?: string;
  items: T[];
};

export type GainerItem = {
  ts_code: string;
  name: string | null;
  industry: string | null;
  base_date: string;
  end_date: string;
  base_close: number;
  end_close: number;
  pct_chg: number;
};

export type SectorGainerItem = {
  sector_code: string;
  name: string | null;
  close: number | null;
  pct_chg: number | null;
  vol: number | null;
  amount: number | null;
  type: string | null;
};
