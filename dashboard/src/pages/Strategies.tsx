import React, { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  BoltIcon,
  PlayCircleIcon,
  StopCircleIcon,
  ArrowPathIcon,
  PlusIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { apiFetch } from '../utils/api';

interface Strategy {
  label: string;
  agent_id: string;
  to_address: string;
  amount_eth: number;
  interval_seconds: number;
  enabled: boolean;
  max_base_fee_gwei?: number | null;
  daily_cap_eth?: number | null;
  next_run_at?: string | null;
  last_run_at?: string | null;
  last_tx_hash?: string | null;
}

interface StrategyMap {
  [label: string]: Strategy;
}

interface CreateStrategyForm {
  label: string;
  agent_id: string;
  to_address: string;
  amount_eth: string;
  interval_seconds: string;
  max_base_fee_gwei: string;
  daily_cap_eth: string;
}

const defaultForm: CreateStrategyForm = {
  label: '',
  agent_id: '',
  to_address: '',
  amount_eth: '0.1',
  interval_seconds: '3600',
  max_base_fee_gwei: '',
  daily_cap_eth: '',
};

const Strategies: React.FC = () => {
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [form, setForm] = useState<CreateStrategyForm>(defaultForm);
  const [message, setMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery<StrategyMap>({
    queryKey: ['strategies'],
    queryFn: () => apiFetch<StrategyMap>('/strategies'),
    refetchInterval: 30000,
  });

  const strategies = useMemo(() => {
    if (!data) {
      return [] as Strategy[];
    }
    return Object.entries(data).map(([label, value]) => ({ ...value, label }));
  }, [data]);

  const resetFeedback = () => {
    setMessage(null);
    setErrorMessage(null);
  };

  const createStrategy = useMutation({
    mutationFn: (payload: CreateStrategyForm) => {
      const body = {
        label: payload.label,
        agent_id: payload.agent_id,
        to_address: payload.to_address,
        amount_eth: Number(payload.amount_eth),
        interval_seconds: Number(payload.interval_seconds),
        max_base_fee_gwei: payload.max_base_fee_gwei ? Number(payload.max_base_fee_gwei) : null,
        daily_cap_eth: payload.daily_cap_eth ? Number(payload.daily_cap_eth) : null,
      };
      return apiFetch('/strategies/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
    },
    onSuccess: () => {
      setMessage('Strategy created successfully.');
      setErrorMessage(null);
      setForm(defaultForm);
      setIsCreateOpen(false);
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : 'Failed to create strategy.';
      setErrorMessage(message);
      setMessage(null);
    },
  });

  const startStrategy = useMutation({
    mutationFn: (label: string) =>
      apiFetch(`/strategies/${encodeURIComponent(label)}/start`, {
        method: 'POST',
      }),
    onSuccess: () => {
      setMessage('Strategy started');
      setErrorMessage(null);
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
    },
    onError: () => setErrorMessage('Unable to start strategy.'),
  });

  const stopStrategy = useMutation({
    mutationFn: (label: string) =>
      apiFetch(`/strategies/${encodeURIComponent(label)}/stop`, {
        method: 'POST',
      }),
    onSuccess: () => {
      setMessage('Strategy stopped');
      setErrorMessage(null);
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
    },
    onError: () => setErrorMessage('Unable to stop strategy.'),
  });

  const tickStrategy = useMutation({
    mutationFn: (label: string) =>
      apiFetch(`/strategies/${encodeURIComponent(label)}/tick`, {
        method: 'POST',
      }),
    onSuccess: () => {
      setMessage('Strategy tick executed');
      setErrorMessage(null);
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
    },
    onError: () => setErrorMessage('Unable to tick strategy.'),
  });

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    resetFeedback();
    if (!form.label.trim() || !form.agent_id.trim() || !form.to_address.trim()) {
      setErrorMessage('Label, agent ID, and recipient address are required.');
      return;
    }
    createStrategy.mutate(form);
  };

  if (isLoading) {
    return <div className="p-6">Loading strategies...</div>;
  }

  if (error) {
    return <div className="p-6 text-sm text-red-600">{(error as Error).message}</div>;
  }

  return (
    <div className="p-6">
      <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Strategies</h1>
          <p className="mt-2 text-gray-600">Automate transfers with gas and spend controls.</p>
        </div>
        <div className="flex flex-col items-start gap-2 md:flex-row md:items-center">
          <button
            onClick={() => {
              resetFeedback();
              setIsCreateOpen(true);
            }}
            className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
          >
            <PlusIcon className="mr-2 h-5 w-5" />
            New Strategy
          </button>
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ['strategies'] })}
            className="inline-flex items-center rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Refresh
          </button>
        </div>
      </div>

      {(message || errorMessage) && (
        <div
          className={`mb-6 rounded-md border px-4 py-3 text-sm ${
            message ? 'border-green-200 bg-green-50 text-green-700' : 'border-red-200 bg-red-50 text-red-700'
          }`}
        >
          {message || errorMessage}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {strategies.length === 0 && (
          <div className="rounded-lg border border-dashed border-gray-300 bg-white p-6 text-center text-sm text-gray-500">
            No strategies configured yet. Create one to begin automated transfers.
          </div>
        )}
        {strategies.map((strategy) => (
          <div key={strategy.label} className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <BoltIcon className="h-5 w-5 text-blue-500" />
                  <h3 className="text-lg font-semibold text-gray-900">{strategy.label}</h3>
                  {strategy.enabled ? (
                    <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                      Active
                    </span>
                  ) : (
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                      Paused
                    </span>
                  )}
                </div>
                <p className="mt-2 text-sm text-gray-500">
                  Agent {strategy.agent_id} → {strategy.to_address.slice(0, 6)}...{strategy.to_address.slice(-4)}
                </p>
              </div>
              <div className="text-right text-sm text-gray-500">
                <p>{strategy.amount_eth} ETH every {strategy.interval_seconds} s</p>
                {strategy.daily_cap_eth && <p>Daily cap: {strategy.daily_cap_eth} ETH</p>}
              </div>
            </div>
            <div className="mt-4 grid grid-cols-1 gap-3 text-sm text-gray-600 sm:grid-cols-2">
              <p>Next run: {strategy.next_run_at ? new Date(strategy.next_run_at).toLocaleString() : '—'}</p>
              <p>Last run: {strategy.last_run_at ? new Date(strategy.last_run_at).toLocaleString() : '—'}</p>
              <p>Gas ceiling: {strategy.max_base_fee_gwei ?? 'n/a'} gwei</p>
              <p>Last tx: {strategy.last_tx_hash ? `${strategy.last_tx_hash.slice(0, 10)}…` : '—'}</p>
            </div>
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                onClick={() => startStrategy.mutate(strategy.label)}
                className="inline-flex items-center rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm font-medium text-green-700 hover:bg-green-100"
              >
                <PlayCircleIcon className="mr-2 h-5 w-5" /> Start
              </button>
              <button
                onClick={() => stopStrategy.mutate(strategy.label)}
                className="inline-flex items-center rounded-md border border-orange-200 bg-orange-50 px-3 py-2 text-sm font-medium text-orange-700 hover:bg-orange-100"
              >
                <StopCircleIcon className="mr-2 h-5 w-5" /> Pause
              </button>
              <button
                onClick={() => tickStrategy.mutate(strategy.label)}
                className="inline-flex items-center rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100"
              >
                <ArrowPathIcon className="mr-2 h-5 w-5" /> Tick Now
              </button>
            </div>
          </div>
        ))}
      </div>

      {isCreateOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-gray-900 bg-opacity-50 px-4">
          <div className="w-full max-w-3xl rounded-lg bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between border-b pb-3">
              <h2 className="text-lg font-semibold text-gray-900">New DCA Strategy</h2>
              <button
                onClick={() => setIsCreateOpen(false)}
                className="rounded-md p-1 text-gray-500 hover:bg-gray-100"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>
            <form className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2" onSubmit={handleSubmit}>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Label</label>
                <input
                  type="text"
                  value={form.label}
                  onChange={(e) => setForm((prev) => ({ ...prev, label: e.target.value }))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="weekly-dca"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Agent ID</label>
                <input
                  type="text"
                  value={form.agent_id}
                  onChange={(e) => setForm((prev) => ({ ...prev, agent_id: e.target.value }))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="marketing-bot"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Recipient Address</label>
                <input
                  type="text"
                  value={form.to_address}
                  onChange={(e) => setForm((prev) => ({ ...prev, to_address: e.target.value }))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0x..."
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Amount (ETH)</label>
                <input
                  type="number"
                  step="0.0001"
                  value={form.amount_eth}
                  onChange={(e) => setForm((prev) => ({ ...prev, amount_eth: e.target.value }))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Interval (seconds)</label>
                <input
                  type="number"
                  value={form.interval_seconds}
                  onChange={(e) => setForm((prev) => ({ ...prev, interval_seconds: e.target.value }))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Max Base Fee (gwei)</label>
                <input
                  type="number"
                  step="0.1"
                  value={form.max_base_fee_gwei}
                  onChange={(e) => setForm((prev) => ({ ...prev, max_base_fee_gwei: e.target.value }))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="optional"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Daily Cap (ETH)</label>
                <input
                  type="number"
                  step="0.0001"
                  value={form.daily_cap_eth}
                  onChange={(e) => setForm((prev) => ({ ...prev, daily_cap_eth: e.target.value }))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="optional"
                />
              </div>
              <div className="md:col-span-2 flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createStrategy.isPending}
                  className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
                >
                  {createStrategy.isPending ? 'Creating...' : 'Create Strategy'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Strategies;
