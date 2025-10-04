import React, { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CpuChipIcon, ClockIcon, CheckCircleIcon, PlusIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { apiFetch } from '../utils/api';

interface Agent {
  id: string;
  name: string;
  description: string;
  wallet_address: string;
  status: string;
  created_at: string;
  last_active: string | null;
  balance_eth: number;
}

interface CreateAgentForm {
  name: string;
  description: string;
}

const Agents: React.FC = () => {
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [form, setForm] = useState<CreateAgentForm>({ name: '', description: '' });
  const [feedback, setFeedback] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const {
    data: agents,
    isLoading,
    error,
  } = useQuery<Agent[]>({
    queryKey: ['agents'],
    queryFn: () => apiFetch<Agent[]>('/agents'),
    refetchInterval: 30000,
  });

  const createAgent = useMutation({
    mutationFn: (payload: CreateAgentForm) =>
      apiFetch('/agents/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
    onSuccess: (data: any) => {
      setFeedback(`Agent ${data?.name ?? form.name} created successfully.`);
      setErrorMessage(null);
      setForm({ name: '', description: '' });
      setIsCreateOpen(false);
      queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : 'Failed to create agent.';
      setErrorMessage(message);
      setFeedback(null);
    },
  });

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.name.trim()) {
      setErrorMessage('Agent name is required.');
      return;
    }
    createAgent.mutate(form);
  };

  const agentList = useMemo(() => agents ?? [], [agents]);

  if (isLoading) {
    return <div className="p-6">Loading agents...</div>;
  }

  if (error) {
    return <div className="p-6 text-sm text-red-600">{(error as Error).message}</div>;
  }

  return (
    <div className="p-6">
      <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">AI Agents</h1>
          <p className="mt-2 text-gray-600">Manage your autonomous AI trading agents</p>
        </div>
        <div className="flex flex-col items-start gap-2 md:flex-row md:items-center">
          <button
            onClick={() => {
              setIsCreateOpen(true);
              setFeedback(null);
              setErrorMessage(null);
            }}
            className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
          >
            <PlusIcon className="mr-2 h-5 w-5" />
            Create Agent
          </button>
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ['agents'] })}
            className="inline-flex items-center rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Refresh
          </button>
        </div>
      </div>

      {(feedback || errorMessage) && (
        <div
          className={`mb-6 rounded-md border px-4 py-3 text-sm ${
            feedback ? 'border-green-200 bg-green-50 text-green-700' : 'border-red-200 bg-red-50 text-red-700'
          }`}
        >
          {feedback || errorMessage}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {agentList.length === 0 && (
          <div className="rounded-lg border border-dashed border-gray-300 bg-white p-6 text-center text-sm text-gray-500">
            No agents found yet. Create one to get started.
          </div>
        )}
        {agentList.map((agent) => (
          <div key={agent.id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center">
                <CpuChipIcon className="h-8 w-8 text-blue-600" />
                <div className="ml-3">
                  <h3 className="text-lg font-semibold text-gray-900">{agent.name}</h3>
                  <div className="flex items-center mt-1">
                    {agent.status === 'active' ? (
                      <CheckCircleIcon className="h-4 w-4 text-green-500" />
                    ) : (
                      <ClockIcon className="h-4 w-4 text-yellow-500" />
                    )}
                    <span className="ml-1 text-sm text-gray-500 capitalize">{agent.status}</span>
                  </div>
                </div>
              </div>
              <div className="text-sm text-gray-500">{agent.balance_eth.toFixed(4)} ETH</div>
            </div>

            <p className="text-gray-600 text-sm mb-4">{agent.description}</p>

            <div className="text-xs text-gray-500 space-y-1">
              <p>
                Wallet: {agent.wallet_address.slice(0, 6)}...{agent.wallet_address.slice(-4)}
              </p>
              <p>Created: {new Date(agent.created_at).toLocaleDateString()}</p>
              {agent.last_active && <p>Last active: {new Date(agent.last_active).toLocaleString()}</p>}
            </div>
          </div>
        ))}
      </div>

      {isCreateOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-gray-900 bg-opacity-50 px-4">
          <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between border-b pb-3">
              <h2 className="text-lg font-semibold text-gray-900">Create Agent</h2>
              <button
                onClick={() => setIsCreateOpen(false)}
                className="rounded-md p-1 text-gray-500 hover:bg-gray-100"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>
            <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Agent Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder="marketing-bot"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
                  placeholder="Purpose or notes for this agent"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                />
              </div>
              {createAgent.isError && !errorMessage && (
                <div className="text-sm text-red-600">Failed to create the agent. Please try again.</div>
              )}
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createAgent.isPending}
                  className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
                >
                  {createAgent.isPending ? 'Creating...' : 'Create Agent'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Agents;
