import { useMemo } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { WalletProvider } from '@tronweb3/tronwallet-adapter-react-hooks';
import { WalletModalProvider } from '@tronweb3/tronwallet-adapter-react-ui';
import { TronLinkAdapter } from '@tronweb3/tronwallet-adapters';
import { WalletError } from '@tronweb3/tronwallet-abstract-adapter';
import '@tronweb3/tronwallet-adapter-react-ui/style.css';

import { Home } from './pages/Home';
import { Protected } from './pages/Protected';

function App() {
  const adapters = useMemo(() => [new TronLinkAdapter()], []);

  const onError = (error: WalletError) => {
    console.error('Wallet error:', error);
  };

  return (
    <BrowserRouter>
      <WalletProvider
        onError={onError}
        adapters={adapters}
        disableAutoConnectOnLoad={true}
      >
        <WalletModalProvider>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/protected" element={<Protected />} />
          </Routes>
        </WalletModalProvider>
      </WalletProvider>
    </BrowserRouter>
  );
}

export default App;
