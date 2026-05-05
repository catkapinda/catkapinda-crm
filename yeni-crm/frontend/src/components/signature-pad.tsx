'use client';

import { useEffect, useRef, useState } from 'react';
import { Eraser, PenTool } from 'lucide-react';

type SignaturePadProps = {
  width?: number;
  height?: number;
  onChange?: (isEmpty: boolean) => void;
};

export type SignaturePadHandle = {
  toDataUrl: () => string | null;
  isEmpty: () => boolean;
  clear: () => void;
};

/**
 * Canvas tabanlı imza alanı — touch + mouse + pen.
 * Boyutlar responsive (parent'a göre 100% genişlikte), DPR'ye göre keskin.
 */
export function SignaturePad({
  height = 200,
  onChange,
}: SignaturePadProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const drawing = useRef(false);
  const lastPos = useRef<{ x: number; y: number } | null>(null);
  const hasDrawn = useRef(false);
  const [isEmpty, setIsEmpty] = useState(true);

  // Sayfada başka kontrolden erişilebilmesi için global bir handle (window)
  // Form'dan submit edileceği zaman kullanılacak
  useEffect(() => {
    if (!canvasRef.current || !containerRef.current) return;
    const canvas = canvasRef.current;
    const container = containerRef.current;
    const dpr = window.devicePixelRatio || 1;
    const w = container.clientWidth;
    canvas.width = w * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${w}px`;
    canvas.style.height = `${height}px`;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 2.5;
  }, [height]);

  const getPos = (e: PointerEvent | React.PointerEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    return { x, y };
  };

  const start = (e: React.PointerEvent) => {
    e.preventDefault();
    const pos = getPos(e);
    if (!pos) return;
    drawing.current = true;
    lastPos.current = pos;
    canvasRef.current?.setPointerCapture(e.pointerId);
  };

  const move = (e: React.PointerEvent) => {
    if (!drawing.current) return;
    const pos = getPos(e);
    if (!pos) return;
    const ctx = canvasRef.current?.getContext('2d');
    if (!ctx || !lastPos.current) return;
    ctx.beginPath();
    ctx.moveTo(lastPos.current.x, lastPos.current.y);
    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();
    lastPos.current = pos;
    if (!hasDrawn.current) {
      hasDrawn.current = true;
      setIsEmpty(false);
      onChange?.(false);
    }
  };

  const end = (e: React.PointerEvent) => {
    drawing.current = false;
    lastPos.current = null;
    try {
      canvasRef.current?.releasePointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
  };

  const clear = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.save();
    // Reset transform to clear full canvas
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.restore();
    // Reapply scale
    const dpr = window.devicePixelRatio || 1;
    ctx.scale(dpr, dpr);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 2.5;
    hasDrawn.current = false;
    setIsEmpty(true);
    onChange?.(true);
  };

  // Window helper — form submit eden parent component canvas'a erişebilsin
  // (forwardRef yerine basit yöntem)
  useEffect(() => {
    const c = canvasRef.current;
    if (!c) return;
    const handle = {
      toDataUrl: () => {
        if (!hasDrawn.current) return null;
        return c.toDataURL('image/png');
      },
      isEmpty: () => !hasDrawn.current,
      clear,
    };
    (c as unknown as { __sigHandle?: typeof handle }).__sigHandle = handle;
  });

  return (
    <div ref={containerRef} className="w-full">
      <div className="relative bg-white rounded-xl border-2 border-slate-300 border-dashed overflow-hidden touch-none">
        <canvas
          ref={canvasRef}
          onPointerDown={start}
          onPointerMove={move}
          onPointerUp={end}
          onPointerCancel={end}
          onPointerLeave={end}
          className="block w-full select-none"
          style={{ touchAction: 'none' }}
        />
        {isEmpty && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="flex flex-col items-center gap-1.5 text-slate-300">
              <PenTool className="w-8 h-8" strokeWidth={1.5} />
              <span className="text-sm font-medium">Buraya imzanızı atın</span>
            </div>
          </div>
        )}
        {/* Imza çizgisi */}
        <div className="absolute left-6 right-6 bottom-6 border-t border-slate-200 pointer-events-none" />
      </div>
      <div className="flex items-center justify-between mt-2">
        <span className="text-xs text-slate-500">
          {isEmpty ? 'Parmak veya kalemle imzalayın' : '✓ İmza alındı'}
        </span>
        <button
          type="button"
          onClick={clear}
          disabled={isEmpty}
          className="inline-flex items-center gap-1 text-xs text-slate-600 hover:text-slate-900 disabled:opacity-40 disabled:cursor-not-allowed transition"
        >
          <Eraser className="w-3 h-3" /> Temizle
        </button>
      </div>
    </div>
  );
}

/**
 * Helper — canvas DOM elementinden data URL al.
 * <SignaturePad /> içindeki canvas'a window üzerinden eklenen handle'ı kullanır.
 */
export function getSignatureDataUrl(canvasEl: HTMLCanvasElement | null): string | null {
  if (!canvasEl) return null;
  const handle = (canvasEl as unknown as { __sigHandle?: { toDataUrl: () => string | null } })
    .__sigHandle;
  return handle?.toDataUrl() ?? null;
}
