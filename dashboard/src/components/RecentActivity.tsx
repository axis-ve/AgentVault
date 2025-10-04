import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import {
  CpuChipIcon,
  ArrowRightIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../utils/api';

interface Activity {
  id: string;
  type: 'agent_created' | 'transaction' | 'strategy' | 'tool_call' | 'error';
  title: string;
  description: string;
  timestamp: string;
  status: 'success' | 'error' | 'pending';
}

export default function RecentActivity() {
  const {
    data: activities,
    isLoading,
    error,
  } = useQuery<Activity[]>({
    queryKey: ['recent-activity'],
    queryFn: () => apiFetch<Activity[]>('/activity/recent'),
    refetchInterval: 30000,
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
            <div className="h-3 bg-gray-200 rounded w-1/2" />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-sm text-red-600">{(error as Error).message}</div>
    );
  }

  if (!activities || activities.length === 0) {
    return <div className="text-sm text-gray-500">No recent activity.</div>;
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircleIcon className="h-4 w-4 text-green-500" />;
      case 'error':
        return <XCircleIcon className="h-4 w-4 text-red-500" />;
      default:
        return <div className="h-4 w-4 bg-yellow-400 rounded-full" />;
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'agent_created':
        return <CpuChipIcon className="h-4 w-4 text-blue-500" />;
      case 'transaction':
        return <ArrowRightIcon className="h-4 w-4 text-green-500" />;
      case 'strategy':
        return <div className="h-4 w-4 bg-purple-500 rounded" />;
      default:
        return <div className="h-4 w-4 bg-gray-500 rounded" />;
    }
  };

  return (
    <div className="space-y-4">
      {activities.map((activity) => (
        <div key={activity.id} className="flex items-start space-x-3">
          <div className="flex-shrink-0">{getTypeIcon(activity.type)}</div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-gray-900 truncate">{activity.title}</p>
              <div className="flex items-center space-x-1">
                {getStatusIcon(activity.status)}
                <span className="text-xs text-gray-500">
                  {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
                </span>
              </div>
            </div>
            <p className="text-sm text-gray-500 truncate">{activity.description}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
