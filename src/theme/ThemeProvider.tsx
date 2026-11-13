import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import {
  customVariables,
  readStoredSettings,
  resolveTheme,
  writeStoredSettings,
  type AccentId,
  type ResolvedTheme,
  type ThemeId,
  type ThemePreference,
  type ThemeSettings,
} from './theme';

interface ThemeContextValue {
  /** Préférence choisie par l'utilisateur (peut être « auto » ou « custom »). */
  preference: ThemePreference;
  /** Thème réellement appliqué après résolution. */
  resolved: ResolvedTheme;
  settings: ThemeSettings;
  /** Vrai si le système demande de réduire les animations. */
  reducedMotion: boolean;
  setPreference: (preference: ThemePreference) => void;
  setAccent: (accent: AccentId) => void;
  update: (patch: Partial<ThemeSettings>) => void;
  setCustom: (patch: Partial<ThemeSettings['custom']>) => void;
  reset: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

/** Variable d'environnement ignorée si l'utilisateur a déjà choisi : local d'abord. */
const prefersReducedMotion = (): boolean =>
  typeof window !== 'undefined' && window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : false;

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<ThemeSettings>(() => readStoredSettings());
  const [systemPrefersDark, setSystemPrefersDark] = useState<boolean>(() =>
    typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia('(prefers-color-scheme: dark)').matches
      : true,
  );
  const [reducedMotion, setReducedMotion] = useState<boolean>(() => prefersReducedMotion());
  const [tick, setTick] = useState(0);
  const initialized = useRef(false);

  const resolved = useMemo<ResolvedTheme>(
    () => resolveTheme(settings, { systemPrefersDark }),
    [settings, systemPrefersDark, tick],
  );

  /** Application effective : attributs + variables du thème personnalisé. */
  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = resolved;
    root.dataset.accent = settings.accent;
    root.classList.toggle('dark', resolved !== 'light');
    root.style.colorScheme = settings.preference === 'custom' ? settings.custom.base : resolved === 'light' ? 'light' : 'dark';

    if (settings.preference === 'custom') {
      const variables = customVariables(settings.custom);
      for (const [name, value] of Object.entries(variables)) root.style.setProperty(name, value);
    } else {
      const variables = customVariables(settings.custom);
      for (const name of Object.keys(variables)) root.style.removeProperty(name);
    }
    if (!initialized.current) {
      initialized.current = true;
      root.dataset.themeReady = 'true';
    }
  }, [resolved, settings.accent, settings.preference, settings.custom]);

  // Persistance : la préférence survit à la fermeture et au redémarrage.
  useEffect(() => {
    writeStoredSettings(settings);
  }, [settings]);

  // Préférences système (mode sombre / animations réduites).
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const dark = window.matchMedia('(prefers-color-scheme: dark)');
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const onDark = (event: MediaQueryListEvent) => setSystemPrefersDark(event.matches);
    const onMotion = (event: MediaQueryListEvent) => setReducedMotion(event.matches);
    dark.addEventListener('change', onDark);
    motion.addEventListener('change', onMotion);
    return () => {
      dark.removeEventListener('change', onDark);
      motion.removeEventListener('change', onMotion);
    };
  }, []);

  // Passage automatique piloté par l'heure locale : vérifié chaque minute.
  useEffect(() => {
    if (settings.preference !== 'auto' || !settings.scheduleEnabled) return;
    const timer = window.setInterval(() => setTick((value) => value + 1), 60_000);
    return () => window.clearInterval(timer);
  }, [settings.preference, settings.scheduleEnabled]);

  const update = useCallback((patch: Partial<ThemeSettings>) => {
    setSettings((current) => ({ ...current, ...patch }));
  }, []);

  const setPreference = useCallback((preference: ThemePreference) => {
    setSettings((current) => ({ ...current, preference }));
  }, []);

  const setAccent = useCallback((accent: AccentId) => {
    setSettings((current) => ({ ...current, accent }));
  }, []);

  const setCustom = useCallback((patch: Partial<ThemeSettings['custom']>) => {
    setSettings((current) => ({ ...current, custom: { ...current.custom, ...patch } }));
  }, []);

  const reset = useCallback(() => {
    setSettings((current) => ({
      preference: 'dark',
      accent: 'cyan',
      scheduleEnabled: false,
      dayStartHour: current.dayStartHour,
      nightStartHour: current.nightStartHour,
      custom: current.custom,
    }));
  }, []);

  const value = useMemo<ThemeContextValue>(
    () => ({ preference: settings.preference, resolved, settings, reducedMotion, setPreference, setAccent, update, setCustom, reset }),
    [settings, resolved, reducedMotion, setPreference, setAccent, update, setCustom, reset],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const value = useContext(ThemeContext);
  if (!value) throw new Error('useTheme doit être utilisé dans un ThemeProvider');
  return value;
}
