import {
  connectorsForWallets,
  getDefaultWallets,
  lightTheme,
} from '@rainbow-me/rainbowkit';
import { configureChains, createConfig } from 'wagmi';
import { mainnet, sepolia } from 'wagmi/chains';
import { publicProvider } from 'wagmi/providers/public';

const configured = configureChains([mainnet, sepolia], [publicProvider()]);
export const chains = configured.chains;
export const publicClient = configured.publicClient;

const projectId = process.env.REACT_APP_WALLET_CONNECT_PROJECT_ID || 'demo-project-id';

const { wallets } = getDefaultWallets({
  appName: 'AgentVault Dashboard',
  projectId,
  chains,
});

const connectors = connectorsForWallets(wallets);

export const wagmiConfig = createConfig({
  autoConnect: true,
  connectors,
  publicClient,
});

export const rainbowKitTheme = lightTheme({
  accentColor: '#0ea5e9',
  accentColorForeground: 'white',
  borderRadius: 'medium',
  fontStack: 'system',
});

export const CONTRACT_ADDRESSES = {
  AGENT_VAULT_TOKEN: {
    [mainnet.id]: '0x0000000000000000000000000000000000000000',
    [sepolia.id]: '0x0000000000000000000000000000000000000000',
  },
};

export const SUPPORTED_CHAINS = [mainnet, sepolia];
