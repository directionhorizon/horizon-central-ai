/** API paiements — routes réelles /api/v1/payments (registre multi-fournisseurs). */
import { API_ROUTES } from '../config/env';
import { http } from './http';

export interface Payment {
  id: string;
  amount: number;
  currency: string;
  status: string;
  detail: string;
  provider?: string;
  mode?: string;
  customer?: string;
  checkout_url?: string;
  created_at: string;
}

export interface PaymentListResponse {
  items: Payment[];
}

export interface PaymentProvider {
  kind: string;
  label: string;
  capabilities: string[];
  env_vars: string[];
  default: boolean;
}

export interface PaymentProvidersResponse {
  items: PaymentProvider[];
  default: string;
}

export interface CreatePaymentInput {
  amount: number;
  currency?: string;
  confirm?: boolean;
  detail?: string;
  provider?: string;
  mode?: 'intent' | 'checkout' | 'setup';
  customer?: string;
}

export interface PaymentEvent {
  id: string;
  type: string;
  payment_id: string;
  created_at: string;
}

export interface PaymentEventsResponse {
  items: PaymentEvent[];
}

export interface RefundInput {
  amount?: number;
  reason?: string;
}

export interface PaymentResult {
  status: string;
  id?: string;
  amount?: number;
  currency?: string;
  detail?: string;
  provider?: string;
  mode?: string;
  customer?: string;
  checkout_url?: string;
  replayed?: boolean;
}

export const paymentsApi = {
  list: (): Promise<PaymentListResponse> =>
    http.requestWithRetry<PaymentListResponse>(API_ROUTES.payments),
  providers: (): Promise<PaymentProvidersResponse> =>
    http.requestWithRetry<PaymentProvidersResponse>(API_ROUTES.paymentProviders),
  create: (input: CreatePaymentInput, idempotencyKey?: string): Promise<PaymentResult> =>
    http.request<PaymentResult>(API_ROUTES.payments, {
      method: 'POST',
      body: input,
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
    }),
  get: (id: string): Promise<Payment> =>
    http.requestWithRetry<Payment>(API_ROUTES.payment(id)),
  refund: (id: string, input: RefundInput = {}): Promise<PaymentResult> =>
    http.request<PaymentResult>(API_ROUTES.paymentRefund(id), {
      method: 'POST',
      body: input,
    }),
  events: (): Promise<PaymentEventsResponse> =>
    http.requestWithRetry<PaymentEventsResponse>(API_ROUTES.paymentEvents),
} as const;

