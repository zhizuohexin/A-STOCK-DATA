import {
  Button,
  Card,
  DatePicker,
  Empty,
  Image,
  Input,
  Popconfirm,
  Space,
  Spin,
  Typography,
  Upload,
  message,
} from 'antd';
import type { UploadFile } from 'antd';
import { DeleteOutlined, FileImageOutlined, ScanOutlined, UploadOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import dayjs, { type Dayjs } from 'dayjs';
import { api, type JournalCategory, type JournalEntry } from '../api/client';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;

type Props = {
  category: JournalCategory;
  title: string;
  placeholder?: string;
};

export default function JournalPage({ category, title, placeholder }: Props) {
  const [entryDate, setEntryDate] = useState<Dayjs>(dayjs());
  const [content, setContent] = useState('');
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [ocrLoading, setOcrLoading] = useState(false);

  const [queryDate, setQueryDate] = useState<Dayjs | null>(dayjs());
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [listLoading, setListLoading] = useState(false);

  const load = async () => {
    setListLoading(true);
    try {
      const params: Record<string, string> = {};
      if (queryDate) params.date = queryDate.format('YYYY-MM-DD');
      const r = await api.get<JournalEntry[]>(`/journal/${category}`, { params });
      setEntries(r.data);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '加载失败');
    } finally {
      setListLoading(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [category, queryDate]);

  const runOcr = async () => {
    const imgs = files.filter((f) => f.originFileObj);
    if (imgs.length === 0) {
      message.warning('请先选择图片');
      return;
    }
    setOcrLoading(true);
    try {
      const texts: string[] = [];
      for (const f of imgs) {
        const fd = new FormData();
        fd.append('file', f.originFileObj as File);
        const r = await api.post<{ text: string }>('/ocr', fd);
        if (r.data.text) texts.push(r.data.text);
      }
      const extracted = texts.join('\n---\n');
      if (!extracted) {
        message.info('未识别出文字');
      } else {
        setContent((prev) => (prev ? `${prev}\n${extracted}` : extracted));
        message.success('已填入文本框，可编辑后提交');
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'OCR 失败');
    } finally {
      setOcrLoading(false);
    }
  };

  const submit = async () => {
    if (!content.trim() && files.length === 0) {
      message.warning('内容或图片至少填一项');
      return;
    }
    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append('entry_date', entryDate.format('YYYY-MM-DD'));
      fd.append('content', content);
      files.forEach((f) => {
        if (f.originFileObj) fd.append('images', f.originFileObj as File);
      });
      await api.post<JournalEntry>(`/journal/${category}`, fd);
      message.success('已保存');
      setContent('');
      setFiles([]);
      if (queryDate && queryDate.isSame(entryDate, 'day')) {
        load();
      } else {
        setQueryDate(entryDate);
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败');
    } finally {
      setSubmitting(false);
    }
  };

  const remove = async (id: number) => {
    try {
      await api.delete(`/journal/${category}/${id}`);
      message.success('已删除');
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '删除失败');
    }
  };

  return (
    <div>
      <Title level={3}>{title}</Title>

      <Card size="small" style={{ marginBottom: 16 }} title="新建记录">
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <Space wrap>
            <span>日期：</span>
            <DatePicker value={entryDate} onChange={(v) => v && setEntryDate(v)} allowClear={false} />
          </Space>
          <TextArea
            rows={6}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder={placeholder || '可直接输入，或上传图片后点"OCR 提取文字"，自动填入后再编辑'}
          />
          <Upload
            multiple
            listType="picture-card"
            fileList={files}
            beforeUpload={() => false}
            onChange={({ fileList }) => setFiles(fileList)}
            onPreview={(f) => {
              if (f.originFileObj) {
                window.open(URL.createObjectURL(f.originFileObj as File));
              } else if (f.url) {
                window.open(f.url);
              }
            }}
            accept="image/*"
          >
            {files.length >= 9 ? null : (
              <div>
                <UploadOutlined />
                <div style={{ marginTop: 4 }}>选择图片</div>
              </div>
            )}
          </Upload>
          <Space>
            <Button
              icon={<ScanOutlined />}
              loading={ocrLoading}
              disabled={files.length === 0}
              onClick={runOcr}
            >
              OCR 提取文字
            </Button>
            <Button type="primary" loading={submitting} onClick={submit}>
              保存
            </Button>
          </Space>
        </Space>
      </Card>

      <Card
        size="small"
        title={
          <Space>
            <span>历史记录</span>
            <DatePicker
              value={queryDate}
              onChange={setQueryDate}
              placeholder="筛选日期（清空看最近）"
            />
            <Button size="small" onClick={load}>刷新</Button>
          </Space>
        }
      >
        <Spin spinning={listLoading}>
          {entries.length === 0 ? (
            <Empty description="暂无记录" />
          ) : (
            <Space direction="vertical" style={{ width: '100%' }} size={12}>
              {entries.map((e) => (
                <Card
                  key={e.id}
                  size="small"
                  type="inner"
                  title={
                    <Space>
                      <Text strong>{e.entry_date}</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {dayjs(e.created_at).format('HH:mm')}
                      </Text>
                    </Space>
                  }
                  extra={
                    <Popconfirm title="确认删除？" onConfirm={() => remove(e.id)}>
                      <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
                    </Popconfirm>
                  }
                >
                  {e.content && (
                    <Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: e.images.length ? 12 : 0 }}>
                      {e.content}
                    </Paragraph>
                  )}
                  {e.images.length > 0 && (
                    <Image.PreviewGroup>
                      <Space wrap>
                        {e.images.map((src) => (
                          <Image
                            key={src}
                            src={src}
                            width={120}
                            height={120}
                            style={{ objectFit: 'cover', borderRadius: 4 }}
                            fallback="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><rect width='100%' height='100%' fill='%23eee'/></svg>"
                            placeholder={<FileImageOutlined style={{ fontSize: 32, color: '#bbb' }} />}
                          />
                        ))}
                      </Space>
                    </Image.PreviewGroup>
                  )}
                </Card>
              ))}
            </Space>
          )}
        </Spin>
      </Card>
    </div>
  );
}
