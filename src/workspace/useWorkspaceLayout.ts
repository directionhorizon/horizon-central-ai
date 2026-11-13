import { useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react';

/**
 * Disposition de l'espace de travail : deux panneaux latéraux indépendants.
 *
 * - largeurs ajustables à la souris (bornées) ;
 * - repli/dépli indépendants (le panneau replié reste accessible en rail) ;
 * - préférences conservées après redémarrage (`localStorage`) ;
 * - commande de restauration ;
 * - adaptation : 3 colonnes sur ordinateur, tiroirs sur tablette/mobile.
 */

export type Side = 'left' | 'right';

export interface WorkspaceLayout {
  leftWidth: number;
  rightWidth: number;
  leftCollapsed: boolean;
  rightCollapsed: boolean;
}

export const WORKSPACE_DEFAULTS: WorkspaceLayout = {
  leftWidth: 280,
  rightWidth: 330,
  leftCollapsed: false,
  rightCollapsed: false,
};

const MIN_WIDTH = 216;
const MAX_WIDTH = 520;
export const RAIL_WIDTH = 52;
export const STORAGE_KEY = 'horizon-central-ai:workspace:v1';

const clamp = (value: number): number => Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, Math.round(value)));

function readLayout(): WorkspaceLayout {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...WORKSPACE_DEFAULTS };
    const parsed = JSON.parse(raw) as Partial<WorkspaceLayout>;
    return {
      leftWidth: clamp(Number(parsed.leftWidth) || WORKSPACE_DEFAULTS.leftWidth),
      rightWidth: clamp(Number(parsed.rightWidth) || WORKSPACE_DEFAULTS.rightWidth),
      leftCollapsed: parsed.leftCollapsed === true,
      rightCollapsed: parsed.rightCollapsed === true,
    };
  } catch {
    return { ...WORKSPACE_DEFAULTS };
  }
}

export type ViewportClass = 'desktop' | 'tablet' | 'mobile';

function classify(width: number): ViewportClass {
  if (width >= 1024) return 'desktop';
  if (width >= 768) return 'tablet';
  return 'mobile';
}

export function useWorkspaceLayout() {
  const [layout, setLayout] = useState<WorkspaceLayout>(() => readLayout());
  const [viewport, setViewport] = useState<ViewportClass>(() =>
    classify(typeof window === 'undefined' ? 1280 : window.innerWidth),
  );
  const dragging = useRef<Side | null>(null);

  // Persistance : la disposition survit à la fermeture de l'application.
  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
    } catch {
      /* stockage indisponible : la disposition reste valable pour la session */
    }
  }, [layout]);

  useEffect(() => {
    const onResize = () => setViewport(classify(window.innerWidth));
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const setWidth = useCallback((side: Side, width: number) => {
    setLayout((current) =>
      side === 'left'
        ? { ...current, leftWidth: clamp(width) }
        : { ...current, rightWidth: clamp(width) },
    );
  }, []);

  const toggle = useCallback((side: Side) => {
    setLayout((current) =>
      side === 'left'
        ? { ...current, leftCollapsed: !current.leftCollapsed }
        : { ...current, rightCollapsed: !current.rightCollapsed },
    );
  }, []);

  const reset = useCallback(() => setLayout({ ...WORKSPACE_DEFAULTS }), []);

  /** Redimensionnement à la souris (poignée verticale entre panneau et centre). */
  const startResize = useCallback(
    (side: Side) => (event: ReactPointerEvent<HTMLDivElement>) => {
      if (viewport !== 'desktop') return;
      event.preventDefault();
      dragging.current = side;
      const startX = event.clientX;
      const startWidth = side === 'left' ? layout.leftWidth : layout.rightWidth;
      const onMove = (moveEvent: PointerEvent) => {
        const delta = side === 'left' ? moveEvent.clientX - startX : startX - moveEvent.clientX;
        setWidth(side, startWidth + delta);
      };
      const onUp = () => {
        dragging.current = null;
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', onUp);
        document.body.classList.remove('ws-resizing');
      };
      window.addEventListener('pointermove', onMove);
      window.addEventListener('pointerup', onUp);
      document.body.classList.add('ws-resizing');
    },
    [layout.leftWidth, layout.rightWidth, setWidth, viewport],
  );

  return { layout, viewport, setWidth, toggle, reset, startResize } as const;
}