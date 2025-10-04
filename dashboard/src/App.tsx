import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WagmiConfig } from 'wagmi';
import { RainbowKitProvider } from '@rainbow-me/rainbowkit';
import { wagmiConfig, rainbowKitTheme, chains } from './config/web3';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Agents from './pages/Agents';
import Usage from './pages/Usage';
import Billing from './pages/Billing';
import Wallet from './pages/Wallet';
import Settings from './pages/Settings';
import Airdrop from './pages/Airdrop';
import Strategies from './pages/Strategies';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <WagmiConfig config={wagmiConfig}>
      <RainbowKitProvider theme={rainbowKitTheme} modalSize="compact" chains={chains}>
        <QueryClientProvider client={queryClient}>
          <Router>
            <div className="min-h-screen bg-gray-50">
              <Layout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/agents" element={<Agents />} />
                  <Route path="/usage" element={<Usage />} />
                  <Route path="/strategies" element={<Strategies />} />
                  <Route path="/billing" element={<Billing />} />
                  <Route path="/wallet" element={<Wallet />} />
                  <Route path="/airdrop" element={<Airdrop />} />
                  <Route path="/settings" element={<Settings />} />
                </Routes>
              </Layout>
            </div>
          </Router>
        </QueryClientProvider>
      </RainbowKitProvider>
    </WagmiConfig>
  );
}

export default App;
