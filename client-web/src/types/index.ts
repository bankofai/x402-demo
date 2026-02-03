/** Delivery kind type */
export type DeliveryKind = 'PAYMENT_ONLY';

/** Payment requirements from server */
export interface PaymentRequirements {
  scheme: string;
  network: string;
  amount: string;
  asset: string;
  payTo: string;
  maxTimeoutSeconds?: number;
  extra?: {
    name?: string;
    version?: string;
    fee?: {
      facilitatorId?: string;
      feeTo: string;
      feeAmount: string;
    };
  };
}

/** Payment permit context */
export interface PaymentPermitContext {
  meta: {
    kind: 'PAYMENT_ONLY';
    paymentId: string;
    nonce: string;
    validAfter: number;
    validBefore: number;
  };
  delivery: {
    receiveToken: string;
    miniReceiveAmount: string;
    tokenId: string;
  };
}

/** Payment required response (402) */
export interface PaymentRequired {
  x402Version: number;
  error?: string;
  resource?: {
    url?: string;
    description?: string;
    mimeType?: string;
  };
  accepts: PaymentRequirements[];
  extensions?: {
    paymentPermitContext?: PaymentPermitContext;
    [key: string]: unknown;
  };
}

/** Payment permit structure */
export interface PaymentPermit {
  meta: {
    kind: 'PAYMENT_ONLY';
    paymentId: string;
    nonce: string;
    validAfter: number;
    validBefore: number;
  };
  buyer: string;
  caller: string;
  payment: {
    payToken: string;
    maxPayAmount: string;
    payTo: string;
  };
  fee: {
    feeTo: string;
    feeAmount: string;
  };
  delivery: {
    receiveToken: string;
    miniReceiveAmount: string;
    tokenId: string;
  };
}

/** Payment payload sent by client */
export interface PaymentPayload {
  x402Version: number;
  resource?: {
    url?: string;
    description?: string;
    mimeType?: string;
  };
  accepted: PaymentRequirements;
  payload: {
    signature: string;
    merchantSignature?: string;
    paymentPermit: PaymentPermit;
  };
  extensions?: Record<string, unknown>;
}
