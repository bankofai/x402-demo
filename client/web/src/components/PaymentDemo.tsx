import { useState, useCallback, useEffect } from 'react';
import { useWallet } from '@tronweb3/tronwallet-adapter-react-hooks';
import { WalletActionButton } from '@tronweb3/tronwallet-adapter-react-ui';
import { PaymentCard } from './PaymentCard';
import { PaymentResult } from './PaymentResult';
import type { PaymentRequired } from '../types';

const SERVER_URL = import.meta.env.VITE_SERVER_URL || 'http://localhost:8000';
const ENDPOINT = import.meta.env.VITE_ENDPOINT || '/protected';

interface PaymentState {
  status: 'idle' | 'loading' | 'payment_required' | 'paying' | 'success' | 'error';
  paymentRequired?: PaymentRequired;
  result?: unknown;
  error?: string;
}

export function PaymentDemo() {
  const { connected } = useWallet();
  const [state, setState] = useState<PaymentState>({ status: 'idle' });
  const [hasAutoFetched, setHasAutoFetched] = useState(false);

  const fetchProtectedResource = useCallback(async () => {
    setState({ status: 'loading' });

    try {
      const url = `${SERVER_URL}${ENDPOINT}`;
      console.log('Fetching:', url);
      const response = await fetch(url);
      console.log('Response status:', response.status);

      if (response.status === 402) {
        // Parse payment requirements
        const paymentRequired = await response.json() as PaymentRequired;
        console.log('402 Response:', paymentRequired);
        
        // Validate response has accepts array
        if (!paymentRequired.accepts || paymentRequired.accepts.length === 0) {
          setState({
            status: 'error',
            error: 'Invalid payment requirements: no payment options available',
          });
          return;
        }
        
        setState({
          status: 'payment_required',
          paymentRequired,
        });
      } else if (response.ok) {
        const result = await response.json();
        console.log('Success response:', result);
        setState({ status: 'success', result });
      } else {
        const errorText = await response.text();
        console.error('Error response:', response.status, errorText);
        setState({
          status: 'error',
          error: `Request failed with status ${response.status}: ${errorText}`,
        });
      }
    } catch (error) {
      console.error('Fetch error:', error);
      setState({
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  }, []);

  const handlePaymentSuccess = useCallback((result: unknown) => {
    setState({ status: 'success', result });
  }, []);

  const handlePaymentError = useCallback((error: string) => {
    setState({ status: 'error', error });
  }, []);

  const handleReset = useCallback(() => {
    setState({ status: 'idle' });
    setHasAutoFetched(false);
  }, []);

  // Auto-fetch when wallet connects
  useEffect(() => {
    if (connected && !hasAutoFetched && state.status === 'idle') {
      setHasAutoFetched(true);
      fetchProtectedResource();
    }
  }, [connected, hasAutoFetched, state.status, fetchProtectedResource]);

  return (
    <div className="space-y-8">
      {/* Connect Wallet or Loading State */}
      {!connected && state.status === 'idle' && (
        <div className="text-center">
          <WalletActionButton className="inline-flex gap-2 items-center text-lg btn-primary" />
        </div>
      )}

      {/* Loading State */}
      {state.status === 'loading' && (
        <div className="py-12 text-center">
          <div className="inline-block w-12 h-12 rounded-full border-b-2 border-gray-900 animate-spin"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      )}

      {/* Payment Required Card */}
      {state.status === 'payment_required' && state.paymentRequired && (
        <PaymentCard
          paymentRequired={state.paymentRequired}
          serverUrl={SERVER_URL}
          endpoint={ENDPOINT}
          onSuccess={handlePaymentSuccess}
          onError={handlePaymentError}
        />
      )}

      {/* Success/Error Result */}
      {(state.status === 'success' || state.status === 'error') && (
        <PaymentResult
          status={state.status}
          result={state.result}
          error={state.error}
          onReset={handleReset}
        />
      )}
    </div>
  );
}
