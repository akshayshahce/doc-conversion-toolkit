export type CompressionMeta = {
  originalSize: number;
  outputSize: number;
  reductionPercent: number;
  targetReductionPercent: number | null;
  targetAchieved: boolean;
  forceReduceSize: boolean;
};

export type FormResult = {
  blob: Blob;
  headers: Headers;
  compressionMeta: CompressionMeta | null;
};

export function getFilenameFromHeaders(headers: Headers): string | null {
  const disposition = headers.get('content-disposition');
  if (!disposition) return null;
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1]);
  const plainMatch = disposition.match(/filename=\"?([^\";]+)\"?/i);
  return plainMatch?.[1] ?? null;
}

function parseCompressionMeta(headers: Headers): CompressionMeta | null {
  const originalSize = headers.get('X-Original-Size');
  const outputSize = headers.get('X-Output-Size');
  const reductionPercent = headers.get('X-Reduction-Percent');
  if (!originalSize || !outputSize || !reductionPercent) return null;

  const target = headers.get('X-Target-Reduction-Percent');
  return {
    originalSize: Number(originalSize),
    outputSize: Number(outputSize),
    reductionPercent: Number(reductionPercent),
    targetReductionPercent: target ? Number(target) : null,
    targetAchieved: headers.get('X-Target-Achieved') === 'true',
    forceReduceSize: headers.get('X-Force-Reduce-Size') === 'true'
  };
}

export async function postForm(endpoint: string, formData: FormData): Promise<FormResult> {
  const response = await fetch(endpoint, {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    let detail = 'Request failed';
    try {
      const parsed = await response.json();
      detail = parsed?.detail ?? detail;
    } catch {
      // ignore parse errors
    }
    throw new Error(detail);
  }

  return {
    blob: await response.blob(),
    headers: response.headers,
    compressionMeta: parseCompressionMeta(response.headers)
  };
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const idx = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** idx).toFixed(idx === 0 ? 0 : 2)} ${units[idx]}`;
}
