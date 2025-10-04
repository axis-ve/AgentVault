import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChartBarIcon, ClockIcon, CurrencyDollarIcon } from '@heroicons/react/24/outline';
import UsageChart from '../components/UsageChart';
import { apiFetch } from '../utils/api';

interface UsageStats {
  total_requests: number;
  total_cost: number;
  daily_usage: Array<{ date: string; requests: number; cost: number }>;
  monthly_usage: Array<{ month: string; requests: number; cost: number }>;
}

const Usage: React.FC = () => {
  const {
    data: usage,
    isLoading,
    error,
  } = useQuery<UsageStats>({
    queryKey: ['usage'],
    queryFn: () => apiFetch<UsageStats>('/usage'),
    refetchInterval: 60000,
  });

  if (isLoading) {
    return <div className="p-6">Loading usage data...</div>;
  }

  if (error) {
    return <div className="p-6 text-sm text-red-600">{(error as Error).message}</div>;
  }

  if (!usage) {
    return <div className="p-6 text-sm text-gray-600">No usage data yet.</div>;
  }

  return (
    <div className="p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Usage Analytics</h1>
        <p className="mt-2 text-gray-600">Track your AI agent usage and costs</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center">
            <ChartBarIcon className="h-8 w-8 text-blue-600" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Requests</p>
              <p className="text-2xl font-bold text-gray-900">{usage.total_requests.toLocaleString()}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center">
            <CurrencyDollarIcon className="h-8 w-8 text-green-600" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Cost</p>
              <p className="text-2xl font-bold text-gray-900">${usage.total_cost.toFixed(4)}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center">
            <ClockIcon className="h-8 w-8 text-purple-600" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Avg Daily</p>
              <p className="text-2xl font-bold text-gray-900">
                {usage.daily_usage.length
                  ? Math.round(usage.total_requests / usage.daily_usage.length)
                  : 0}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Usage Chart */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Usage Over Time</h2>
        <UsageChart data={usage.daily_usage} />
      </div>

      {/* Monthly Summary */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Monthly Summary</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Month
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Requests
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cost
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Avg/Day
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {usage.monthly_usage.map((month, index) => (
                <tr key={index}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {month.month}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {month.requests.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${month.cost.toFixed(4)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {Math.round(month.requests / 30)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Usage;
