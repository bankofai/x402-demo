import { useState, useCallback, useEffect } from 'react';
import { useWallet } from '@tronweb3/tronwallet-adapter-react-hooks';
import { WalletActionButton } from '@tronweb3/tronwallet-adapter-react-ui';
import { PaymentCard } from '../components/PaymentCard';
import { PaymentResult } from '../components/PaymentResult';
import type { PaymentRequired } from '../types';

const SERVER_URL = import.meta.env.VITE_SERVER_URL || 'http://localhost:8000';
const ENDPOINT = import.meta.env.VITE_ENDPOINT || '/protected';

interface PaymentState {
  status: 'idle' | 'loading' | 'payment_required' | 'paying' | 'success' | 'error';
  paymentRequired?: PaymentRequired;
  result?: unknown;
  error?: string;
}

export function Protected() {
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
      console.log('Response content-type:', response.headers.get('content-type'));

      if (response.status === 402) {
        const paymentRequired = await response.json() as PaymentRequired;
        console.log('402 Response:', paymentRequired);
        
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
        const contentType = response.headers.get('content-type');
        
        // Check if response is an image
        if (contentType?.startsWith('image/')) {
          const blob = await response.blob();
          const imageUrl = URL.createObjectURL(blob);
          console.log('Success - image blob URL:', imageUrl);
          setState({ status: 'success', result: { url: imageUrl, type: 'image' } });
        } else {
          // JSON response
          const result = await response.json();
          console.log('Success response:', result);
          setState({ status: 'success', result });
        }
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
    <div className="min-h-screen bg-white flex items-center justify-center px-6 py-16">
      <div className="max-w-2xl w-full">
        {/* Connect Wallet or Loading State */}
        {!connected && state.status === 'idle' && (
          <div className="text-center">
            <h1 className="text-4xl font-bold text-gray-900 mb-4">Payment Required</h1>
            <p className="text-lg text-gray-600 mb-8">
              Connect your wallet to access protected content
            </p>
            <WalletActionButton className="btn-primary text-lg inline-flex items-center gap-2" />
          </div>
        )}

        {/* Loading State */}
        {state.status === 'loading' && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
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
    </div>
  );
}
