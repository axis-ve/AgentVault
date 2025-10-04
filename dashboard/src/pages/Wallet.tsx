import React, { useState } from 'react';
import { WalletIcon, ArrowUpIcon, ArrowDownIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { useAccount, useBalance, useSendTransaction } from 'wagmi';
import { formatEther, parseEther } from 'viem';

const Wallet: React.FC = () => {
  const { address, isConnected } = useAccount();
  const { data: balance } = useBalance({ address });
  const [sendAmount, setSendAmount] = useState('');
  const [recipient, setRecipient] = useState('');
  const [isSending, setIsSending] = useState(false);

  const { sendTransaction } = useSendTransaction();

  const handleSendTransaction = async () => {
    if (!sendAmount || !recipient) return;

    setIsSending(true);
    try {
      await sendTransaction({
        to: recipient as `0x${string}`,
        value: parseEther(sendAmount),
      });
      setSendAmount('');
      setRecipient('');
    } catch (error) {
      console.error('Transaction failed:', error);
    } finally {
      setIsSending(false);
    }
  };

  if (!isConnected) {
    return (
      <div className="p-6">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Wallet</h1>
          <p className="mt-2 text-gray-600">Connect your wallet to manage your tokens</p>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="text-center">
            <WalletIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No wallet connected</h3>
            <p className="mt-1 text-sm text-gray-500">Connect your wallet to view your balance and transactions</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Wallet</h1>
        <p className="mt-2 text-gray-600">Manage your AVT tokens and transactions</p>
      </div>

      {/* Wallet Balance */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">AVT Balance</h2>
            <p className="text-sm text-gray-500">Your AgentVault Token balance</p>
          </div>
          <div className="text-right">
            <p className="text-3xl font-bold text-gray-900">
              {balance ? formatEther(balance.value) : '0'} AVT
            </p>
            <p className="text-sm text-gray-500">
              {balance ? `$${(Number(balance.value) / 1e18 * 0.1).toFixed(2)}` : '$0.00'}
            </p>
          </div>
        </div>
      </div>

      {/* Send Tokens */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Send Tokens</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Recipient Address
            </label>
            <input
              type="text"
              value={recipient}
              onChange={(e) => setRecipient(e.target.value)}
              placeholder="0x..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Amount (AVT)
            </label>
            <input
              type="number"
              value={sendAmount}
              onChange={(e) => setSendAmount(e.target.value)}
              placeholder="0.00"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <button
            onClick={handleSendTransaction}
            disabled={!sendAmount || !recipient || isSending}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center"
          >
            {isSending ? (
              <>
                <ArrowPathIcon className="h-4 w-4 mr-2 animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <ArrowUpIcon className="h-4 w-4 mr-2" />
                Send Tokens
              </>
            )}
          </button>
        </div>
      </div>

      {/* Transaction History */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Transactions</h2>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center">
              <ArrowDownIcon className="h-4 w-4 text-green-500 mr-3" />
              <div>
                <p className="text-sm font-medium text-gray-900">Received 100 AVT</p>
                <p className="text-xs text-gray-500">From 0x1234...5678</p>
              </div>
            </div>
            <span className="text-xs text-gray-500">2 hours ago</span>
          </div>
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center">
              <ArrowUpIcon className="h-4 w-4 text-red-500 mr-3" />
              <div>
                <p className="text-sm font-medium text-gray-900">Sent 50 AVT</p>
                <p className="text-xs text-gray-500">To 0xabcd...efgh</p>
              </div>
            </div>
            <span className="text-xs text-gray-500">1 day ago</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Wallet;
