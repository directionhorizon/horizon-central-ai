import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { GitBranch, Loader2, Plus, Search, Sparkles, Tag } from 'lucide-react';
import { skillsApi, type CreateSkillInput } from '../../api/skills';
import { describeApiError } from '../../api/errors';
import type { Skill } from '../../api/entities';

/**
 * Bibliothèque de compétences (skills).
 *
 * Catalogue central côté serveur, visible et recherchable : on pioche ici
 * quand on crée un agent, un système d'orchestration, ou pour améliorer
 * l'existant. Aucune compétence n'est imposée.
 */

const LEVEL_LABEL: Record<string, string> = {
  standard: 'Standard',
  avance: 'Avancé',
};

const LEVEL_STYLE: Record<string, string> = {
  standard: 'bg-cyan-400/10 text-cyan-200 border-cyan-400/25',
  avance: 'bg-violet-400/10 text-violet-200 border-violet-400/25',
};

const ORIGIN_LABEL: Record<string, string> = {
  github: 'GitHub',
  integrated: 'Catalogue',
  manual: 'Ajoutée',
};

const ALL = 'All';

export const SkillsLibrary = () => {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState(ALL);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [name, setName] = useState('');
  const [newCategory, setNewCategory] = useState('');
  const [description, setDescription] = useState('');
  const [level, setLevel] = useState('standard');
  const [tags, setTags] = useState('');
  const [importUrl, setImportUrl] = useState('');
  const [importing, setImporting] = useState(false);

  const refresh = useCallback(async (search: string, cat: string) => {
    setError(null);
    try {
      const params: { q?: string; category?: string } = {};
      if (search.trim()) params.q = search.trim();
      if (cat !== ALL) params.category = cat;
      const [list, cats] = await Promise.all([skillsApi.list(params), skillsApi.categories()]);
      setSkills(list.items);
      setCategories(cats.items);
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  // Recherche et filtre pilotés par le serveur (léger anti-rebond).
  useEffect(() => {
    const id = window.setTimeout(() => void refresh(query, category), 250);
    return () => window.clearTimeout(id);
  }, [query, category, refresh]);

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const input: CreateSkillInput = {
        name: name.trim(),
        category: newCategory.trim() || 'Général',
        description: description.trim(),
        level,
        tags: tags.trim(),
      };
      const created = await skillsApi.create(input);
      setNotice(`Compétence ajoutée : ${created.name}`);
      setName('');
      setNewCategory('');
      setDescription('');
      setTags('');
      setLevel('standard');
      await refresh(query, category);
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setBusy(false);
    }
  };

  const handleImport = async () => {
    if (!importUrl.trim()) return;
    setImporting(true);
    setError(null);
    setNotice(null);
    try {
      const result = await skillsApi.import({ url: importUrl.trim(), origin: 'github' });
      setNotice(`Import terminé : ${result.created} ajoutée(s), ${result.skipped} déjà présente(s).`);
      setImportUrl('');
      await refresh(query, category);
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setImporting(false);
    }
  };

  return (
    <main className="mx-auto max-w-6xl p-6">
      <header className="mb-6 flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-400/10 text-violet-200">
          <Sparkles size={18} />
        </span>
        <div>
          <h1 className="text-lg font-semibold text-slate-100">Compétences</h1>
          <p className="text-xs text-slate-500">
            Bibliothèque centrale à piocher pour un agent, un système d'orchestration, ou pour améliorer l'existant.
          </p>
        </div>
      </header>

      {(error || notice) && (
        <p
          className={`mb-4 rounded-lg border px-3 py-2 text-xs ${
            error
              ? 'border-rose-400/25 bg-rose-400/5 text-rose-200'
              : 'border-emerald-400/25 bg-emerald-400/5 text-emerald-200'
          }`}
        >
          {error ?? notice}
        </p>
      )}

      <section className="mb-5 rounded-xl border border-white/[0.08] bg-[#12151e]/80 p-4">
        <div className="relative">
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Rechercher une compétence (nom, description, mot-clé)…"
            className="h-10 w-full rounded-lg border border-white/10 bg-white/[0.04] pl-9 pr-3 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-violet-400/50"
          />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {[ALL, ...categories].map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setCategory(item)}
              className={`rounded-full border px-3 py-1 text-[11px] transition ${
                category === item
                  ? 'border-violet-400/40 bg-violet-400/15 text-violet-100'
                  : 'border-white/10 text-slate-400 hover:bg-white/5'
              }`}
            >
              {item === ALL ? 'Toutes' : item}
            </button>
          ))}
        </div>
      </section>
      <section className="mb-6">
        {loading ? (
          <p className="flex items-center justify-center gap-2 rounded-xl border border-white/[0.08] bg-[#12151e]/60 p-10 text-xs text-slate-500">
            <Loader2 size={14} className="animate-spin" /> Chargement des compétences…
          </p>
        ) : skills.length === 0 ? (
          <p className="rounded-xl border border-white/[0.08] bg-[#12151e]/60 p-10 text-center text-xs text-slate-500">
            Aucune compétence ne correspond à cette recherche.
          </p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {skills.map((skill) => (
              <article
                key={skill.id}
                className="flex flex-col rounded-xl border border-white/[0.08] bg-[#12151e]/80 p-4 transition hover:border-violet-400/30"
              >
                <div className="mb-2 flex items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold text-slate-100">{skill.name}</h3>
                  <span
                    className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium ${
                      LEVEL_STYLE[skill.level] ?? 'border-white/10 text-slate-300'
                    }`}
                  >
                    {LEVEL_LABEL[skill.level] ?? skill.level}
                  </span>
                </div>
                <div className="mb-2 flex flex-wrap items-center gap-1.5">
                  <span className="inline-flex w-fit items-center gap-1 rounded-full bg-white/5 px-2 py-0.5 text-[10px] text-slate-400">
                    <Tag size={10} /> {skill.category}
                  </span>
                  <span
                    className="inline-flex w-fit items-center gap-1 rounded-full border border-white/10 px-2 py-0.5 text-[10px] text-slate-400"
                    title={skill.source_url || skill.author || skill.origin}
                  >
                    <GitBranch size={10} /> {ORIGIN_LABEL[skill.origin] ?? skill.origin}
                  </span>
                </div>
                <p className="flex-1 text-xs leading-relaxed text-slate-400">{skill.description || '—'}</p>
                {skill.tags && (
                  <p className="mt-3 flex flex-wrap gap-1">
                    {skill.tags
                      .split(',')
                      .map((tag) => tag.trim())
                      .filter(Boolean)
                      .map((tag) => (
                        <span key={tag} className="rounded bg-white/[0.04] px-1.5 py-0.5 text-[10px] text-slate-500">
                          {tag}
                        </span>
                      ))}
                  </p>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-xl border border-white/[0.08] bg-[#12151e]/80 p-5">
        <h2 className="mb-4 flex items-center gap-2 text-base font-semibold text-slate-100">
          <Plus size={16} className="text-violet-300" /> Ajouter une compétence
        </h2>
        <form onSubmit={handleCreate} className="grid gap-3 md:grid-cols-2">
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Nom (obligatoire)"
            className="h-9 rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs text-slate-100 outline-none focus:border-violet-400/50"
          />
          <input
            value={newCategory}
            onChange={(event) => setNewCategory(event.target.value)}
            placeholder="Catégorie (ex. Recherche)"
            className="h-9 rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs text-slate-100 outline-none focus:border-violet-400/50"
          />
          <input
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Description (ce que la compétence permet de faire)"
            className="h-9 rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs text-slate-100 outline-none focus:border-violet-400/50 md:col-span-2"
          />
          <input
            value={tags}
            onChange={(event) => setTags(event.target.value)}
            placeholder="Mots-clés séparés par des virgules"
            className="h-9 rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs text-slate-100 outline-none focus:border-violet-400/50"
          />
          <select
            value={level}
            onChange={(event) => setLevel(event.target.value)}
            className="h-9 rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs text-slate-100 outline-none focus:border-violet-400/50"
          >
            <option value="standard">Standard</option>
            <option value="avance">Avancé</option>
          </select>
          <button
            type="submit"
            disabled={busy || !name.trim()}
            className="flex h-9 items-center justify-center gap-2 rounded-lg bg-violet-400/15 text-xs font-medium text-violet-200 hover:bg-violet-400/25 disabled:opacity-40 md:col-span-2"
          >
            {busy ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
            Ajouter à la bibliothèque
          </button>
        </form>
      </section>

      <section className="mt-5 rounded-xl border border-white/[0.08] bg-[#12151e]/80 p-5">
        <h2 className="mb-2 flex items-center gap-2 text-base font-semibold text-slate-100">
          <GitBranch size={16} className="text-cyan-300" /> Importer depuis GitHub
        </h2>
        <p className="mb-3 text-xs leading-5 text-slate-500">
          URL d'un fichier JSON de compétences hébergé sur GitHub (raw.githubusercontent.com).
          Seules les métadonnées sont importées — aucun code n'est exécuté, rien n'est écrasé.
        </p>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            value={importUrl}
            onChange={(event) => setImportUrl(event.target.value)}
            placeholder="https://raw.githubusercontent.com/…/skills.json"
            className="h-9 flex-1 rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs text-slate-100 outline-none focus:border-cyan-400/50"
          />
          <button
            type="button"
            onClick={() => void handleImport()}
            disabled={importing || !importUrl.trim()}
            className="flex h-9 items-center justify-center gap-2 rounded-lg bg-cyan-400/15 px-4 text-xs font-medium text-cyan-200 hover:bg-cyan-400/25 disabled:opacity-40"
          >
            {importing ? <Loader2 size={14} className="animate-spin" /> : <GitBranch size={14} />}
            Importer
          </button>
        </div>
      </section>
    </main>
  );
};

export default SkillsLibrary;
