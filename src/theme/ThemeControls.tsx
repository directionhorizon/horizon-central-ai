import { Moon, Palette, RotateCcw, Sun, Sunrise, Sunset } from 'lucide-react';
import { useTheme } from './ThemeProvider';
import { ACCENTS, THEME_OPTIONS } from './theme';

const label = 'text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500';
const chip = 'rounded-lg border border-white/10 px-2.5 py-1.5 text-[11px] text-slate-300 hover:bg-white/5';
const chipActive = 'rounded-lg border border-cyan-400/30 bg-cyan-400/10 px-2.5 py-1.5 text-[11px] text-cyan-100';

/**
 * Panneau de personnalisation de l'affichage.
 * Il ne dépend ni du réseau ni d'un fournisseur IA : la préférence est locale.
 */
export function ThemeControls({ compact = false }: { compact?: boolean }) {
  const { preference, resolved, settings, update, setPreference, setAccent, setCustom, reset } = useTheme();

  return (
    <div className="space-y-5">
      <header className="flex items-start justify-between gap-3">
        <div>
          <p className={label}>Apparence</p>
          <p className="mt-1 text-xs text-slate-500">
            Appliqué à toute l’application et conservé après redémarrage.
          </p>
        </div>
        <button type="button" className={chip} onClick={reset} title="Revenir au thème sombre cyan">
          <RotateCcw size={12} className="mr-1 inline" /> Réinitialiser
        </button>
      </header>

      <div className="grid gap-2 sm:grid-cols-2">
        {THEME_OPTIONS.map((option) => (
          <button
            key={option.id}
            type="button"
            onClick={() => setPreference(option.id)}
            className={`${preference === option.id ? chipActive : chip} text-left`}
            aria-pressed={preference === option.id}
          >
            <span className="flex items-center gap-2 text-xs font-medium">
              {option.id === 'light' ? <Sun size={13} /> : null}
              {option.id === 'dark' ? <Moon size={13} /> : null}
              {option.id === 'auto' ? <Sunrise size={13} /> : null}
              {option.id === 'custom' ? <Palette size={13} /> : null}
              {option.label}
            </span>
            <span className="mt-1 block text-[10px] text-slate-500">{option.hint}</span>
          </button>
        ))}
      </div>

      <div>
        <p className={label}>Palette d’accentuation</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {ACCENTS.map((accent) => (
            <button
              key={accent.id}
              type="button"
              onClick={() => setAccent(accent.id)}
              aria-pressed={settings.accent === accent.id}
              title={accent.label}
              className={
                settings.accent === accent.id
                  ? 'flex items-center gap-2 rounded-lg border border-cyan-400/40 bg-cyan-400/10 px-2 py-1 text-[11px] text-cyan-100'
                  : 'flex items-center gap-2 rounded-lg border border-white/10 px-2 py-1 text-[11px] text-slate-300 hover:bg-white/5'
              }
            >
              <span
                aria-hidden="true"
                style={{ background: accent.swatch }}
                className="inline-block h-3 w-3 rounded-full"
              />
              {accent.label}
            </button>
          ))}
        </div>
      </div>

      {preference === 'auto' && (
        <div className="rounded-lg border border-white/10 p-3">
          <label className="flex items-center gap-2 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={settings.scheduleEnabled}
              onChange={(event) => update({ scheduleEnabled: event.target.checked })}
            />
            Basculer selon l’heure locale
          </label>
          {settings.scheduleEnabled && (
            <div className="mt-3 flex flex-wrap items-center gap-4 text-[11px] text-slate-400">
              <span className="flex items-center gap-2">
                <Sunrise size={13} /> Jour dès
                <input
                  type="number"
                  min={0}
                  max={23}
                  value={settings.dayStartHour}
                  onChange={(event) => update({ dayStartHour: Number(event.target.value) })}
                  className="w-14 rounded border border-white/10 bg-transparent px-1.5 py-0.5 text-slate-200"
                />
                h
              </span>
              <span className="flex items-center gap-2">
                <Sunset size={13} /> Nuit dès
                <input
                  type="number"
                  min={0}
                  max={23}
                  value={settings.nightStartHour}
                  onChange={(event) => update({ nightStartHour: Number(event.target.value) })}
                  className="w-14 rounded border border-white/10 bg-transparent px-1.5 py-0.5 text-slate-200"
                />
                h
              </span>
            </div>
          )}
          <p className="mt-2 text-[10px] text-slate-500">
            Un choix manuel reste toujours prioritaire : le mode automatique ne l’écrase jamais.
          </p>
        </div>
      )}

      {preference === 'custom' && (
        <div className="rounded-lg border border-white/10 p-3">
          <p className={label}>Palette personnalisée</p>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {(
              [
                ['background', 'Fond'],
                ['surface', 'Panneaux'],
                ['foreground', 'Texte'],
                ['accent', 'Accent'],
              ] as const
            ).map(([key, text]) => (
              <label key={key} className="flex items-center justify-between gap-2 text-[11px] text-slate-400">
                {text}
                <input
                  type="color"
                  value={settings.custom[key]}
                  onChange={(event) => setCustom({ [key]: event.target.value })}
                  className="h-7 w-12 cursor-pointer rounded border border-white/10 bg-transparent"
                />
              </label>
            ))}
          </div>
          <label className="mt-3 flex items-center gap-2 text-[11px] text-slate-400">
            Base de contraste
            <select
              value={settings.custom.base}
              onChange={(event) => setCustom({ base: event.target.value === 'light' ? 'light' : 'dark' })}
              className="rounded border border-white/10 bg-transparent px-2 py-1 text-slate-200"
            >
              <option value="dark">Sombre</option>
              <option value="light">Clair</option>
            </select>
          </label>
        </div>
      )}

      {!compact && (
        <p className="text-[10px] text-slate-600">
          Thème appliqué : <span className="text-slate-400">{resolved}</span> · accent{' '}
          <span className="text-slate-400">{settings.accent}</span> · préférence locale
          (<code>horizon-local-ai:theme:v1</code>)
        </p>
      )}
    </div>
  );
}

export default ThemeControls;

