import { useMemo, useState } from 'react';
import { Search, X } from 'lucide-react';
import type { SkillSummary } from '../api/entities';

/**
 * Sélecteur de compétences : recherche, filtre par catégorie, rattachement multiple.
 * Distingue les compétences héritées du système de celles propres à l'agent (D)
 * et affiche un aperçu de la compétence au survol (E).
 */
interface SkillPickerProps {
  skills: SkillSummary[];
  inherited?: SkillSummary[];
  attached: SkillSummary[];
  busy?: boolean;
  onAttach: (skillId: string) => void;
  onDetach: (skillId: string) => void;
}

export const SkillPicker = ({
  skills,
  inherited = [],
  attached,
  busy = false,
  onAttach,
  onDetach,
}: SkillPickerProps) => {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [hovered, setHovered] = useState<SkillSummary | null>(null);

  const attachedIds = useMemo(() => new Set(attached.map((skill) => skill.id)), [attached]);
  const inheritedIds = useMemo(() => new Set(inherited.map((skill) => skill.id)), [inherited]);

  const categories = useMemo(() => {
    const set = new Set<string>();
    skills.forEach((skill) => {
      if (skill.category) set.add(skill.category);
    });
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [skills]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return skills.filter((skill) => {
      if (category && skill.category !== category) return false;
      if (!needle) return true;
      return (
        skill.name.toLowerCase().includes(needle) ||
        (skill.category ?? '').toLowerCase().includes(needle)
      );
    });
  }, [skills, query, category]);

  return (
    <div className="mt-2 rounded-lg border border-white/[0.08] bg-black/20 p-3">
      {inherited.length > 0 && (
        <div className="mb-2">
          <p className="mb-1 text-[10px] uppercase tracking-wide text-slate-500">
            Héritées du système d'orchestration
          </p>
          <div className="flex flex-wrap gap-1">
            {inherited.map((skill) => (
              <span
                key={skill.id}
                className="rounded-full border border-slate-600/40 bg-slate-800/40 px-2 py-0.5 text-[11px] text-slate-300"
                title={`Héritée du système : ${skill.name}`}
              >
                {skill.name}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[160px]">
          <Search className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Rechercher une compétence…"
            className="w-full rounded-md border border-white/10 bg-black/30 py-1.5 pl-7 pr-7 text-xs text-slate-200 placeholder:text-slate-500 focus:border-cyan-500/40 focus:outline-none"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="absolute right-1.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
              aria-label="Effacer la recherche"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        <select
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          className="rounded-md border border-white/10 bg-black/30 px-2 py-1.5 text-xs text-slate-200 focus:border-cyan-500/40 focus:outline-none"
        >
          <option value="">Toutes les catégories</option>
          {categories.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-2 max-h-56 overflow-y-auto">
        {filtered.length === 0 ? (
          <p className="py-3 text-center text-[11px] text-slate-500">Aucune compétence ne correspond.</p>
        ) : (
          <ul className="space-y-1">
            {filtered.map((skill) => {
              const isAttached = attachedIds.has(skill.id);
              const isInherited = inheritedIds.has(skill.id);
              return (
                <li
                  key={skill.id}
                  onMouseEnter={() => setHovered(skill)}
                  onMouseLeave={() => setHovered(null)}
                  className="flex items-start gap-2 rounded-md px-2 py-1.5 hover:bg-white/[0.04]"
                >
                  <input
                    type="checkbox"
                    checked={isAttached || isInherited}
                    disabled={busy || isInherited}
                    onChange={() => (isAttached ? onDetach(skill.id) : onAttach(skill.id))}
                    className="mt-0.5 h-3.5 w-3.5 accent-cyan-500"
                    title={isInherited ? 'Héritée du système : non retirable ici' : undefined}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs text-slate-200">{skill.name}</p>
                    {skill.category && (
                      <p className="truncate text-[10px] text-slate-500">{skill.category}</p>
                    )}
                  </div>
                  {isInherited && (
                    <span className="shrink-0 rounded-full border border-slate-600/40 px-1.5 py-0.5 text-[9px] text-slate-400">
                      système
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {hovered && (
        <div className="mt-2 rounded-md border border-white/10 bg-black/40 p-2">
          <p className="text-[11px] font-medium text-slate-200">{hovered.name}</p>
          {hovered.description ? (
            <p className="mt-0.5 text-[10px] text-slate-400">{hovered.description}</p>
          ) : (
            <p className="mt-0.5 text-[10px] text-slate-500">Pas de description.</p>
          )}
          {hovered.category && (
            <p className="mt-1 text-[10px] text-slate-500">Catégorie : {hovered.category}</p>
          )}
        </div>
      )}
    </div>
  );
};

export default SkillPicker;

