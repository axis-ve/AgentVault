import React from 'react';
import {
  CpuChipIcon,
  ChartBarIcon,
  CreditCardIcon,
  ArrowTrendingUpIcon,
  ClockIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { useQuery } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';
import StatsCard from '../components/StatsCard';
import UsageChart from '../components/UsageChart';
import RecentActivity from '../components/RecentActivity';
import TokenBalance from '../components/TokenBalance';
import { apiFetch } from '../utils/api';

interface DashboardStats {
  totalAgents: number;
  activeAgents: number;
  totalUsage: number;
  monthlyUsage: number;
  tokenBalance: string;
  airdropEligible: boolean;
  nextAirdrop: string;
  activeStrategies?: number;
}

interface UsageSummary {
  daily_usage: Array<{ date: string; requests: number; cost: number }>;
  monthly_usage: Array<{ month: string; requests: number; cost: number }>;
  total_requests: number;
  total_cost: number;
}

export default function Dashboard() {
  const {
    data: stats,
    isLoading,
    error,
  } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: () => apiFetch<DashboardStats>('/dashboard/stats'),
    refetchInterval: 30000,
  });

  const { data: usageSummary } = useQuery<UsageSummary>({
    queryKey: ['usage-summary'],
    queryFn: () => apiFetch<UsageSummary>('/usage'),
    staleTime: 60000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          <p className="font-semibold">Failed to load dashboard</p>
          <p className="text-sm mt-1">{(error as Error).message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600">Welcome back! Here's what's happening with your agents.</p>
        </div>
        <TokenBalance />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Total Agents"
          value={stats?.totalAgents || 0}
          icon={CpuChipIcon}
          trend={{ value: stats?.totalAgents || 0, isPositive: true }}
          color="blue"
        />
        <StatsCard
          title="Active Agents"
          value={stats?.activeAgents || 0}
          icon={ChartBarIcon}
          trend={{ value: stats?.activeAgents || 0, isPositive: true }}
          color="green"
        />
        <StatsCard
          title="Monthly Usage"
          value={stats?.monthlyUsage || 0}
          icon={ArrowTrendingUpIcon}
          trend={{ value: stats?.monthlyUsage || 0, isPositive: true }}
          color="purple"
        />
        <StatsCard
          title="Token Balance"
          value={stats?.tokenBalance || '0'}
          icon={CreditCardIcon}
          trend={{ value: Number(stats?.tokenBalance || 0), isPositive: true }}
          color="yellow"
        />
        {typeof stats?.activeStrategies === 'number' && (
          <StatsCard
            title="Active Strategies"
            value={stats.activeStrategies}
            icon={ChartBarIcon}
            trend={{ value: stats.activeStrategies, isPositive: stats.activeStrategies > 0 }}
            color="blue"
          />
        )}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Usage Chart */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Usage Overview</h3>
          <UsageChart data={usageSummary?.daily_usage} />
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Activity</h3>
          <RecentActivity />
        </div>
      </div>

      {/* Alerts and Notifications */}
      {stats?.airdropEligible && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <ExclamationTriangleIcon className="h-5 w-5 text-green-400" />
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-green-800">Airdrop Available!</h3>
              <div className="mt-2 text-sm text-green-700">
                <p>
                  You're eligible for an airdrop! Claim your tokens before{' '}
                  {stats?.nextAirdrop
                    ? formatDistanceToNow(new Date(stats.nextAirdrop), { addSuffix: true })
                    : 'the deadline'}.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <button className="flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700">
            <CpuChipIcon className="h-5 w-5 mr-2" />
            Create Agent
          </button>
          <button className="flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
            <ChartBarIcon className="h-5 w-5 mr-2" />
            View Analytics
          </button>
          <button className="flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
            <CreditCardIcon className="h-5 w-5 mr-2" />
            Buy Tokens
          </button>
          <button className="flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
            <ClockIcon className="h-5 w-5 mr-2" />
            Schedule Task
          </button>
        </div>
      </div>
    </div>
  );
}
