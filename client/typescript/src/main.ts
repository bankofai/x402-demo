/**
 * X402 TRON Demo - TypeScript Client
 *
 * Demonstrates the x402 payment protocol: request a paid resource,
 * automatically sign & settle on-chain, then consume the response.
 */

import { config } from 'dotenv';
import { dirname, join, resolve } from 'path';
import { fileURLToPath } from 'url';
import { writeFileSync } from 'fs';
import { tmpdir } from 'os';
import { TronWeb } from 'tronweb';
import {
  X402Client,
  X402FetchClient,
  ExactTronClientMechanism,
  TronClientSigner,
  DefaultTokenSelectionStrategy,
  SufficientBalancePolicy,
  decodePaymentPayload,
  getPaymentPermitAddress,
  type SettleResponse,
} from '@bankofai/x402-tron';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, '../../../.env') });

const TRON_PRIVATE_KEY = process.env.TRON_PRIVATE_KEY ?? '';
const SERVER_URL       = process.env.SERVER_URL ?? 'http://localhost:8000';
const NETWORK          = 'tron:nile';
const ENDPOINT         = '/protected-nile';
const TRON_GRID_HOST   = 'https://nile.trongrid.io';
// const NETWORK          = 'tron:mainnet';
// const ENDPOINT         = '/protected-mainnet';
// const TRON_GRID_HOST   = 'https://api.trongrid.io';

if (!TRON_PRIVATE_KEY) {
  console.error('Error: TRON_PRIVATE_KEY not set in .env');
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
  const networkName = NETWORK.split(':')[1];
  const tronWeb = new TronWeb({ fullHost: TRON_GRID_HOST, privateKey: TRON_PRIVATE_KEY }) as any;
  const signer  = TronClientSigner.withPrivateKey(tronWeb, TRON_PRIVATE_KEY, networkName as any);

  hr();
  console.log('X402 Client (TypeScript)');
  hr();
  console.log(`  Network  : ${NETWORK}`);
  console.log(`  Address  : ${signer.getAddress()}`);
  console.log(`  Permit   : ${getPaymentPermitAddress(NETWORK)}`);
  console.log(`  Resource : ${SERVER_URL}${ENDPOINT}`);
  hr();

  const x402 = new X402Client({ tokenStrategy: new DefaultTokenSelectionStrategy() })
    .register('tron:*', new ExactTronClientMechanism(signer))
    .registerPolicy(new SufficientBalancePolicy(signer));

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
