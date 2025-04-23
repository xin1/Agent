import React, { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { ArrowDownToLine } from 'lucide-react';

export default function PDFCropper() {
  const [topCm, setTopCm] = useState('2');
  const [bottomCm, setBottomCm] = useState('2');
  const [file, setFile] = useState(null);
  const [downloading, setDownloading] = useState(false);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleSubmit = async () => {
    if (!file) return;
    setDownloading(true);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('top_cm', topCm);
    formData.append('bottom_cm', bottomCm);

    try {
      const response = await fetch('/api/process-pdf', {
        method: 'POST',
        body: formData,
      });

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'processed_output.zip';
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      console.error('处理出错:', err);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto p-4">
      <Card>
        <CardContent className="space-y-4 p-4">
          <h2 className="text-xl font-bold">PDF 剪裁与结构提取工具</h2>

          <div className="space-y-2">
            <Label htmlFor="top-cm">页眉删除高度（cm）</Label>
            <Input id="top-cm" value={topCm} onChange={e => setTopCm(e.target.value)} />

            <Label htmlFor="bottom-cm">页脚删除高度（cm）</Label>
            <Input id="bottom-cm" value={bottomCm} onChange={e => setBottomCm(e.target.value)} />

            <Label htmlFor="file">上传 PDF 文件</Label>
            <Input id="file" type="file" accept="application/pdf" onChange={handleFileChange} />
          </div>

          <Button onClick={handleSubmit} disabled={downloading} className="w-full mt-4">
            <ArrowDownToLine className="mr-2" />
            {downloading ? '处理中...' : '开始处理并下载结果'}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
