import { ReactNode, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowRightLeft,
  FileArchive,
  FileImage,
  FileOutput,
  FileStack,
  Moon,
  Sparkles,
  Sun,
} from 'lucide-react';
import { FileDropzone } from './components/FileDropzone';
import { ImageCompressionStudio } from './components/ImageCompressionStudio';
import { ResultPanel } from './components/ResultPanel';
import { downloadBlob, formatBytes, getFilenameFromHeaders, postForm } from './lib/api';

type ToolKey =
  | 'image-convert'
  | 'image-resize'
  | 'image-compress'
  | 'image-pdf'
  | 'pdf-merge'
  | 'pdf-images'
  | 'pdf-compress'
  | 'pdf-utils';

type ToolItem = {
  key: ToolKey;
  title: string;
  description: string;
  icon: ReactNode;
  section: 'Images' | 'PDF';
};

const tools: ToolItem[] = [
  { key: 'image-convert', title: 'Image Converter', description: 'Convert common formats in batch.', icon: <ArrowRightLeft size={16} />, section: 'Images' },
  { key: 'image-resize', title: 'Image Resize', description: 'Resize with aspect-ratio protection.', icon: <FileImage size={16} />, section: 'Images' },
  { key: 'image-compress', title: 'Image Compression', description: 'Preview-first image compression with compare slider.', icon: <FileArchive size={16} />, section: 'Images' },
  { key: 'image-pdf', title: 'Images to PDF', description: 'Create PDFs from a visible, reorderable image queue.', icon: <FileStack size={16} />, section: 'PDF' },
  { key: 'pdf-merge', title: 'Merge PDFs', description: 'Combine multiple PDFs in your chosen drag-and-drop order.', icon: <FileStack size={16} />, section: 'PDF' },
  { key: 'pdf-images', title: 'PDF to Images', description: 'Export high-DPI pages as image files.', icon: <FileImage size={16} />, section: 'PDF' },
  { key: 'pdf-compress', title: 'PDF Compression', description: 'Best-effort target compression with honest reporting.', icon: <FileArchive size={16} />, section: 'PDF' },
  { key: 'pdf-utils', title: 'PDF Utilities', description: 'Merge, split, extract, rotate, delete, and reorder.', icon: <FileOutput size={16} />, section: 'PDF' },
];

function ToolButton({
  active,
  item,
  onClick,
}: {
  active: boolean;
  item: ToolItem;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-2xl px-3 py-3 text-left transition ${
        active
          ? 'bg-brand-600 text-white shadow-lg'
          : 'border border-slate-200 bg-white/70 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900/70 dark:hover:bg-slate-800'
      }`}
    >
      <div className="flex items-center gap-2 font-semibold">
        {item.icon}
        {item.title}
      </div>
      <p className={`mt-1 text-xs ${active ? 'text-white/80' : 'text-slate-500 dark:text-slate-400'}`}>{item.description}</p>
    </button>
  );
}

export default function App() {
  const [tool, setTool] = useState<ToolKey>('image-compress');
  const [dark, setDark] = useState(false);
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [pdfFiles, setPdfFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ message: string; error?: string; beforeSize?: string; afterSize?: string } | null>(null);

  const [outputFormat, setOutputFormat] = useState('png');
  const [bgColor, setBgColor] = useState('#ffffff');

  const [resizeWidth, setResizeWidth] = useState(1200);
  const [resizeHeight, setResizeHeight] = useState(1200);
  const [keepAspectRatio, setKeepAspectRatio] = useState(false);

  const [pageSize, setPageSize] = useState('original');
  const [fitPage, setFitPage] = useState(true);

  const [pdfImageFormat, setPdfImageFormat] = useState('png');
  const [dpi, setDpi] = useState(300);
  const [pageRange, setPageRange] = useState('');

  const [pdfCompressMode, setPdfCompressMode] = useState('quality_first');
  const [pdfTargetReduction, setPdfTargetReduction] = useState('');
  const [pdfForceReduce, setPdfForceReduce] = useState(false);

  const [pdfUtilityAction, setPdfUtilityAction] = useState('split');
  const [utilityValue, setUtilityValue] = useState('1-2');
  const [rotateDegrees, setRotateDegrees] = useState(90);

  const groupedTools = useMemo(
    () => ({
      Images: tools.filter((item) => item.section === 'Images'),
      PDF: tools.filter((item) => item.section === 'PDF'),
    }),
    []
  );

  const resetWorkspace = (nextTool: ToolKey) => {
    setTool(nextTool);
    setImageFiles([]);
    setPdfFiles([]);
    setResult(null);
  };

  const runDownload = async (endpoint: string, form: FormData, filename: string, sourceFiles: File[]) => {
    setBusy(true);
    setResult(null);
    try {
      const response = await postForm(endpoint, form);
      downloadBlob(response.blob, getFilenameFromHeaders(response.headers) ?? filename);
      const before = sourceFiles.reduce((sum, file) => sum + file.size, 0);
      setResult({
        message: 'Done. File ready for download.',
        beforeSize: formatBytes(response.compressionMeta?.originalSize ?? before),
        afterSize: formatBytes(response.compressionMeta?.outputSize ?? response.blob.size),
      });
    } catch (error) {
      setResult({ message: '', error: error instanceof Error ? error.message : 'Unexpected error' });
    } finally {
      setBusy(false);
    }
  };

  const renderPanel = () => {
    if (tool === 'image-convert') {
      return (
        <>
          <FileDropzone files={imageFiles} setFiles={setImageFiles} accept="image/*" />
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-medium">Output format
              <select className="mt-1 w-full rounded-xl border border-slate-300 bg-transparent p-2 text-slate-900 dark:border-slate-700 dark:text-slate-100" value={outputFormat} onChange={(e) => setOutputFormat(e.target.value)}>
                <option>png</option><option>jpeg</option><option>webp</option><option>bmp</option><option>tiff</option>
              </select>
            </label>
            <label className="text-sm font-medium">JPEG background fill
              <input type="color" className="mt-1 h-10 w-full rounded-xl border border-slate-300 p-1 dark:border-slate-700" value={bgColor} onChange={(e) => setBgColor(e.target.value)} />
            </label>
          </div>
          <button type="button" disabled={busy || imageFiles.length === 0} className="rounded-xl bg-brand-600 px-4 py-2 text-white disabled:opacity-40" onClick={async () => {
            const form = new FormData();
            imageFiles.forEach((file) => form.append('files', file));
            form.append('output_format', outputFormat);
            form.append('background_color', bgColor);
            await runDownload('/api/images/convert', form, imageFiles.length > 1 ? 'converted_images.zip' : `converted.${outputFormat}`, imageFiles);
          }}>
            Convert Images
          </button>
        </>
      );
    }

    if (tool === 'image-resize') {
      return (
        <>
          <FileDropzone files={imageFiles} setFiles={setImageFiles} accept="image/*" />
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="text-sm font-medium">Width (px)
              <input className="mt-1 w-full rounded-xl border border-slate-300 bg-transparent p-2 text-slate-900 dark:border-slate-700 dark:text-slate-100" type="number" min={1} value={resizeWidth} onChange={(e) => setResizeWidth(Number(e.target.value || 1))} />
            </label>
            <label className="text-sm font-medium">Height (px)
              <input className="mt-1 w-full rounded-xl border border-slate-300 bg-transparent p-2 text-slate-900 dark:border-slate-700 dark:text-slate-100" type="number" min={1} value={resizeHeight} onChange={(e) => setResizeHeight(Number(e.target.value || 1))} />
            </label>
            <label className="mt-7 inline-flex items-center gap-2 text-sm">
              <input type="checkbox" checked={keepAspectRatio} onChange={(e) => setKeepAspectRatio(e.target.checked)} /> Keep aspect ratio and fit inside target box
            </label>
          </div>
          <button type="button" disabled={busy || imageFiles.length === 0} className="rounded-xl bg-brand-600 px-4 py-2 text-white disabled:opacity-40" onClick={async () => {
            const form = new FormData();
            imageFiles.forEach((file) => form.append('files', file));
            form.append('width', String(resizeWidth));
            form.append('height', String(resizeHeight));
            form.append('keep_aspect_ratio', String(keepAspectRatio));
            await runDownload('/api/images/resize', form, imageFiles.length > 1 ? 'resized_images.zip' : imageFiles[0].name, imageFiles);
          }}>
            Resize Images
          </button>
        </>
      );
    }

    if (tool === 'image-compress') {
      return <ImageCompressionStudio busy={busy} setBusy={setBusy} />;
    }

    if (tool === 'image-pdf') {
      return (
        <>
          <FileDropzone files={imageFiles} setFiles={setImageFiles} accept="image/*" />
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-medium">Page size
              <select className="mt-1 w-full rounded-xl border border-slate-300 bg-transparent p-2 text-slate-900 dark:border-slate-700 dark:text-slate-100" value={pageSize} onChange={(e) => setPageSize(e.target.value)}>
                <option value="original">Original</option>
                <option value="a4">A4</option>
                <option value="letter">Letter</option>
              </select>
            </label>
            <label className="mt-7 inline-flex items-center gap-2 text-sm">
              <input type="checkbox" checked={fitPage} onChange={(e) => setFitPage(e.target.checked)} /> Fit to page
            </label>
          </div>
          <button type="button" disabled={busy || imageFiles.length === 0} className="rounded-xl bg-brand-600 px-4 py-2 text-white disabled:opacity-40" onClick={async () => {
            const form = new FormData();
            imageFiles.forEach((file) => form.append('files', file));
            form.append('page_size', pageSize);
            form.append('fit_to_page', String(fitPage));
            form.append('filename', 'images.pdf');
            await runDownload('/api/images/to-pdf', form, 'images.pdf', imageFiles);
          }}>
            Create PDF
          </button>
        </>
      );
    }

    if (tool === 'pdf-images') {
      return (
        <>
          <FileDropzone files={pdfFiles} setFiles={setPdfFiles} accept="application/pdf" multiple={false} />
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="text-sm font-medium">Format
              <select className="mt-1 w-full rounded-xl border border-slate-300 bg-transparent p-2 text-slate-900 dark:border-slate-700 dark:text-slate-100" value={pdfImageFormat} onChange={(e) => setPdfImageFormat(e.target.value)}>
                <option>png</option><option>jpeg</option><option>webp</option>
              </select>
            </label>
            <label className="text-sm font-medium">DPI
              <select className="mt-1 w-full rounded-xl border border-slate-300 bg-transparent p-2 text-slate-900 dark:border-slate-700 dark:text-slate-100" value={dpi} onChange={(e) => setDpi(Number(e.target.value))}>
                <option value={150}>150</option><option value={200}>200</option><option value={300}>300</option><option value={600}>600</option>
              </select>
            </label>
            <label className="text-sm font-medium">Page range
              <input className="mt-1 w-full rounded-xl border border-slate-300 bg-transparent p-2 text-slate-900 placeholder:text-slate-400 dark:border-slate-700 dark:text-slate-100 dark:placeholder:text-slate-500" value={pageRange} onChange={(e) => setPageRange(e.target.value)} placeholder="1-3,6" />
            </label>
          </div>
          <button type="button" disabled={busy || pdfFiles.length === 0} className="rounded-xl bg-brand-600 px-4 py-2 text-white disabled:opacity-40" onClick={async () => {
            const form = new FormData();
            form.append('file', pdfFiles[0]);
            form.append('format', pdfImageFormat);
            form.append('dpi', String(dpi));
            if (pageRange) form.append('page_range', pageRange);
            await runDownload('/api/pdf/to-images', form, 'pdf_images.zip', pdfFiles);
          }}>
            Export Images
          </button>
        </>
      );
    }

    if (tool === 'pdf-merge') {
      return (
        <>
          <FileDropzone files={pdfFiles} setFiles={setPdfFiles} accept="application/pdf" multiple />
          <div className="rounded-2xl border border-slate-200 bg-white/80 p-4 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900/80 dark:text-slate-300">
            Upload multiple PDFs, then drag the cards to arrange the final merge order. The merged file follows the visible top-to-bottom sequence.
          </div>
          <button type="button" disabled={busy || pdfFiles.length < 2} className="rounded-xl bg-brand-600 px-4 py-2 text-white disabled:opacity-40" onClick={async () => {
            const form = new FormData();
            pdfFiles.forEach((file) => form.append('files', file));
            await runDownload('/api/pdf/merge', form, 'merged.pdf', pdfFiles);
          }}>
            Merge PDFs
          </button>
        </>
      );
    }

    if (tool === 'pdf-compress') {
      return (
        <>
          <FileDropzone files={pdfFiles} setFiles={setPdfFiles} accept="application/pdf" multiple={false} />
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="text-sm font-medium">Mode
              <select className="mt-1 w-full rounded-xl border border-slate-300 bg-transparent p-2 text-slate-900 dark:border-slate-700 dark:text-slate-100" value={pdfCompressMode} onChange={(e) => setPdfCompressMode(e.target.value)}>
                <option value="quality_first">Quality-first</option>
                <option value="light">Light compression</option>
                <option value="balanced">Balanced compression</option>
                <option value="strong">Strong compression</option>
              </select>
            </label>
            <label className="text-sm font-medium">Target reduction %
              <input className="mt-1 w-full rounded-xl border border-slate-300 bg-transparent p-2 text-slate-900 placeholder:text-slate-400 dark:border-slate-700 dark:text-slate-100 dark:placeholder:text-slate-500" type="number" min={1} max={90} value={pdfTargetReduction} onChange={(e) => setPdfTargetReduction(e.target.value)} placeholder="20" />
            </label>
            <label className="mt-7 inline-flex items-center gap-2 text-sm">
              <input type="checkbox" checked={pdfForceReduce} onChange={(e) => setPdfForceReduce(e.target.checked)} /> Force reduce size
            </label>
          </div>
          <button type="button" disabled={busy || pdfFiles.length === 0} className="rounded-xl bg-brand-600 px-4 py-2 text-white disabled:opacity-40" onClick={async () => {
            const form = new FormData();
            form.append('file', pdfFiles[0]);
            form.append('mode', pdfCompressMode);
            form.append('force_reduce_size', String(pdfForceReduce));
            if (pdfTargetReduction) form.append('target_reduction_percent', pdfTargetReduction);
            await runDownload('/api/pdf/compress', form, 'compressed.pdf', pdfFiles);
          }}>
            Compress PDF
          </button>
        </>
      );
    }

    return (
      <>
        <FileDropzone files={pdfFiles} setFiles={setPdfFiles} accept="application/pdf" multiple={false} />
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="text-sm font-medium">Action
            <select className="mt-1 w-full rounded-xl border border-slate-300 bg-transparent p-2 text-slate-900 dark:border-slate-700 dark:text-slate-100" value={pdfUtilityAction} onChange={(e) => setPdfUtilityAction(e.target.value)}>
              <option value="split">Split by ranges</option>
              <option value="extract">Extract pages</option>
              <option value="rotate">Rotate pages</option>
              <option value="delete">Delete pages</option>
              <option value="reorder">Reorder pages</option>
            </select>
          </label>
          <label className="text-sm font-medium">Input
            <input className="mt-1 w-full rounded-xl border border-slate-300 bg-transparent p-2 text-slate-900 placeholder:text-slate-400 dark:border-slate-700 dark:text-slate-100 dark:placeholder:text-slate-500" value={utilityValue} onChange={(e) => setUtilityValue(e.target.value)} placeholder={pdfUtilityAction === 'reorder' ? '3,1,2' : '1-3,6'} />
          </label>
          {pdfUtilityAction === 'rotate' && (
            <label className="text-sm font-medium">Rotation
              <select className="mt-1 w-full rounded-xl border border-slate-300 bg-transparent p-2 text-slate-900 dark:border-slate-700 dark:text-slate-100" value={rotateDegrees} onChange={(e) => setRotateDegrees(Number(e.target.value))}>
                <option value={90}>90</option><option value={180}>180</option><option value={270}>270</option>
              </select>
            </label>
          )}
        </div>
        <button type="button" disabled={busy || pdfFiles.length === 0} className="rounded-xl bg-brand-600 px-4 py-2 text-white disabled:opacity-40" onClick={async () => {
          const form = new FormData();
          form.append('file', pdfFiles[0]);
          if (pdfUtilityAction === 'split') form.append('ranges', utilityValue);
          if (pdfUtilityAction === 'extract') form.append('pages', utilityValue);
          if (pdfUtilityAction === 'delete') form.append('pages', utilityValue);
          if (pdfUtilityAction === 'reorder') form.append('order', utilityValue);
          if (pdfUtilityAction === 'rotate') {
            form.append('pages', utilityValue);
            form.append('degrees', String(rotateDegrees));
          }
          const endpoint = `/api/pdf/${pdfUtilityAction}`;
          const filename = pdfUtilityAction === 'split' ? 'split_pdf.zip' : `${pdfUtilityAction}.pdf`;
          await runDownload(endpoint, form, filename, pdfFiles);
        }}>
          Run PDF Utility
        </button>
      </>
    );
  };

  return (
    <div className={dark ? 'dark' : ''}>
      <div className="min-h-screen bg-[radial-gradient(circle_at_10%_0%,rgba(14,165,233,0.22),transparent_32%),radial-gradient(circle_at_92%_0%,rgba(249,115,22,0.18),transparent_28%),linear-gradient(180deg,#f5f7fb_0%,#eef4ff_100%)] text-slate-900 dark:bg-[radial-gradient(circle_at_10%_0%,rgba(14,165,233,0.2),transparent_32%),radial-gradient(circle_at_92%_0%,rgba(34,197,94,0.12),transparent_28%),linear-gradient(180deg,#020617_0%,#111827_100%)] dark:text-slate-100">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <header className="mb-6 flex items-center justify-between rounded-3xl border border-white/50 bg-white/75 p-5 shadow-xl backdrop-blur dark:border-slate-700 dark:bg-slate-900/75">
            <div>
              <p className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-200">
                <Sparkles size={12} /> Private local processing
              </p>
              <h1 className="mt-3 font-display text-3xl">Doc Conversion Toolkit</h1>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Preview-first document and image processing with local-only workflows.</p>
            </div>
            <button type="button" onClick={() => setDark((value) => !value)} className="rounded-xl border border-slate-300 bg-white/80 p-2 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100">
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </header>

          <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
            <aside className="rounded-3xl border border-white/50 bg-white/75 p-3 shadow-xl backdrop-blur dark:border-slate-700 dark:bg-slate-900/75">
              {(['Images', 'PDF'] as const).map((section) => (
                <div key={section} className="mb-4">
                  <p className="px-2 pb-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">{section}</p>
                  <div className="space-y-2">
                    {groupedTools[section].map((item) => (
                      <ToolButton key={item.key} active={tool === item.key} item={item} onClick={() => resetWorkspace(item.key)} />
                    ))}
                  </div>
                </div>
              ))}
            </aside>

            <motion.main initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="rounded-3xl border border-white/50 bg-white/80 p-6 text-slate-900 shadow-xl backdrop-blur dark:border-slate-700 dark:bg-slate-900/80 dark:text-slate-100">
              <div className="space-y-5">{renderPanel()}</div>
              {busy && <p className="mt-4 text-sm text-brand-700 dark:text-brand-300">Processing locally...</p>}
              {result && <div className="mt-4"><ResultPanel {...result} /></div>}
            </motion.main>
          </div>

          <footer className="mt-6 rounded-3xl border border-white/50 bg-white/70 px-5 py-4 text-sm text-slate-600 shadow-xl backdrop-blur dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-300">
            Developed by: <span className="font-semibold text-slate-900 dark:text-slate-100">Akshay Shah</span>{' '}
            (<a className="text-brand-700 underline-offset-2 hover:underline dark:text-brand-300" href="mailto:akshayshah.ce@gmail.com">Akshayshah.ce@gmail.com</a>)
          </footer>
        </div>
      </div>
    </div>
  );
}
