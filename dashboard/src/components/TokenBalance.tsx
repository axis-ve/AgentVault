import React from 'react';
import { useAccount, useBalance } from 'wagmi';
import { formatEther } from 'ethers';
import { WalletIcon, ArrowUpIcon } from '@heroicons/react/24/outline';

export default function TokenBalance() {
  const { address, isConnected } = useAccount();
  const { data: balance } = useBalance({
    address,
    watch: true,
  });

  if (!isConnected || !address) {
    return (
      <div className="flex items-center space-x-2 text-sm text-gray-600">
        <WalletIcon className="h-4 w-4" />
        <span>Connect Wallet</span>
      </div>
    );
  }

  return (
    <div className="flex items-center space-x-3">
      <div className="flex items-center space-x-2 bg-gray-50 rounded-lg px-3 py-2">
        <WalletIcon className="h-4 w-4 text-gray-500" />
        <div className="text-right">
          <div className="text-sm font-medium text-gray-900">
            {balance ? formatEther(balance.value) : '0.00'} ETH
          </div>
          <div className="text-xs text-gray-500">
            {address.slice(0, 6)}...{address.slice(-4)}
          </div>
        </div>
      </div>
      <button className="flex items-center space-x-1 text-sm text-indigo-600 hover:text-indigo-700">
        <ArrowUpIcon className="h-4 w-4" />
        <span>Buy AVT</span>
      </button>
    </div>
  );
}