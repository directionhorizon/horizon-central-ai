import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { AlertTriangle, Archive, CheckCircle2, Database, FileText, Loader2, Plus, RefreshCw, Search } from 'lucide-react';
import { documentsApi } from '../../api/documents';
import { projectsApi } from '../../api/projects';
import { describeApiError } from '../../api/errors';
import type { KnowledgeDocument, ProjectSummary } from '../../api/entities';

export const KnowledgeMemoryLive = () => {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [projectId, setProjectId] = useState('');
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<KnowledgeDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [tags, setTags] = useState('');
  const [source, setSource] = useState('');

  const load = useCallback(async () => {
    setError(null);
    try {
      const [documentsResponse, projectsResponse] = await Promise.all([
        documentsApi.list({ projectId: projectId || undefined, query: query || undefined }),
        projectsApi.list(),
      ]);
      setDocuments(documentsResponse.items);
      setProjects(projectsResponse.items);
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setLoading(false);
    }
  }, [projectId, query]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!title.trim()) return;
    setBusy('create');
    setError(null);
    setNotice(null);
    try {
      const created = await documentsApi.create({
        title: title.trim(),
        content,
        project_id: projectId || null,
        tags: tags.trim(),
        source: source.trim(),
      });
      setTitle('');
      setContent('');
      setTags('');
      setSource('');
      setSelected(created);
      setNotice('Document enregistré dans la mémoire centrale.');
      await load();
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setBusy(null);
    }
  };

  const handleArchive = async (document: KnowledgeDocument) => {
    setBusy(document.id);
    setError(null);
    setNotice(null);
    try {
      await documentsApi.archive(document.id);
      setSelected(null);
      setNotice('Document archivé (aucune suppression physique).');
      await load();
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0b10] text-slate-100">
      <div className="mx-auto min-h-screen w-full max-w-[1500px] px-5 pb-12 pt-8 sm:px-8 lg:px-10">
        <header className="mb-7 border-b border-white/[0.07] pb-6">
          <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-cyan-400">
            <Database size={14} /> Mémoire centrale
          </div>
          <h1 className="text-3xl font-semibold tracking-[-0.03em] text-white">Knowledge &amp; Memory</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
            Documents rattachés aux projets, stockés dans la base locale. Recherche par mots-clés, archivage logique, aucune suppression silencieuse.
          </p>
        </header>

        {error && (
          <div className="mb-5 flex items-start gap-3 rounded-xl border border-rose-400/25 bg-rose-400/[0.07] p-4">
            <AlertTriangle size={17} className="mt-0.5 shrink-0 text-rose-300" />
            <p className="text-xs leading-5 text-rose-100">{error}</p>
          </div>
        )}
        {notice && (
          <div className="mb-5 flex items-start gap-3 rounded-xl border border-cyan-400/25 bg-cyan-400/[0.06] p-4">
            <CheckCircle2 size={17} className="mt-0.5 shrink-0 text-cyan-300" />
            <p className="text-xs leading-5 text-cyan-100">{notice}</p>
          </div>
        )}

        <div className="grid gap-5 lg:grid-cols-[1fr_400px]">
          <section className="rounded-xl border border-white/[0.08] bg-[#12151e]/80 p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-white">Documents ({documents.length})</h2>
                <p className="mt-1 text-xs text-slate-500">Mémoire centrale · lecture et recherche</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <label className="relative">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Rechercher"
                    className="h-9 w-44 rounded-lg border border-white/10 bg-white/[0.04] pl-9 pr-3 text-xs outline-none focus:border-cyan-400/50"
                  />
                </label>
                <select
                  value={projectId}
                  onChange={(event) => setProjectId(event.target.value)}
                  className="h-9 rounded-lg border border-white/10 bg-[#171a24] px-3 text-xs text-slate-300"
                >
                  <option value="">Tous les projets</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>{project.name}</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => void load()}
                  className="flex h-9 items-center gap-2 rounded-lg border border-white/10 px-3 text-[11px] text-slate-300 hover:bg-white/5"
                >
                  <RefreshCw size={13} className={loading ? 'animate-spin' : ''} /> Actualiser
                </button>
              </div>
            </div>
            <div className="space-y-2">
              {documents.map((document) => (
                <article key={document.id} className="rounded-lg border border-white/[0.07] bg-black/20 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-white">{document.title}</p>
                      <p className="mt-1 text-[11px] text-slate-500">
                        {document.project_id ?? 'sans projet'} · {document.tags || 'sans tag'} · {document.source || 'source non renseignée'}
                      </p>
                      <p className="mt-1 line-clamp-2 text-[11px] leading-5 text-slate-400">{document.content || '—'}</p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => setSelected(document)}
                        className="rounded-md border border-white/10 px-3 py-1.5 text-[11px] text-slate-300 hover:bg-white/5"
                      >
                        Ouvrir
                      </button>
                      <button
                        type="button"
                        disabled={busy === document.id}
                        onClick={() => void handleArchive(document)}
                        className="flex items-center gap-1 rounded-md border border-white/10 px-3 py-1.5 text-[11px] text-slate-400 hover:bg-white/5 disabled:opacity-40"
                      >
                        <Archive size={12} /> Archiver
                      </button>
                    </div>
                  </div>
                  <p className="mt-2 text-[10px] text-slate-600">Dernière mise à jour : {document.updated_at}</p>
                </article>
              ))}
              {documents.length === 0 && !loading && (
                <p className="p-8 text-center text-xs text-slate-500">
                  Aucun document en mémoire. Créez-en un avec le formulaire à droite.
                </p>
              )}
            </div>
          </section>

          <aside className="space-y-5">
            <section className="rounded-xl border border-white/[0.08] bg-[#12151e]/80 p-5">
              <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-white">
                <Plus size={15} className="text-cyan-300" /> Nouveau document
              </h2>
              <form onSubmit={handleCreate} className="space-y-2">
                <input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="Titre"
                  className="h-9 w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs outline-none focus:border-cyan-400/50"
                />
                <textarea
                  value={content}
                  onChange={(event) => setContent(event.target.value)}
                  placeholder="Contenu"
                  rows={6}
                  className="w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-xs outline-none focus:border-cyan-400/50"
                />
                <input
                  value={tags}
                  onChange={(event) => setTags(event.target.value)}
                  placeholder="Tags séparés par des virgules"
                  className="h-9 w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs outline-none focus:border-cyan-400/50"
                />
                <input
                  value={source}
                  onChange={(event) => setSource(event.target.value)}
                  placeholder="Source (fichier, URL, note)"
                  className="h-9 w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs outline-none focus:border-cyan-400/50"
                />
                <button
                  type="submit"
                  disabled={busy === 'create' || !title.trim()}
                  className="flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-cyan-400/15 text-xs font-medium text-cyan-200 hover:bg-cyan-400/25 disabled:opacity-40"
                >
                  {busy === 'create' ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                  Enregistrer
                </button>
              </form>
              <p className="mt-3 text-[10px] leading-4 text-slate-600">
                Le document est rattaché au projet sélectionné dans la liste. Aucun contenu n'est écrasé : l'archivage conserve l'historique.
              </p>
            </section>

            {selected && (
              <section className="rounded-xl border border-white/[0.08] bg-[#12151e]/80 p-5">
                <h2 className="mb-2 flex items-center gap-2 text-base font-semibold text-white">
                  <FileText size={15} className="text-cyan-300" /> {selected.title}
                </h2>
                <p className="text-[10px] text-slate-600">{selected.updated_at} · {selected.status}</p>
                <p className="mt-3 whitespace-pre-wrap text-xs leading-5 text-slate-300">{selected.content || '—'}</p>
                <button
                  type="button"
                  onClick={() => setSelected(null)}
                  className="mt-3 text-[11px] text-cyan-300 hover:underline"
                >
                  Fermer
                </button>
              </section>
            )}
          </aside>
        </div>
      </div>
    </div>
  );
};
