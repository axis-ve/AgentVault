import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../utils/api';

interface UsageData {
  date: string;
  requests: number;
  cost: number;
}

interface UsageResponse {
  daily_usage: UsageData[];
}

interface UsageChartProps {
  data?: UsageData[];
}

export default function UsageChart({ data }: UsageChartProps) {
  const {
    data: usageResponse,
    isLoading,
    error,
  } = useQuery<UsageResponse>({
    queryKey: ['usage-chart'],
    queryFn: () => apiFetch<UsageResponse>('/usage'),
    enabled: !data,
    staleTime: 60000,
  });

  const chartData = data ?? usageResponse?.daily_usage ?? [];

  if (!data && isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!data && error) {
    return (
      <div className="flex items-center justify-center h-64 text-sm text-red-600">
        {(error as Error).message}
      </div>
    );
  }

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
          />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip
            labelFormatter={(value) => new Date(value).toLocaleDateString()}
            formatter={(value: number, name: string) => {
              if (name === 'requests') {
                return [`${value} calls`, 'Requests'];
              }
              return [`$${value.toFixed(2)}`, 'Cost'];
            }}
          />
          <Line
            type="monotone"
            dataKey="requests"
            stroke="#0ea5e9"
            strokeWidth={2}
            dot={{ fill: '#0ea5e9', strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6, stroke: '#0ea5e9', strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
