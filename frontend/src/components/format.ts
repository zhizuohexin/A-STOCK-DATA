/**
 * 单位说明（provider 返回的原始单位）:
 * - Tushare daily.amount: 千元      → fromUnit='qianyuan'
 * - Tushare daily.vol: 手           → fromUnit='shou'
 * - Eastmoney / 其它 amount: 元     → fromUnit='yuan'
 * - 所有 vol: 手                   → fromUnit='shou'
 */
export type YiFromUnit = 'yuan' | 'qianyuan' | 'shou';

function toYi(value: number, from: YiFromUnit): number {
  switch (from) {
    case 'yuan': return value / 1e8;
    case 'qianyuan': return value / 1e5;
    case 'shou': return value / 1e8;
  }
}

export function formatYi(
  value: number | null | undefined,
  from: YiFromUnit = 'yuan',
  label: string = '亿',
): string {
  if (value == null || Number.isNaN(value)) return '-';
  const yi = toYi(value, from);
  if (Math.abs(yi) < 0.01 && yi !== 0) return `<0.01${label}`;
  return `${yi.toFixed(2)}${label}`;
}

export const formatYiYuan = (v: number | null | undefined, from: YiFromUnit = 'yuan') =>
  formatYi(v, from, '亿');

export const formatYiShou = (v: number | null | undefined) => formatYi(v, 'shou', '亿手');
