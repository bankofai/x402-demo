import type { PaymentRequirements, PaymentPayload, PaymentPermit, PaymentPermitContext } from '../types';
import {
  decodePaymentPayload as sdkDecodePaymentPayload,
  encodePaymentPayload as sdkEncodePaymentPayload,
  getChainId,
  getPaymentPermitAddress,
  toEvmHex,
} from '@open-aibank/x402-tron';

/** Delivery kind type */
type DeliveryKind = 'PAYMENT_ONLY';

/** TronWeb instance type (injected by TronLink) */
interface TronWebInstance {
  trx: {
    signTypedData?: (
      domain: Record<string, unknown>,
      types: Record<string, unknown>,
      value: Record<string, unknown>
    ) => Promise<string>;
    _signTypedData?: (
      domain: Record<string, unknown>,
      types: Record<string, unknown>,
      value: Record<string, unknown>
    ) => Promise<string>;
  };
  address: {
    toHex(address: string): string;
    fromHex(address: string): string;
  };
  defaultAddress: {
    base58: string;
  };
  contract(): {
    at(address: string): Promise<TRC20Contract>;
  };
}

/** TRC20 Contract interface */
interface TRC20Contract {
  allowance(owner: string, spender: string): {
    call(): Promise<{ toString(): string }>;
  };
  approve(spender: string, amount: string): {
    send(): Promise<string>;
  };
  balanceOf(address: string): {
    call(): Promise<{ toString(): string }>;
  };
}

/** Kind mapping for EIP-712 (string to numeric) */
const KIND_MAP: Record<DeliveryKind, number> = {
  PAYMENT_ONLY: 0,
};

/** EIP-712 domain for TRON payment permit */
// Note: NO version field! Based on contract's EIP712Domain definition
const PAYMENT_PERMIT_DOMAIN = {
  name: 'PaymentPermit',
};

/** EIP-712 types for payment permit */
// Primary type is "PaymentPermitDetails" to match the contract's typehash
const PAYMENT_PERMIT_TYPES = {
  PermitMeta: [
    { name: 'kind', type: 'uint8' },
    { name: 'paymentId', type: 'bytes16' },
    { name: 'nonce', type: 'uint256' },
    { name: 'validAfter', type: 'uint256' },
    { name: 'validBefore', type: 'uint256' },
  ],
  Payment: [
    { name: 'payToken', type: 'address' },
    { name: 'maxPayAmount', type: 'uint256' },
    { name: 'payTo', type: 'address' },
  ],
  Fee: [
    { name: 'feeTo', type: 'address' },
    { name: 'feeAmount', type: 'uint256' },
  ],
  Delivery: [
    { name: 'receiveToken', type: 'address' },
    { name: 'miniReceiveAmount', type: 'uint256' },
    { name: 'tokenId', type: 'uint256' },
  ],
  PaymentPermitDetails: [
    { name: 'meta', type: 'PermitMeta' },
    { name: 'buyer', type: 'address' },
    { name: 'caller', type: 'address' },
    { name: 'payment', type: 'Payment' },
    { name: 'fee', type: 'Fee' },
    { name: 'delivery', type: 'Delivery' },
  ],
};

/** Generate a random payment ID */
function generatePaymentId(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return '0x' + Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('');
}

/** Generate a random nonce */
function generateNonce(): string {
  return Math.floor(Math.random() * 1000000000).toString();
}

/**
 * Ensure sufficient allowance for PaymentPermit contract
 * If allowance is insufficient, trigger approval transaction
 */
async function ensureAllowance(
  tronWeb: TronWebInstance,
  tokenAddress: string,
  spenderAddress: string,
  requiredAmount: string
): Promise<void> {
  console.log('[ALLOWANCE] Checking allowance...');
  console.log('[ALLOWANCE] Token:', tokenAddress);
  console.log('[ALLOWANCE] Spender:', spenderAddress);
  console.log('[ALLOWANCE] Required amount:', requiredAmount);

  try {
    const tokenContract = await tronWeb.contract().at(tokenAddress);
    const ownerAddress = tronWeb.defaultAddress.base58;

    // Check current allowance
    const allowanceResult = await tokenContract.allowance(ownerAddress, spenderAddress).call();
    const currentAllowance = BigInt(allowanceResult.toString());
    const required = BigInt(requiredAmount);

    console.log('[ALLOWANCE] Current allowance:', currentAllowance.toString());
    console.log('[ALLOWANCE] Required:', required.toString());

    if (currentAllowance >= required) {
      console.log('[ALLOWANCE] Sufficient allowance, no approval needed');
      return;
    }

    // Insufficient allowance, request approval
    console.log('[ALLOWANCE] Insufficient allowance, requesting approval...');
    
    // Approve a large amount to avoid frequent approvals (e.g., 1 billion tokens)
    const approveAmount = (required * BigInt(100)).toString(); // 100x the required amount
    console.log('[ALLOWANCE] Approving amount:', approveAmount);

    const txId = await tokenContract.approve(spenderAddress, approveAmount).send();
    console.log('[ALLOWANCE] Approval transaction sent:', txId);
    console.log('[ALLOWANCE] Waiting for confirmation...');

    // Wait a bit for transaction to be confirmed
    await new Promise(resolve => setTimeout(resolve, 3000));

    // Verify approval was successful
    const newAllowanceResult = await tokenContract.allowance(ownerAddress, spenderAddress).call();
    const newAllowance = BigInt(newAllowanceResult.toString());
    console.log('[ALLOWANCE] New allowance:', newAllowance.toString());

    if (newAllowance < required) {
      throw new Error('Approval transaction completed but allowance is still insufficient');
    }

    console.log('[ALLOWANCE] Approval successful!');
  } catch (error) {
    console.error('[ALLOWANCE] Error:', error);
    throw new Error('Failed to ensure allowance: ' + (error instanceof Error ? error.message : 'Unknown error'));
  }
}

/** Create payment payload for x402 protocol */
export async function createPaymentPayload(
  requirements: PaymentRequirements,
  extensions: { paymentPermitContext?: PaymentPermitContext } | undefined,
  buyerAddress: string,
  _wallet: unknown // Not used - we use window.tronWeb directly
): Promise<PaymentPayload> {
  const now = Math.floor(Date.now() / 1000);
  const validBefore = now + (requirements.maxTimeoutSeconds || 300);

  // Use context from server or generate defaults
  const context = extensions?.paymentPermitContext;
  const meta = {
    kind: context?.meta.kind || 'PAYMENT_ONLY' as const,
    paymentId: context?.meta.paymentId || generatePaymentId(),
    nonce: context?.meta.nonce || generateNonce(),
    validAfter: context?.meta.validAfter || now,
    validBefore: context?.meta.validBefore || validBefore,
  };

  const delivery = {
    receiveToken: context?.delivery.receiveToken || '0x0000000000000000000000000000000000000000',
    miniReceiveAmount: context?.delivery.miniReceiveAmount || '0',
    tokenId: context?.delivery.tokenId || '0',
  };

  const feeTo = requirements.extra?.fee?.feeTo || '0x0000000000000000000000000000000000000000';
  const feeAmount = requirements.extra?.fee?.feeAmount || '0';

  const permit: PaymentPermit = {
    meta,
    buyer: buyerAddress,
    caller: feeTo,
    payment: {
      payToken: requirements.asset,
      maxPayAmount: requirements.amount,
      payTo: requirements.payTo,
    },
    fee: {
      feeTo,
      feeAmount,
    },
    delivery,
  };

  // Sign using TronWeb's signTypedData (TIP-712)
  try {
    console.log('=== Creating Payment Payload ===');
    console.log('Requirements:', JSON.stringify(requirements, null, 2));
    console.log('Extensions:', JSON.stringify(extensions, null, 2));
    console.log('Buyer address:', buyerAddress);
    console.log('Permit (before conversion):', JSON.stringify(permit, null, 2));

    // Get TronWeb from window (injected by TronLink)
    const tronWeb = (window as unknown as { tronWeb?: TronWebInstance }).tronWeb;
    if (!tronWeb) {
      throw new Error('TronWeb not found. Please install TronLink wallet.');
    }
    console.log('TronWeb found:', !!tronWeb);

    // Get PaymentPermit contract address from SDK config
    const permitContractAddress = getPaymentPermitAddress(requirements.network);

    // Calculate total required amount (payment + fee)
    const totalAmount = (BigInt(requirements.amount) + BigInt(feeAmount)).toString();
    console.log('[PAYMENT] Total amount needed:', totalAmount);

    // Ensure sufficient allowance before signing
    await ensureAllowance(
      tronWeb,
      requirements.asset,
      permitContractAddress,
      totalAmount
    );

    // Check for signTypedData support
    const signTypedData = tronWeb.trx.signTypedData || tronWeb.trx._signTypedData;
    if (!signTypedData) {
      throw new Error('TronWeb does not support signTypedData. Please upgrade TronLink.');
    }
    console.log('signTypedData method available');

    console.log('=== Converting addresses ===');
    // Convert permit to EIP-712 compatible format:
    // 1. kind: string -> uint8
    // 2. All addresses: TRON Base58 -> EVM hex (0x...)
    const permitForSigning = {
      meta: {
        kind: KIND_MAP[permit.meta.kind],
        paymentId: permit.meta.paymentId,
        nonce: permit.meta.nonce,
        validAfter: permit.meta.validAfter,
        validBefore: permit.meta.validBefore,
      },
      buyer: toEvmHex(permit.buyer),
      caller: toEvmHex(permit.caller),
      payment: {
        payToken: toEvmHex(permit.payment.payToken),
        maxPayAmount: permit.payment.maxPayAmount,
        payTo: toEvmHex(permit.payment.payTo),
      },
      fee: {
        feeTo: toEvmHex(permit.fee.feeTo),
        feeAmount: permit.fee.feeAmount,
      },
      delivery: {
        receiveToken: toEvmHex(permit.delivery.receiveToken),
        miniReceiveAmount: permit.delivery.miniReceiveAmount,
        tokenId: permit.delivery.tokenId,
      },
    };

    // Build domain with chainId and verifyingContract
    // Extract chainId from network string (e.g., "tron:nile" or "tron:3448148188")
    // TronLink requires chainId as hex string
    console.log('[CHAIN] requirements.network:', requirements.network);
    
    const chainIdDecimal = getChainId(requirements.network);
    const chainId = '0x' + chainIdDecimal.toString(16);
    console.log('[CHAIN] Final chainId (hex):', chainId, 'decimal:', chainIdDecimal);

    // Use the permitContractAddress we already got for allowance check
    const verifyingContract = permitContractAddress ? toEvmHex(permitContractAddress) : '0x' + '0'.repeat(40);

    const domain = {
      name: PAYMENT_PERMIT_DOMAIN.name,
      chainId,
      verifyingContract,
    };

    console.log('=== Signing Data ===');
    console.log('Domain:', JSON.stringify(domain, null, 2));
    console.log('Types:', JSON.stringify(PAYMENT_PERMIT_TYPES, null, 2));
    console.log('Permit for signing:', JSON.stringify(permitForSigning, null, 2));

    // Call TronWeb's signTypedData (TIP-712)
    console.log('Calling signTypedData...');
    const signature = await signTypedData.call(
      tronWeb.trx,
      domain,
      PAYMENT_PERMIT_TYPES,
      permitForSigning
    );

    console.log('=== Signature Result ===');
    console.log('Signature:', signature);

    const payload = {
      x402Version: 2,
      resource: { url: '' },
      accepted: requirements,
      payload: {
        signature,
        paymentPermit: permit,
      },
      extensions: {},
    };

    console.log('=== Final Payload ===');
    console.log('Payload:', JSON.stringify(payload, null, 2));

    return payload;
  } catch (error) {
    console.error('Signature error:', error);
    throw new Error('Failed to sign payment permit: ' + (error instanceof Error ? error.message : 'Unknown error'));
  }
}

/** Encode payment payload to base64 */
export function encodePaymentPayload(payload: PaymentPayload): string {
  return sdkEncodePaymentPayload(payload);
}

/** Decode payment payload from base64 */
export function decodePaymentPayload<T>(encoded: string): T {
  return sdkDecodePaymentPayload<T>(encoded);
}
