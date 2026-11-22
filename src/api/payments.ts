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
  mode?: 'intent' | 'checkout';
  customer?: string;
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
}

export const paymentsApi = {
  list: (): Promise<PaymentListResponse> =>
    http.requestWithRetry<PaymentListResponse>(API_ROUTES.payments),
  providers: (): Promise<PaymentProvidersResponse> =>
    http.requestWithRetry<PaymentProvidersResponse>(API_ROUTES.paymentProviders),
  create: (input: CreatePaymentInput): Promise<PaymentResult> =>
    http.request<PaymentResult>(API_ROUTES.payments, { method: 'POST', body: input }),
  get: (id: string): Promise<Payment> =>
    http.requestWithRetry<Payment>(API_ROUTES.payment(id)),
} as const;

