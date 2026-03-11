import JSZip from 'jszip';
import { Download, Trash2 } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { downloadBlob, formatBytes, postForm, type CompressionMeta } from '../lib/api';
import { BeforeAfterCompare } from './BeforeAfterCompare';
import { FileDropzone } from './FileDropzone';
import { ResultPanel } from './ResultPanel';

type Props = {
  busy: boolean;
  setBusy: (value: boolean) => void;
};

type CompressionResult = {
  blob: Blob;
  url: string;
  meta: CompressionMeta | null;
};

type EditorSettings = {
  quality: number;
  colors: number;
  precision: number;
};

const defaultSettings: EditorSettings = {
  quality: 80,
  colors: 256,
  precision: 2,
};

function extOf(file: File): string {
  return file.name.split('.').pop()?.toLowerCase() ?? '';
}

function supportsQuality(ext: string): boolean {
  return ext === 'jpg' || ext === 'jpeg' || ext === 'webp';
}

function supportsColors(ext: string): boolean {
  return ext === 'png' || ext === 'gif';
}

function supportsPrecision(ext: string): boolean {
  return ext === 'svg';
}

export function ImageCompressionStudio({ busy, setBusy }: Props) {
  const [files, setFiles] = useState<File[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [settings, setSettings] = useState<Record<string, EditorSettings>>({});
  const [results, setResults] = useState<Record<string, CompressionResult>>({});
  const [status, setStatus] = useState<{ message: string; error?: string; beforeSize?: string; afterSize?: string } | null>(null);
  const previewTimerRef = useRef<number | null>(null);
  const [selectedOriginalUrl, setSelectedOriginalUrl] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      Object.values(results).forEach((result) => URL.revokeObjectURL(result.url));
    };
  }, [results]);

  useEffect(() => {
    if (files.length === 0) {
      setSelectedIndex(0);
      setSettings({});
      setResults({});
      setStatus(null);
      return;
    }
    setSelectedIndex((current) => Math.min(current, files.length - 1));
    setSettings((current) => {
      const next = { ...current };
      for (const file of files) {
        if (!next[file.name]) next[file.name] = { ...defaultSettings };
      }
      for (const key of Object.keys(next)) {
        if (!files.find((file) => file.name === key)) delete next[key];
      }
      return next;
    });
    setResults((current) => {
      const next = { ...current };
      for (const key of Object.keys(next)) {
        if (!files.find((file) => file.name === key)) {
          URL.revokeObjectURL(next[key].url);
          delete next[key];
        }
      }
      return next;
    });
  }, [files]);

  const selectedFile = files[selectedIndex] ?? null;
  const selectedExt = selectedFile ? extOf(selectedFile) : '';
  const selectedSettings = selectedFile ? settings[selectedFile.name] ?? defaultSettings : defaultSettings;
  const selectedResult = selectedFile ? results[selectedFile.name] ?? null : null;

  useEffect(() => {
    if (!selectedFile) {
      setSelectedOriginalUrl(null);
      return;
    }
    const url = URL.createObjectURL(selectedFile);
    setSelectedOriginalUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [selectedFile]);

  const beforeTotal = useMemo(() => files.reduce((sum, file) => sum + file.size, 0), [files]);
  const afterTotal = useMemo(
    () =>
      files.reduce((sum, file) => {
        const result = results[file.name];
        return sum + (result?.meta?.outputSize ?? file.size);
      }, 0),
    [files, results]
  );

  const applyPreview = async (file: File) => {
    const ext = extOf(file);
    const fileSettings = settings[file.name] ?? defaultSettings;
    const form = new FormData();
    form.append('file', file);
    form.append('compression_level', supportsPrecision(ext) ? '0' : String(Math.max(0, Math.min(99, 100 - fileSettings.quality))));
    if (supportsQuality(ext)) form.append('quality', String(fileSettings.quality));
    if (supportsColors(ext)) form.append('colors', String(fileSettings.colors));
    if (supportsPrecision(ext)) form.append('precision', String(fileSettings.precision));

    const response = await postForm('/api/images/compress-preview', form);
    setResults((current) => {
      const existing = current[file.name];
      if (existing) URL.revokeObjectURL(existing.url);
      return {
        ...current,
        [file.name]: {
          blob: response.blob,
          url: URL.createObjectURL(response.blob),
          meta: response.compressionMeta,
        },
      };
    });
    setStatus({
      message: 'Preview ready.',
      beforeSize: formatBytes(response.compressionMeta?.originalSize ?? file.size),
      afterSize: formatBytes(response.compressionMeta?.outputSize ?? response.blob.size),
    });
  };

  useEffect(() => {
    if (!selectedFile) return;
    if (previewTimerRef.current) window.clearTimeout(previewTimerRef.current);
    previewTimerRef.current = window.setTimeout(() => {
      setBusy(true);
      void applyPreview(selectedFile)
        .catch((error) => setStatus({ message: '', error: error instanceof Error ? error.message : 'Unexpected error' }))
        .finally(() => setBusy(false));
    }, 250);
    return () => {
      if (previewTimerRef.current) window.clearTimeout(previewTimerRef.current);
    };
  }, [selectedFile?.name, selectedSettings.quality, selectedSettings.colors, selectedSettings.precision]);

  const saveAll = async () => {
    const zip = new JSZip();
    for (const file of files) {
      const result = results[file.name];
      if (!result) continue;
      zip.file(file.name.replace(/(\.[^.]+)?$/, '_compressed$1'), result.blob);
    }
    const blob = await zip.generateAsync({ type: 'blob' });
    downloadBlob(blob, 'compressed_images.zip');
  };

  const compressAll = async () => {
    setBusy(true);
    setStatus(null);
    try {
      for (const file of files) {
        await applyPreview(file);
      }
      setStatus({
        message: 'Batch compression ready.',
        beforeSize: formatBytes(beforeTotal),
        afterSize: formatBytes(afterTotal),
      });
    } catch (error) {
      setStatus({ message: '', error: error instanceof Error ? error.message : 'Unexpected error' });
    } finally {
      setBusy(false);
    }
  };

  const shiftSetting = (field: 'quality' | 'colors' | 'precision', delta: number, min: number, max: number) => {
    if (!selectedFile) return;
    setSettings((current) => {
      const base = current[selectedFile.name] ?? defaultSettings;
      return {
        ...current,
        [selectedFile.name]: {
          ...base,
          [field]: Math.max(min, Math.min(max, base[field] + delta)),
        },
      };
    });
  };

  const clearAll = () => {
    Object.values(results).forEach((result) => URL.revokeObjectURL(result.url));
    setFiles([]);
    setResults({});
    setSettings({});
    setStatus(null);
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl">Image Compression Studio</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">Compress multiple images, adjust one file at a time, preview before saving, and download individually or as a ZIP.</p>
        </div>
        <button type="button" onClick={clearAll} className="inline-flex items-center gap-2 rounded-xl border border-slate-300 px-4 py-2 text-sm text-slate-700 dark:border-slate-600 dark:text-slate-100">
          <Trash2 size={14} /> Clear
        </button>
      </div>

      <FileDropzone files={files} setFiles={setFiles} accept="image/*,.svg" />

      <div className="rounded-2xl border border-slate-200 bg-white/80 p-4 dark:border-slate-700 dark:bg-slate-900/80">
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <span><strong>Before:</strong> {formatBytes(beforeTotal)}</span>
          <span><strong>After:</strong> {formatBytes(afterTotal)}</span>
          <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-200">
            {beforeTotal > 0 ? `${Math.max(0, ((beforeTotal - afterTotal) * 100) / beforeTotal).toFixed(1)}% reduction` : '0.0% reduction'}
          </span>
        </div>
      </div>

      {files.length > 0 && (
        <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
          <div className="space-y-3">
            {files.map((file, index) => {
              const result = results[file.name];
              return (
                <button
                  key={file.name}
                  type="button"
                  onClick={() => setSelectedIndex(index)}
                  className={`w-full rounded-2xl border p-3 text-left ${selectedIndex === index ? 'border-brand-500 bg-brand-50 dark:bg-brand-950/20' : 'border-slate-200 bg-white/80 dark:border-slate-700 dark:bg-slate-900/80'}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{file.name}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">{formatBytes(file.size)}</p>
                    </div>
                    {result && (
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          downloadBlob(result.blob, file.name.replace(/(\.[^.]+)?$/, '_compressed$1'));
                        }}
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-2 py-1 text-xs text-slate-700 dark:border-slate-600 dark:text-slate-100"
                      >
                        <Download size={12} /> Save
                      </button>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {selectedFile && (
            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-200 bg-white/80 p-4 dark:border-slate-700 dark:bg-slate-900/80">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="font-semibold">{selectedFile.name}</h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400">{formatBytes(selectedFile.size)}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      disabled={!selectedResult}
                      onClick={() => {
                        if (!selectedFile || !selectedResult) return;
                        downloadBlob(selectedResult.blob, selectedFile.name.replace(/(\.[^.]+)?$/, '_compressed$1'));
                      }}
                      className="rounded-xl bg-brand-600 px-4 py-2 text-white disabled:opacity-40"
                    >
                      Apply
                    </button>
                    {files.length > 1 && (
                      <button type="button" disabled={busy} onClick={() => void compressAll()} className="rounded-xl border border-slate-300 px-4 py-2 text-slate-700 dark:border-slate-600 dark:text-slate-100">
                        Compress {files.length}
                      </button>
                    )}
                    <button type="button" disabled={busy || Object.keys(results).length === 0} onClick={() => void saveAll()} className="rounded-xl border border-slate-300 px-4 py-2 text-slate-700 dark:border-slate-600 dark:text-slate-100">
                      Save All
                    </button>
                  </div>
                </div>

                {supportsQuality(selectedExt) && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium">Quality</label>
                      <input
                        className="w-20 rounded-lg border border-slate-300 bg-transparent px-2 py-1 text-sm text-slate-900 dark:border-slate-600 dark:text-slate-100"
                        type="number"
                        min={0}
                        max={100}
                        value={selectedSettings.quality}
                        onChange={(e) => setSettings((current) => ({ ...current, [selectedFile.name]: { ...selectedSettings, quality: Number(e.target.value || 0) } }))}
                      />
                    </div>
                    <input className="w-full" type="range" min={0} max={100} value={selectedSettings.quality} onChange={(e) => setSettings((current) => ({ ...current, [selectedFile.name]: { ...selectedSettings, quality: Number(e.target.value) } }))} />
                    <div className="flex gap-2 text-sm">
                      <button type="button" className="rounded-lg border border-slate-300 px-2 py-1 text-slate-700 dark:border-slate-600 dark:text-slate-100" onClick={() => shiftSetting('quality', -10, 0, 100)}>-10</button>
                      <button type="button" className="rounded-lg border border-slate-300 px-2 py-1 text-slate-700 dark:border-slate-600 dark:text-slate-100" onClick={() => shiftSetting('quality', -1, 0, 100)}>-1</button>
                      <button type="button" className="rounded-lg border border-slate-300 px-2 py-1 text-slate-700 dark:border-slate-600 dark:text-slate-100" onClick={() => shiftSetting('quality', 1, 0, 100)}>+1</button>
                      <button type="button" className="rounded-lg border border-slate-300 px-2 py-1 text-slate-700 dark:border-slate-600 dark:text-slate-100" onClick={() => shiftSetting('quality', 10, 0, 100)}>+10</button>
                    </div>
                  </div>
                )}

                {supportsColors(selectedExt) && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium">Colors</label>
                      <input
                        className="w-24 rounded-lg border border-slate-300 bg-transparent px-2 py-1 text-sm text-slate-900 dark:border-slate-600 dark:text-slate-100"
                        type="number"
                        min={2}
                        max={256}
                        value={selectedSettings.colors}
                        onChange={(e) => setSettings((current) => ({ ...current, [selectedFile.name]: { ...selectedSettings, colors: Number(e.target.value || 2) } }))}
                      />
                    </div>
                    <input className="w-full" type="range" min={2} max={256} value={selectedSettings.colors} onChange={(e) => setSettings((current) => ({ ...current, [selectedFile.name]: { ...selectedSettings, colors: Number(e.target.value) } }))} />
                  </div>
                )}

                {supportsPrecision(selectedExt) && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium">Precision</label>
                      <input
                        className="w-20 rounded-lg border border-slate-300 bg-transparent px-2 py-1 text-sm text-slate-900 dark:border-slate-600 dark:text-slate-100"
                        type="number"
                        min={0}
                        max={3}
                        value={selectedSettings.precision}
                        onChange={(e) => setSettings((current) => ({ ...current, [selectedFile.name]: { ...selectedSettings, precision: Number(e.target.value || 0) } }))}
                      />
                    </div>
                    <input className="w-full" type="range" min={0} max={3} step={1} value={selectedSettings.precision} onChange={(e) => setSettings((current) => ({ ...current, [selectedFile.name]: { ...selectedSettings, precision: Number(e.target.value) } }))} />
                  </div>
                )}
              </div>

              {selectedResult ? (
                <div>
                  <BeforeAfterCompare
                    beforeUrl={selectedOriginalUrl ?? ''}
                    afterUrl={selectedResult.url}
                    beforeLabel={formatBytes(selectedResult.meta?.originalSize ?? selectedFile.size)}
                    afterLabel={formatBytes(selectedResult.meta?.outputSize ?? selectedResult.blob.size)}
                    reductionLabel={`${selectedResult.meta?.reductionPercent.toFixed(1) ?? '0.0'}% smaller`}
                  />
                </div>
              ) : (
                <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900/80 dark:text-slate-400">
                  Adjust settings for the selected file. Preview updates automatically, and Apply downloads the current result.
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {status && <ResultPanel {...status} />}
    </div>
  );
}
