import { FileText, GripVertical, Image as ImageIcon, UploadCloud, X } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';

type Props = {
  files: File[];
  setFiles: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
};

type PreviewItem = {
  file: File;
  url: string;
  kind: 'image' | 'pdf' | 'other';
};

function reorder(items: File[], from: number, to: number): File[] {
  const next = [...items];
  const [moved] = next.splice(from, 1);
  next.splice(to, 0, moved);
  return next;
}

export function FileDropzone({ files, setFiles, accept, multiple = true }: Props) {
  const ref = useRef<HTMLInputElement | null>(null);
  const [dragIndex, setDragIndex] = useState<number | null>(null);

  const previews: PreviewItem[] = useMemo(
    () =>
      files.map((file) => {
        const type = file.type;
        const kind = type.startsWith('image/') ? 'image' : type === 'application/pdf' ? 'pdf' : 'other';
        return { file, url: URL.createObjectURL(file), kind };
      }),
    [files]
  );

  useEffect(() => {
    return () => {
      previews.forEach((p) => URL.revokeObjectURL(p.url));
    };
  }, [files]);

  const handleFiles = (list: FileList | null) => {
    if (!list) return;
    const next = Array.from(list);
    setFiles(multiple ? [...files, ...next] : next.slice(0, 1));
  };

  const remove = (idx: number) => setFiles(files.filter((_, i) => i !== idx));

  return (
    <div className="space-y-4">
      <div
        className="cursor-pointer rounded-2xl border-2 border-dashed border-slate-300 p-6 text-center text-slate-900 transition hover:border-brand-500 dark:border-slate-700 dark:text-slate-100"
        onClick={() => ref.current?.click()}
        onDrop={(e) => {
          e.preventDefault();
          handleFiles(e.dataTransfer.files);
        }}
        onDragOver={(e) => e.preventDefault()}
      >
        <input ref={ref} type="file" hidden accept={accept} multiple={multiple} onChange={(e) => handleFiles(e.target.files)} />
        <UploadCloud className="mx-auto mb-3 h-8 w-8 text-brand-600" />
        <p className="font-medium">Drag and drop files here, or click to browse</p>
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Files are processed locally and removed from temp storage after processing.</p>
      </div>

      {previews.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-semibold text-slate-900 dark:text-slate-100">Selected ({previews.length})</p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {previews.map((item, idx) => (
              <div
                key={`${item.file.name}-${idx}`}
                draggable={multiple}
                onDragStart={() => setDragIndex(idx)}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => {
                  if (dragIndex === null || dragIndex === idx) return;
                  setFiles(reorder(files, dragIndex, idx));
                  setDragIndex(null);
                }}
                className="rounded-xl border border-slate-200 bg-white/70 dark:border-slate-700 dark:bg-slate-900/70 p-2"
              >
                <div className="mb-2 flex items-center justify-between gap-2 text-xs text-slate-600 dark:text-slate-300">
                  <span className="inline-flex items-center gap-1 truncate">
                    <GripVertical size={14} />
                    <span className="truncate" title={item.file.name}>{item.file.name}</span>
                  </span>
                  <button type="button" onClick={() => remove(idx)} className="rounded border p-1 hover:bg-slate-100 dark:hover:bg-slate-800">
                    <X size={12} />
                  </button>
                </div>

                {item.kind === 'image' && <img src={item.url} alt={item.file.name} className="h-32 w-full rounded-md object-cover" />}
                {item.kind === 'pdf' && (
                  <div className="h-32 w-full rounded-md border border-slate-200 dark:border-slate-700 overflow-hidden bg-slate-50 dark:bg-slate-900">
                    <iframe title={item.file.name} src={item.url} className="h-full w-full" />
                  </div>
                )}
                {item.kind === 'other' && (
                  <div className="flex h-32 w-full items-center justify-center rounded-md border border-slate-200 text-slate-500 dark:border-slate-700 dark:text-slate-400">
                    <span className="inline-flex items-center gap-2"><FileText size={16} /> Preview unavailable</span>
                  </div>
                )}

                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{(item.file.size / 1024).toFixed(1)} KB</p>
              </div>
            ))}
          </div>
          {multiple && previews.length > 1 && <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Drag cards to reorder processing order.</p>}
        </div>
      )}
    </div>
  );
}
