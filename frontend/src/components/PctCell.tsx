export const UP_COLOR = '#f5222d';
export const DOWN_COLOR = '#52c41a';

export function PctCell({ value, withSign = true }: { value: number | null | undefined; withSign?: boolean }) {
  if (value == null || Number.isNaN(value)) return <>-</>;
  const color = value >= 0 ? UP_COLOR : DOWN_COLOR;
  const sign = withSign && value > 0 ? '+' : '';
  return <span style={{ color, fontWeight: 600 }}>{sign}{value.toFixed(2)}%</span>;
}

export function PriceDeltaCell({ value }: { value: number | null | undefined }) {
  if (value == null || Number.isNaN(value)) return <>-</>;
  const color = value >= 0 ? UP_COLOR : DOWN_COLOR;
  const sign = value > 0 ? '+' : '';
  return <span style={{ color, fontWeight: 600 }}>{sign}{value.toFixed(2)}</span>;
}

export const numSorter = (key: string) => (a: any, b: any) => {
  const av = a[key];
  const bv = b[key];
  if (av == null && bv == null) return 0;
  if (av == null) return -1;
  if (bv == null) return 1;
  return av - bv;
};

export const strSorter = (key: string) => (a: any, b: any) => {
  const av = a[key] ?? '';
  const bv = b[key] ?? '';
  return String(av).localeCompare(String(bv));
};
