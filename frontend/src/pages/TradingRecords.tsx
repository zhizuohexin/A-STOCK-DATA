import JournalPage from './JournalPage';

export default function TradingRecords() {
  return (
    <JournalPage
      category="trading"
      title="我的交易记录"
      placeholder="记录今日买卖操作、持仓变化、止盈止损；可以上传交割单/截图，OCR 提取后再编辑"
    />
  );
}
