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
  ExactPermitTronClientMechanism,
  ExactPermitEvmClientMechanism,
  NativeExactEvmClientMechanism,
  TronClientSigner,
  EvmClientSigner,
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

const TRON_PRIVATE_KEY  = process.env.TRON_PRIVATE_KEY ?? '';
const BSC_PRIVATE_KEY   = process.env.BSC_PRIVATE_KEY ?? '';
const SERVER_URL       = process.env.SERVER_URL ?? 'http://localhost:8000';
// const NETWORK          = 'tron:nile';
// const ENDPOINT         = '/protected-nile';
// const NETWORK          = 'tron:mainnet';
// const ENDPOINT         = '/protected-mainnet';
// const NETWORK          = 'eip155:56';
// const ENDPOINT         = '/protected-bsc-mainnet';
const NETWORK          = 'eip155:97';
const ENDPOINT         = '/protected-bsc-testnet';
const BSC_TESTNET_RPC  = 'https://data-seed-prebsc-1-s1.binance.org:8545/';
const BSC_MAINNET_RPC  = 'https://bsc-dataseed.binance.org/';
const TRON_GRID_HOST   = 'https://nile.trongrid.io';
// const TRON_GRID_HOST   = 'https://api.trongrid.io';

const isEvmNetwork = NETWORK.startsWith('eip155:');
const PRIVATE_KEY = isEvmNetwork ? BSC_PRIVATE_KEY : TRON_PRIVATE_KEY;

if (!PRIVATE_KEY) {
  const keyName = isEvmNetwork ? 'BSC_PRIVATE_KEY' : 'TRON_PRIVATE_KEY';
  console.error(`Error: ${keyName} not set in .env`);
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
  let signer: TronClientSigner | EvmClientSigner;
  if (isEvmNetwork) {
    const rpcUrl = NETWORK === 'eip155:56' ? BSC_MAINNET_RPC : BSC_TESTNET_RPC;
    signer = new EvmClientSigner(PRIVATE_KEY, rpcUrl);
  } else {
    const networkName = NETWORK.split(':')[1];
    const tronWeb = new TronWeb({ fullHost: TRON_GRID_HOST, privateKey: PRIVATE_KEY }) as any;
    signer = TronClientSigner.withPrivateKey(tronWeb, PRIVATE_KEY, networkName as any);
  }

  hr();
  console.log('X402 Client (TypeScript)');
  hr();
  console.log(`  Network  : ${NETWORK}`);
  console.log(`  Address  : ${signer.getAddress()}`);
  console.log(`  Permit   : ${getPaymentPermitAddress(NETWORK)}`);
  console.log(`  Resource : ${SERVER_URL}${ENDPOINT}`);
  hr();

  const x402 = new X402Client({ tokenStrategy: new DefaultTokenSelectionStrategy() });
  if (isEvmNetwork) {
    x402.register('eip155:*', new ExactPermitEvmClientMechanism(signer as EvmClientSigner));
    x402.register('eip155:*', new NativeExactEvmClientMechanism(signer as EvmClientSigner));
  } else {
    x402.register('tron:*', new ExactPermitTronClientMechanism(signer as TronClientSigner));
  }
  x402.registerPolicy(new SufficientBalancePolicy(signer));

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
