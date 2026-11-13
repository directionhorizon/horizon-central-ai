/**
 * Modèle du gestionnaire de thèmes HORIZON.
 *
 * La préférence de thème est unique, centrale et persistante : aucune page ne
 * gère sa propre palette. Ce module ne lit ni n'écrit aucun secret et ne dépend
 * ni du réseau ni d'un fournisseur IA (personnalisation strictement locale).
 */

export type ThemeId = 'dark' | 'light' | 'comfort' | 'contrast';
/** Thème réellement appliqué : un des thèmes prédéfinis, ou la palette personnalisée. */
export type ResolvedTheme = ThemeId | 'custom';
export type ThemePreference = ThemeId | 'auto' | 'custom';
export type AccentId = 'cyan' | 'azure' | 'violet' | 'emerald' | 'amber' | 'rose';

export interface CustomPalette {
  /** Base de contraste : détermine les couleurs dérivées et le color-scheme. */
  base: 'dark' | 'light';
  background: string;
  surface: string;
  foreground: string;
  accent: string;
}

export interface ThemeSettings {
  preference: ThemePreference;
  accent: AccentId;
  /** Bascule selon l'heure locale (utilisée uniquement en mode « auto »). */
  scheduleEnabled: boolean;
  /** Heure (0-23) à partir de laquelle le thème clair s'applique. */
  dayStartHour: number;
  /** Heure (0-23) à partir de laquelle le thème sombre s'applique. */
  nightStartHour: number;
  custom: CustomPalette;
}

export const THEME_STORAGE_KEY = 'horizon-local-ai:theme:v1';

export const ACCENTS: ReadonlyArray<{ id: AccentId; label: string; swatch: string }> = [
  { id: 'cyan', label: 'Cyan', swatch: '#00d1ff' },
  { id: 'azure', label: 'Bleu', swatch: '#3b82f6' },
  { id: 'violet', label: 'Violet', swatch: '#8b5cf6' },
  { id: 'emerald', label: 'Émeraude', swatch: '#10b981' },
  { id: 'amber', label: 'Ambre', swatch: '#f59e0b' },
  { id: 'rose', label: 'Rose', swatch: '#f43f5e' },
];

export const THEME_OPTIONS: ReadonlyArray<{
  id: ThemePreference;
  label: string;
  hint: string;
}> = [
  { id: 'auto', label: 'Automatique', hint: 'Suit le système, puis l’heure si activée' },
  { id: 'light', label: 'Clair', hint: 'Environnements lumineux, travail de jour' },
  { id: 'dark', label: 'Sombre', hint: 'Environnements peu éclairés, travail de nuit' },
  { id: 'comfort', label: 'Confort visuel', hint: 'Couleurs douces, éblouissement réduit' },
  { id: 'contrast', label: 'Contraste élevé', hint: 'Lisibilité et accessibilité maximales' },
  { id: 'custom', label: 'Personnalisé', hint: 'Fond, surface et accent au choix' },
];

export const DEFAULT_SETTINGS: ThemeSettings = {
  preference: 'dark',
  accent: 'cyan',
  scheduleEnabled: false,
  dayStartHour: 7,
  nightStartHour: 20,
  custom: {
    base: 'dark',
    background: '#101317',
    surface: '#171b21',
    foreground: '#f2f5f9',
    accent: '#00d1ff',
  },
};

const hexOr = (value: unknown, fallback: string): string =>
  typeof value === 'string' && /^#[0-9a-fA-F]{6}$/.test(value.trim()) ? value.trim() : fallback;

const clampHour = (value: unknown, fallback: number): number => {
  const parsed = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(23, Math.max(0, Math.round(parsed)));
};

/** Lecture défensive : toute valeur corrompue retombe sur la valeur par défaut. */
export function parseSettings(raw: unknown): ThemeSettings {
  if (!raw || typeof raw !== 'object') return { ...DEFAULT_SETTINGS };
  const input = raw as Record<string, unknown>;
  const pick = (allowed: readonly string[], value: unknown, fallback: string): string =>
    typeof value === 'string' && allowed.includes(value) ? value : fallback;

  const customInput = (input.custom ?? {}) as Record<string, unknown>;
  return {
    preference: pick(
      ['auto', 'dark', 'light', 'comfort', 'contrast', 'custom'],
      input.preference,
      DEFAULT_SETTINGS.preference,
    ) as ThemePreference,
    accent: pick(
      ACCENTS.map((item) => item.id),
      input.accent,
      DEFAULT_SETTINGS.accent,
    ) as AccentId,
    scheduleEnabled: input.scheduleEnabled === true,
    dayStartHour: clampHour(input.dayStartHour, DEFAULT_SETTINGS.dayStartHour),
    nightStartHour: clampHour(input.nightStartHour, DEFAULT_SETTINGS.nightStartHour),
    custom: {
      base: customInput.base === 'light' ? 'light' : 'dark',
      background: hexOr(customInput.background, DEFAULT_SETTINGS.custom.background),
      surface: hexOr(customInput.surface, DEFAULT_SETTINGS.custom.surface),
      foreground: hexOr(customInput.foreground, DEFAULT_SETTINGS.custom.foreground),
      accent: hexOr(customInput.accent, DEFAULT_SETTINGS.custom.accent),
    },
  };
}

export function readStoredSettings(): ThemeSettings {
  try {
    const raw = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (!raw) return { ...DEFAULT_SETTINGS };
    return parseSettings(JSON.parse(raw) as unknown);
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

export function writeStoredSettings(settings: ThemeSettings): void {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // Stockage indisponible : le thème reste appliqué pour la session en cours.
  }
}

/** Sommes-nous dans la plage « jour » (thème clair) selon l'heure locale ? */
export function isDayTime(hour: number, dayStartHour: number, nightStartHour: number): boolean {
  if (dayStartHour === nightStartHour) return true;
  if (dayStartHour < nightStartHour) return hour >= dayStartHour && hour < nightStartHour;
  // Plage traversant minuit (ex. 20 h → 7 h).
  return hour >= dayStartHour || hour < nightStartHour;
}

/**
 * Résout la préférence en thème réellement appliqué.
 * `systemPrefersDark` provient de `prefers-color-scheme`. Un choix explicite de
 * l'utilisateur est toujours prioritaire : le mode automatique ne l'écrase pas.
 */
export function resolveTheme(
  settings: ThemeSettings,
  options: { systemPrefersDark: boolean; now?: Date },
): ResolvedTheme {
  if (settings.preference !== 'auto') return settings.preference;
  if (settings.scheduleEnabled) {
    const now = options.now ?? new Date();
    return isDayTime(now.getHours(), settings.dayStartHour, settings.nightStartHour) ? 'light' : 'dark';
  }
  return options.systemPrefersDark ? 'dark' : 'light';
}

/** Variables CSS du thème personnalisé (aucune valeur inventée : saisie utilisateur). */
export function customVariables(custom: CustomPalette): Record<string, string> {
  const light = custom.base === 'light';
  return {
    '--custom-background': custom.background,
    '--custom-surface': custom.surface,
    '--custom-surface-2': light ? '#eef1f7' : '#1e232b',
    '--custom-foreground': custom.foreground,
    '--custom-muted': light ? '#5b6474' : '#9aa5b4',
    '--custom-accent': custom.accent,
    '--custom-accent-fg': light ? '#ffffff' : '#06131a',
    '--custom-accent-mix': light ? '#06232b' : '#e6faff',
    '--custom-border': light ? '#d3dae6' : '#2a323c',
    '--custom-hairline': light ? 'rgba(16,24,40,0.12)' : 'rgba(255,255,255,0.12)',
    '--custom-hover': light ? 'rgba(16,24,40,0.06)' : 'rgba(255,255,255,0.06)',
    '--custom-scheme': light ? 'light' : 'dark',
  };
}

