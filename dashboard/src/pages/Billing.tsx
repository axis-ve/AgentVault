import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { CreditCardIcon, ClockIcon, CheckCircleIcon } from '@heroicons/react/24/outline';
import { apiFetch } from '../utils/api';

interface BillingHistory {
  id: string;
  amount: number;
  description: string;
  timestamp: string;
  status: string;
}

const Billing: React.FC = () => {
  const {
    data: billingHistory,
    isLoading,
    error,
  } = useQuery<BillingHistory[]>({
    queryKey: ['billing'],
    queryFn: () => apiFetch<BillingHistory[]>('/billing/history'),
    refetchInterval: 60000,
  });

  if (isLoading) {
    return <div className="p-6">Loading billing history...</div>;
  }

  if (error) {
    return <div className="p-6 text-sm text-red-600">{(error as Error).message}</div>;
  }

  return (
    <div className="p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Billing & Payments</h1>
        <p className="mt-2 text-gray-600">View your payment history and manage billing</p>
      </div>

      {/* Current Plan */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Current Plan</h2>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold text-gray-900">Usage-Based Plan</h3>
            <p className="text-gray-600">Pay per MCP call • On-chain security • Dashboard analytics</p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold text-gray-900">${billingHistory?.[0]?.amount.toFixed(4) || '0.0000'}</p>
            <p className="text-sm text-gray-500">latest invoice</p>
          </div>
        </div>
      </div>

      {/* Payment Method */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Payment Method</h2>
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <CreditCardIcon className="h-8 w-8 text-blue-600" />
            <div className="ml-4">
              <p className="font-medium text-gray-900">ETH / AVT on-chain settlement</p>
              <p className="text-sm text-gray-500">Link your wallet to settle invoices automatically</p>
            </div>
          </div>
          <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
            Configure
          </button>
        </div>
      </div>

      {/* Billing History */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Billing History</h2>
        {billingHistory && billingHistory.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Description
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Amount
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {billingHistory.map((bill) => (
                  <tr key={bill.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {new Date(bill.timestamp).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {bill.description}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      ${bill.amount.toFixed(4)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        {bill.status === 'paid' ? (
                          <CheckCircleIcon className="h-4 w-4 text-green-500" />
                        ) : (
                          <ClockIcon className="h-4 w-4 text-yellow-500" />
                        )}
                        <span className="ml-2 text-sm text-gray-500 capitalize">{bill.status}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-sm text-gray-600">No invoices generated yet.</div>
        )}
      </div>
    </div>
  );
};

export default Billing;
