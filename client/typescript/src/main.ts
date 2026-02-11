/**
 * X402 Demo - TypeScript Client (Multi-Network)
 *
 * Registers BOTH TRON and EVM mechanisms by default so the client can
 * handle 402 responses from any supported chain.  The server decides
 * which network(s) to accept; the SDK picks the best affordable option.
 */

import { config } from 'dotenv';
import { dirname, join, resolve } from 'path';
import { fileURLToPath } from 'url';
import { writeFileSync } from 'fs';
import { tmpdir } from 'os';
import {
  X402Client,
  X402FetchClient,
  ExactPermitTronClientMechanism,
  ExactPermitEvmClientMechanism,
  ExactEvmClientMechanism,
  TronClientSigner,
  EvmClientSigner,
  DefaultTokenSelectionStrategy,
  SufficientBalancePolicy,
  decodePaymentPayload,
  type SettleResponse,
} from '@bankofai/x402';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, '../../../.env') });

const TRON_PRIVATE_KEY = process.env.TRON_PRIVATE_KEY ?? '';
const BSC_PRIVATE_KEY  = process.env.BSC_PRIVATE_KEY ?? '';
const SERVER_URL       = process.env.SERVER_URL ?? 'http://localhost:8000';
// For TRON mainnet, set TRON_GRID_API_KEY in .env — the signer reads it from env automatically.

// Change ENDPOINT to target a different server resource.
// The server may return accepts[] spanning multiple networks.
// const ENDPOINT         = '/protected-nile';
// const ENDPOINT         = '/protected-mainnet';
// const ENDPOINT         = '/protected-bsc-mainnet';
const ENDPOINT         = '/protected-bsc-testnet';


if (!TRON_PRIVATE_KEY) {
  console.error('Error: TRON_PRIVATE_KEY not set in .env');
  process.exit(1);
}
if (!BSC_PRIVATE_KEY) {
  console.error('Error: BSC_PRIVATE_KEY not set in .env');
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const hr = () => console.log('─'.repeat(72));

function printSettlement(header: string): void {
  const settle = decodePaymentPayload<SettleResponse>(header);
  console.log('Settlement:');
  console.log(`  success : ${settle.success}`);
  console.log(`  network : ${settle.network}`);
  console.log(`  tx      : ${settle.transaction}`);
  if (settle.errorReason) console.log(`  error   : ${settle.errorReason}`);
}

async function saveImage(response: Response): Promise<string> {
  const ct = response.headers.get('content-type') ?? '';
  const ext = ct.includes('jpeg') || ct.includes('jpg') ? 'jpg'
            : ct.includes('webp') ? 'webp' : 'png';
  const buf = Buffer.from(await response.arrayBuffer());
  const path = join(tmpdir(), `x402_${Date.now()}.${ext}`);
  writeFileSync(path, buf);
  return path;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  // --- Create signers for every chain family ---
  const tronSigner = new TronClientSigner(TRON_PRIVATE_KEY);
  const evmSigner  = new EvmClientSigner(BSC_PRIVATE_KEY);

  hr();
  console.log('X402 Client (TypeScript · Multi-Network)');
  hr();
  console.log(`  TRON Address : ${tronSigner.getAddress()}`);
  console.log(`  EVM  Address : ${evmSigner.getAddress()}`);
  console.log(`  Resource     : ${SERVER_URL}${ENDPOINT}`);
  hr();

  // --- Register mechanisms for ALL networks ---
  const x402 = new X402Client({ tokenStrategy: new DefaultTokenSelectionStrategy() });
  x402.register('tron:*',   new ExactPermitTronClientMechanism(tronSigner));
  x402.register('eip155:*', new ExactPermitEvmClientMechanism(evmSigner));
  x402.register('eip155:*', new ExactEvmClientMechanism(evmSigner));

  // Balance policy: auto-resolves signers from registered mechanisms
  x402.registerPolicy(SufficientBalancePolicy);

  const client = new X402FetchClient(x402);

  const url = `${SERVER_URL}${ENDPOINT}`;
  console.log(`\nGET ${url} …`);

  const res = await client.get(url);
  console.log(`\n✅ ${res.status} ${res.statusText}`);

  const paymentHeader = res.headers.get('payment-response');
  if (paymentHeader) printSettlement(paymentHeader);

  const ct = res.headers.get('content-type') ?? '';
  if (ct.includes('application/json')) {
    console.log(`\n${JSON.stringify(await res.json(), null, 2)}`);
  } else if (ct.includes('image/')) {
    const path = await saveImage(res);
    console.log(`\nImage saved → ${path}`);
  } else {
    const text = await res.text();
    console.log(`\n${text.slice(0, 500)}`);
  }
}

main().catch((err) => {
  console.error('\n❌', err instanceof Error ? err.message : err);
  process.exit(1);
});
