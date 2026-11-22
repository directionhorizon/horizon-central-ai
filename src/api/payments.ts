/** API paiements (PaymentIntents Stripe) — routes réelles /api/v1/payments. */
import { API_ROUTES } from '../config/env';
import { http } from './http';

export interface Payment {
  id: string;
  amount: number;
  currency: string;
  status: string;
  detail: string;
  created_at: string;
}

export interface PaymentListResponse {
  items: Payment[];
}

export interface CreatePaymentInput {
  amount: number;
  currency?: string;
  confirm?: boolean;
  detail?: string;
}

export interface PaymentResult {
  status: string;
  id?: string;
  amount?: number;
  currency?: string;
  detail?: string;
}

export const paymentsApi = {
  list: (): Promise<PaymentListResponse> =>
    http.requestWithRetry<PaymentListResponse>(API_ROUTES.payments),
  create: (input: CreatePaymentInput): Promise<PaymentResult> =>
    http.request<PaymentResult>(API_ROUTES.payments, { method: 'POST', body: input }),
  get: (id: string): Promise<Payment> =>
    http.requestWithRetry<Payment>(API_ROUTES.payment(id)),
} as const;
