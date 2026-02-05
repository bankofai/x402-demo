import { useState, useCallback, useMemo, useEffect } from 'react';
import { useWallet } from '@tronweb3/tronwallet-adapter-react-hooks';
import { WalletActionButton } from '@tronweb3/tronwallet-adapter-react-ui';
import type { PaymentRequired, PaymentRequirements } from '../types';
import { createPaymentPayload, encodePaymentPayload } from '../utils/payment';

interface PaymentCardProps {
  paymentRequired: PaymentRequired;
  serverUrl: string;
  endpoint: string;
  onSuccess: (result: unknown) => void;
  onError: (error: string) => void;
}

const NETWORK_NAMES: Record<string, string> = {
  'tron:mainnet': 'TRON Mainnet',
  'tron:shasta': 'TRON Shasta Testnet',
  'tron:nile': 'TRON Nile Testnet',
};

// Get supported networks from environment variable, default to 'nile'
const getSupportedNetworks = (): ('nile' | 'shasta' | 'mainnet')[] => {
  const envNetworks = import.meta.env.VITE_SUPPORTED_NETWORKS;
  if (!envNetworks) {
    return ['nile']; // Default to nile if not configured
  }
  
  const networks = envNetworks.split(',').map((n: string) => n.trim());
  const validNetworks = networks.filter((n: string) => 
    n === 'nile' || n === 'shasta' || n === 'mainnet'
  );
  
  return validNetworks.length > 0 ? validNetworks : ['nile'];
};

const SUPPORTED_NETWORKS = getSupportedNetworks();

// Helper function to get token display name from asset address
function getTokenDisplayName(assetAddress: string): string {
  // Try to extract token symbol from the payment requirements if available
  // For now, just show shortened address
  return `${assetAddress.slice(0, 6)}...${assetAddress.slice(-4)}`;
}

function detectTronNetworkFromHost(host: string | undefined): 'nile' | 'shasta' | 'mainnet' | 'unknown' {
  if (!host) return 'unknown';
  const h = host.toLowerCase();
  if (h.includes('nile')) return 'nile';
  if (h.includes('shasta')) return 'shasta';
  if (h.includes('trongrid') || h.includes('mainnet')) return 'mainnet';
  return 'unknown';
}

export function PaymentCard({
  paymentRequired,
  serverUrl,
  endpoint,
  onSuccess,
  onError,
}: PaymentCardProps) {
  const { address, connected, wallet } = useWallet();
  const [isPaying, setIsPaying] = useState(false);
  const [selectedRequirement, setSelectedRequirement] = useState<PaymentRequirements>(
    paymentRequired.accepts[0]
  );

  const [walletNetwork, setWalletNetwork] = useState<'nile' | 'shasta' | 'mainnet' | 'unknown'>('unknown');

  useEffect(() => {
    if (!connected) {
      setWalletNetwork('unknown');
      return;
    }

    const tronWeb = (window as unknown as { tronWeb?: { fullNode?: { host?: string } } }).tronWeb;
    const host = tronWeb?.fullNode?.host;
    setWalletNetwork(detectTronNetworkFromHost(host));
  }, [connected]);

  const isSupportedNetwork = SUPPORTED_NETWORKS.includes(walletNetwork as 'nile' | 'shasta' | 'mainnet');

  const networkName = useMemo(() => {
    return NETWORK_NAMES[selectedRequirement.network] || selectedRequirement.network;
  }, [selectedRequirement.network]);

  const tokenName = useMemo(() => {
    return getTokenDisplayName(selectedRequirement.asset);
  }, [selectedRequirement.asset]);

  const formattedAmount = useMemo(() => {
    const amount = BigInt(selectedRequirement.amount);
    const decimals = 6; // USDT/USDC decimals
    const divisor = BigInt(10 ** decimals);
    const whole = amount / divisor;
    const fraction = amount % divisor;
    const fractionStr = fraction.toString().padStart(decimals, '0').replace(/0+$/, '');
    return fractionStr ? `${whole}.${fractionStr}` : whole.toString();
  }, [selectedRequirement.amount]);

  const handlePay = useCallback(async () => {
    if (!connected || !address || !wallet) {
      onError('Please connect your wallet first');
      return;
    }

    if (!isSupportedNetwork) {
      onError('Unsupported network. Please switch to Nile or Shasta and reselect the wallet.');
      return;
    }

    setIsPaying(true);

    try {
      // Get wallet adapter
      if (!wallet || !wallet.adapter) {
        throw new Error('Wallet adapter not available');
      }

      console.log('Creating payment payload with wallet adapter...');

      // Create payment payload
      const paymentPayload = await createPaymentPayload(
        selectedRequirement,
        paymentRequired.extensions,
        address,
        wallet
      );

      // Encode and send payment
      const encodedPayload = encodePaymentPayload(paymentPayload);
      const url = `${serverUrl}${endpoint}`;

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'PAYMENT-SIGNATURE': encodedPayload,
        },
      });

      if (response.ok) {
        const contentType = response.headers.get('content-type');
        console.log('Payment response content-type:', contentType);
        
        // Check if response is an image
        if (contentType?.startsWith('image/')) {
          const blob = await response.blob();
          const imageUrl = URL.createObjectURL(blob);
          console.log('Payment success - image blob URL:', imageUrl);
          onSuccess({ url: imageUrl, type: 'image' });
        } else {
          // JSON response
          const result = await response.json();
          console.log('Payment success - JSON:', result);
          onSuccess(result);
        }
      } else {
        const errorText = await response.text();
        onError(`Payment failed: ${response.status} - ${errorText}`);
      }
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Payment failed');
    } finally {
      setIsPaying(false);
    }
  }, [
    connected,
    address,
    wallet,
    isSupportedNetwork,
    selectedRequirement,
    paymentRequired.extensions,
    serverUrl,
    endpoint,
    onSuccess,
    onError,
  ]);

  return (
    <div className="p-10 mx-auto max-w-lg bg-white rounded-2xl border border-gray-200">
      <h2 className="mb-3 text-3xl font-bold text-center text-gray-900">
        Payment Required
      </h2>

      <p className="mb-8 text-lg text-center text-gray-600">
        Access to protected content. To access this content, please pay{' '}
        <span className="font-semibold text-gray-900">${formattedAmount} {tokenName}</span>.
      </p>

      {/* Faucet Link */}
      <p className="mb-8 text-sm italic text-center text-gray-500">
        Need {tokenName}?{' '}
        <a
          href="https://nileex.io/join/getJoinPage"
          target="_blank"
          rel="noopener noreferrer"
          className="text-gray-900 underline hover:text-gray-700"
        >
          Get some here
        </a>
      </p>

      {/* Wallet Connection */}
      {!connected ? (
        <div className="space-y-4">
          <WalletActionButton className="w-full btn-primary" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Disconnect Button */}
          <WalletActionButton className="w-full btn-secondary" />

          {!isSupportedNetwork && (
            <div className="px-4 py-3 text-sm text-red-700 bg-red-50 rounded-xl border border-red-200">
              Unsupported network. Please switch TronLink to <b>Nile</b> or <b>Shasta</b>, then reconnect.
            </div>
          )}

          {/* Payment Details */}
          <div className="py-6 space-y-4 border-gray-200 border-y">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Wallet</span>
              <span className="font-mono text-sm text-gray-900">
                {address?.slice(0, 6)}...{address?.slice(-4)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Available balance</span>
              <span className="font-medium text-gray-900">••••• {tokenName}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Amount</span>
              <span className="font-semibold text-gray-900">
                ${formattedAmount} {tokenName}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Network</span>
              <span className="text-gray-900">{networkName}</span>
            </div>
          </div>

          {/* Pay Button */}
          <button
            onClick={handlePay}
            disabled={isPaying || !isSupportedNetwork}
            className="w-full text-lg btn-primary"
          >
            {isPaying ? 'Processing...' : 'Pay now'}
          </button>
        </div>
      )}

      {/* Payment Options (if multiple) */}
      {paymentRequired.accepts.length > 1 && (
        <div className="pt-6 mt-6 border-t border-gray-200">
          <p className="mb-3 text-sm tracking-wide text-gray-500 uppercase">Payment options</p>
          <div className="space-y-2">
            {paymentRequired.accepts.map((req, index) => (
              <button
                key={index}
                onClick={() => setSelectedRequirement(req)}
                className={`w-full text-left px-4 py-3 rounded-xl transition-all ${
                  selectedRequirement === req
                    ? 'bg-gray-900 text-white'
                    : 'bg-gray-50 hover:bg-gray-100 text-gray-900'
                }`}
              >
                {NETWORK_NAMES[req.network] || req.network} - {getTokenDisplayName(req.asset)}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
