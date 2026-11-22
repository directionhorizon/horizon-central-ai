import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { AlertTriangle, CheckCircle2, CreditCard, Loader2, Plus, RefreshCw } from 'lucide-react';
import { paymentsApi } from '../../api/payments';
import type { Payment, PaymentProvider } from '../../api/payments';
import { describeApiError } from '../../api/errors';

/**
 * Page Paiements : liste des PaymentIntents enregistrés et création.
 *
 * La validation humaine est obligatoire : sans `confirm`, le serveur répond
 * `requires_human_validation` et aucun paiement n'est créé. L'interface le dit
 * explicitement et ne cache jamais cet état.
 */
const statusStyle: Record<string, string> = {
  requires_payment_method: 'bg-amber-400/10 text-amber-300',
  requires_human_validation: 'bg-amber-400/10 text-amber-300',
  succeeded: 'bg-emerald-400/10 text-emerald-300',
  processing: 'bg-cyan-400/10 text-cyan-300',
  canceled: 'bg-slate-500/10 text-slate-400',
};

const badge = (value: string) =>
  `rounded-full px-2 py-0.5 text-[10px] font-medium ${statusStyle[value] ?? 'bg-white/5 text-slate-300'}`;

const formatAmount = (amount: number, currency: string) =>
  `${(amount / 100).toFixed(2)} ${currency.toUpperCase()}`;

export const Payments = () => {
  const [items, setItems] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const [amount, setAmount] = useState('1000');
  const [currency, setCurrency] = useState('eur');
  const [detail, setDetail] = useState('');
  const [confirm, setConfirm] = useState(false);
  const [providers, setProviders] = useState<PaymentProvider[]>([]);
  const [provider, setProvider] = useState('');
  const [mode, setMode] = useState<'intent' | 'checkout'>('checkout');
  const [customer, setCustomer] = useState('');
  const [checkoutUrl, setCheckoutUrl] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const response = await paymentsApi.list();
      setItems(response.items ?? []);
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    let alive = true;
    paymentsApi
      .providers()
      .then((response) => {
        if (!alive) return;
        setProviders(response.items ?? []);
        setProvider((current) => current || response.default || '');
      })
      .catch(() => {
        /* l'absence de registre ne doit pas bloquer la page */
      });
    return () => {
      alive = false;
    };
  }, []);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const result = await paymentsApi.create({
        amount: Number(amount),
        currency,
        confirm,
        detail,
        provider: provider || undefined,
        mode,
        customer: customer || undefined,
      });
      if (result.status === 'requires_human_validation') {
        setCheckoutUrl(null);
        setNotice(
          'Validation humaine requise : aucun paiement créé. Cochez « Je confirme » puis relancez.',
        );
      } else {
        setNotice(`Paiement créé : ${result.id ?? 'identifiant inconnu'} (${result.status}).`);
        setCheckoutUrl(result.checkout_url ?? null);
        setConfirm(false);
        await load();
      }
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="hz-eyebrow">Paiements</p>
          <h1 className="mt-1 flex items-center gap-2 text-lg font-semibold text-slate-100">
            <CreditCard size={16} /> Paiements
          </h1>
          <p className="mt-1 text-xs text-slate-500">
            Création multi-fournisseurs (Stripe, PayPal, Mollie). La validation humaine est obligatoire.
          </p>
        </div>
        <button type="button" className="hz-btn hz-btn--ghost" onClick={() => void load()}>
          <RefreshCw size={12} className="mr-1 inline" /> Rafraîchir
        </button>
      </header>

      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-rose-400/20 bg-rose-400/10 p-3 text-xs text-rose-200">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {notice && (
        <div className="flex items-start gap-2 rounded-lg border border-cyan-400/20 bg-cyan-400/10 p-3 text-xs text-cyan-100">
          <CheckCircle2 size={14} className="mt-0.5 shrink-0" />
          <span>{notice}</span>
        </div>
      )}

      {checkoutUrl && (
        <div className="flex items-start gap-2 rounded-lg border border-emerald-400/20 bg-emerald-400/10 p-3 text-xs text-emerald-100">
          <CheckCircle2 size={14} className="mt-0.5 shrink-0" />
          <span>
            Lien de paiement :{' '}
            <a className="underline" href={checkoutUrl} target="_blank" rel="noreferrer">
              {checkoutUrl}
            </a>
          </span>
        </div>
      )}

      <section className="hz-panel p-4">
        <p className="hz-eyebrow">Créer un paiement</p>
        <form className="mt-3 grid gap-3 md:grid-cols-4" onSubmit={submit}>
          <label className="text-xs text-slate-400">
            Montant (centimes)
            <input
              type="number"
              min={1}
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              className="mt-1 w-full rounded-md border border-white/10 bg-black/30 px-2 py-1.5 text-xs text-slate-200 focus:border-cyan-500/40 focus:outline-none"
              required
            />
          </label>
          <label className="text-xs text-slate-400">
            Devise
            <select
              value={currency}
              onChange={(event) => setCurrency(event.target.value)}
              className="mt-1 w-full rounded-md border border-white/10 bg-black/30 px-2 py-1.5 text-xs text-slate-200 focus:border-cyan-500/40 focus:outline-none"
            >
              <option value="eur">EUR</option>
              <option value="usd">USD</option>
              <option value="gbp">GBP</option>
            </select>
          </label>
          <label className="text-xs text-slate-400">
            Fournisseur
            <select
              value={provider}
              onChange={(event) => setProvider(event.target.value)}
              className="mt-1 w-full rounded-md border border-white/10 bg-black/30 px-2 py-1.5 text-xs text-slate-200 focus:border-cyan-500/40 focus:outline-none"
            >
              <option value="">
                Par défaut ({providers.find((item) => item.default)?.label ?? 'Stripe'})
              </option>
              {providers.map((item) => (
                <option key={item.kind} value={item.kind}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-slate-400">
            Mode
            <select
              value={mode}
              onChange={(event) => setMode(event.target.value as 'intent' | 'checkout')}
              className="mt-1 w-full rounded-md border border-white/10 bg-black/30 px-2 py-1.5 text-xs text-slate-200 focus:border-cyan-500/40 focus:outline-none"
            >
              <option value="checkout">Checkout (lien hébergé)</option>
              <option value="intent">PaymentIntent (direct)</option>
            </select>
          </label>
          <label className="text-xs text-slate-400 md:col-span-2">
            Client (identifiant, facultatif)
            <input
              type="text"
              value={customer}
              onChange={(event) => setCustomer(event.target.value)}
              placeholder="cus_… ou adresse e-mail"
              className="mt-1 w-full rounded-md border border-white/10 bg-black/30 px-2 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:border-cyan-500/40 focus:outline-none"
            />
          </label>
          <label className="text-xs text-slate-400 md:col-span-2">
            Référence (facultatif)
            <input
              type="text"
              value={detail}
              onChange={(event) => setDetail(event.target.value)}
              placeholder="Ex. Commande #123"
              className="mt-1 w-full rounded-md border border-white/10 bg-black/30 px-2 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:border-cyan-500/40 focus:outline-none"
            />
          </label>
          <label className="flex items-center gap-2 text-xs text-slate-300 md:col-span-3">
            <input
              type="checkbox"
              checked={confirm}
              onChange={(event) => setConfirm(event.target.checked)}
              className="h-3.5 w-3.5 accent-cyan-500"
            />
            Je confirme créer ce paiement (obligatoire)
          </label>
          <button type="submit" className="hz-btn" disabled={busy}>
            {busy ? (
              <Loader2 size={12} className="mr-1 inline animate-spin" />
            ) : (
              <Plus size={12} className="mr-1 inline" />
            )}
            Créer
          </button>
        </form>
      </section>

      <section className="hz-panel p-0">
        <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
          <p className="hz-eyebrow">Paiements enregistrés</p>
          <span className="text-[11px] text-slate-500">{items.length}</span>
        </div>
        {loading ? (
          <p className="p-4 text-xs text-slate-500">Chargement…</p>
        ) : items.length === 0 ? (
          <p className="p-4 text-xs text-slate-500">
            Aucun paiement enregistré. Créez-en un avec la validation humaine.
          </p>
        ) : (
          <ul className="divide-y divide-white/5">
            {items.map((payment) => (
              <li key={payment.id} className="flex flex-wrap items-center gap-2 px-4 py-2.5">
                <span className="font-mono text-[11px] text-slate-300">{payment.id}</span>
                <span className="text-xs text-slate-200">
                  {formatAmount(payment.amount, payment.currency)}
                </span>
                {payment.provider && (
                  <span className="rounded-full bg-white/5 px-2 py-0.5 text-[10px] text-slate-300">
                    {payment.provider}
                  </span>
                )}
                {payment.mode && <span className="text-[10px] text-slate-500">{payment.mode}</span>}
                <span className={badge(payment.status)}>{payment.status}</span>
                {payment.checkout_url && (
                  <a
                    className="text-[11px] text-cyan-300 underline"
                    href={payment.checkout_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Lien de paiement
                  </a>
                )}
                {payment.detail && (
                  <span className="text-[11px] text-slate-500">{payment.detail}</span>
                )}
                <span className="ml-auto text-[10px] text-slate-600">{payment.created_at}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
};

export default Payments;

