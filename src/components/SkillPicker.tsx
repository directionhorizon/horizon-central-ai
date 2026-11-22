import { useMemo, useState } from 'react';
import { Search, X } from 'lucide-react';
import type { SkillSummary } from '../api/entities';

/**
 * Sélecteur de compétences : recherche, filtre par catégorie, rattachement multiple.
 * Le composant ne décide rien : il affiche l'état reçu et remonte les intentions.
 */
interface SkillPickerProps {
  skills: SkillSummary[];
  attached: SkillSummary[];
  busy?: boolean;
  onAttach: (skillId: string) => void;
  onDetach: (skillId: string) => void;
}

export const SkillPicker = ({ skills, attached, busy = false, onAttach, onDetach }: SkillPickerProps) => {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');

  const attachedIds = useMemo(() => new Set(attached.map((skill) => skill.id)), [attached]);

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
        (skill.description ?? '').toLowerCase().includes(needle)
      );
    });
  }, [skills, query, category]);

  return (
    <div className="mt-2 rounded-xl border border-white/10 bg-white/[0.02] p-3">
      {attached.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1">
          {attached.map((skill) => (
            <span
              key={skill.id}
              className="inline-flex items-center gap-1 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-2 py-0.5 text-[11px] text-cyan-100"
            >
              {skill.name}
              <button
                type="button"
                onClick={() => onDetach(skill.id)}
                disabled={busy}
                className="text-cyan-200/70 hover:text-rose-300"
                aria-label={`Retirer ${skill.name}`}
              >
                <X size={11} />
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <label className="relative flex-1">
          <Search size={13} className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Rechercher une compétence…"
            className="w-full rounded-lg border border-white/10 bg-[#0d1320] py-1.5 pl-7 pr-2 text-xs text-slate-100 outline-none focus:border-cyan-400/40"
          />
        </label>
        <select
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          className="rounded-lg border border-white/10 bg-[#0d1320] px-2 py-1.5 text-xs text-slate-200 outline-none focus:border-cyan-400/40"
        >
          <option value="">Toutes catégories</option>
          {categories.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-2 max-h-56 overflow-auto rounded-lg border border-white/[0.06]">
        {filtered.length === 0 ? (
          <p className="px-3 py-4 text-center text-xs text-slate-500">Aucune compétence ne correspond.</p>
        ) : (
          <ul className="divide-y divide-white/[0.05]">
            {filtered.map((skill) => {
              const isAttached = attachedIds.has(skill.id);
              return (
                <li key={skill.id} className="flex items-start gap-2 px-2 py-1.5">
                  <input
                    type="checkbox"
                    checked={isAttached}
                    disabled={busy}
                    onChange={() => (isAttached ? onDetach(skill.id) : onAttach(skill.id))}
                    className="mt-0.5 h-3.5 w-3.5 accent-cyan-400"
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-xs text-slate-200">{skill.name}</span>
                    <span className="block truncate text-[10px] text-slate-500">{skill.category}</span>
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </div>
      <p className="mt-1 text-[10px] text-slate-500">
        {filtered.length} compétence(s) affichée(s) · {attached.length} rattachée(s)
      </p>
    </div>
  );
};

export default SkillPicker;
