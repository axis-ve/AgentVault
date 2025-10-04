import React, { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowPathIcon } from '@heroicons/react/24/outline';
import { apiFetch } from '../utils/api';

interface AgentSummary {
  id: string;
  name: string;
  wallet_address: string;
  balance_eth: number;
}

interface TransferForm {
  agent_id: string;
  to_address: string;
  amount_eth: string;
  confirmation_code: string;
  dry_run: boolean;
}

interface TransferResponse {
  success: boolean;
  dry_run?: boolean;
  simulation?: Record<string, unknown>;
  tx_hash?: string;
  amount_eth?: number;
  to_address?: string;
}

const emptyForm: TransferForm = {
  agent_id: '',
  to_address: '',
  amount_eth: '0.01',
  confirmation_code: '',
  dry_run: true,
};

const Wallet: React.FC = () => {
  const queryClient = useQueryClient();
  const { data: agents, isLoading, error } = useQuery<AgentSummary[]>({
    queryKey: ['agents'],
    queryFn: () => apiFetch<AgentSummary[]>('/agents'),
    refetchInterval: 30000,
  });

  const agentOptions = useMemo(() => agents ?? [], [agents]);
  const [form, setForm] = useState<TransferForm>(emptyForm);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [requestingAgent, setRequestingAgent] = useState(false);

  useEffect(() => {
    if (agentOptions.length > 0 && !form.agent_id) {
      setForm((prev) => ({ ...prev, agent_id: agentOptions[0].id }));
    }
  }, [agentOptions, form.agent_id]);

  const selectedAgent = agentOptions.find((agent) => agent.id === form.agent_id);

  const faucetMutation = useMutation({
    mutationFn: (agentId: string) =>
      apiFetch(`/agents/${encodeURIComponent(agentId)}/faucet`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount_eth: null }),
      }),
    onSuccess: (_data, agentId) => {
      setStatusMessage(`Faucet request sent for ${agentId}. Balance will update once funds arrive.`);
      setErrorMessage(null);
      queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : 'Failed to request faucet funds.';
      setErrorMessage(message);
      setStatusMessage(null);
    },
    onSettled: () => setRequestingAgent(false),
  });

  const transferMutation = useMutation<TransferResponse, unknown, TransferForm>({
    mutationFn: (payload) =>
      apiFetch<TransferResponse>('/agents/transfer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: payload.agent_id,
          to_address: payload.to_address,
          amount_eth: Number(payload.amount_eth),
          confirmation_code: payload.confirmation_code || undefined,
          dry_run: payload.dry_run,
        }),
      }),
    onSuccess: (data) => {
      if (data.dry_run) {
        setStatusMessage('Dry-run simulation complete. Review the details below.');
      } else {
        setStatusMessage(`Transfer sent successfully. Tx hash: ${data.tx_hash}`);
      }
      setErrorMessage(null);
      queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : 'Transfer failed. Please try again.';
      setErrorMessage(message);
      setStatusMessage(null);
    },
  });

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.agent_id || !form.to_address || !form.amount_eth) {
      setErrorMessage('Agent, recipient, and amount are required.');
      setStatusMessage(null);
      return;
    }
    transferMutation.mutate(form);
  };

  const handleFaucet = () => {
    if (!selectedAgent) {
      return;
    }
    setRequestingAgent(true);
    faucetMutation.mutate(selectedAgent.id);
  };

  if (isLoading) {
    return <div className="p-6">Loading wallets…</div>;
  }

  if (error) {
    return <div className="p-6 text-sm text-red-600">{(error as Error).message}</div>;
  }

  if (agentOptions.length === 0) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-6 text-center text-sm text-gray-500">
          No agent wallets yet. Create an agent to provision its secure wallet.
        </div>
      </div>
    );
  }

  const simulation = transferMutation.data?.simulation as
    | { estimated_fee_eth?: number; estimated_total_eth?: number; gas?: number; max_fee_per_gas?: number }
    | undefined;

  return (
    <div className="space-y-8 p-6">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Vault Wallets</h1>
          <p className="text-gray-600">Manage agent-controlled wallets, simulate transfers, and execute MCP operations.</p>
        </div>
        <button
          onClick={() => queryClient.invalidateQueries({ queryKey: ['agents'] })}
          className="inline-flex items-center rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Refresh
        </button>
      </div>

      {(statusMessage || errorMessage) && (
        <div
          className={`rounded-md border px-4 py-3 text-sm ${
            statusMessage ? 'border-green-200 bg-green-50 text-green-700' : 'border-red-200 bg-red-50 text-red-700'
          }`}
        >
          {statusMessage || errorMessage}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">Select Agent Wallet</h2>
          <p className="text-sm text-gray-600">Switch between provisioned wallets to view balances and send managed transfers.</p>
          <select
            value={form.agent_id}
            onChange={(e) => setForm((prev) => ({ ...prev, agent_id: e.target.value }))}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {agentOptions.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.id} ({agent.balance_eth.toFixed(4)} ETH)
              </option>
            ))}
          </select>

          {selectedAgent && (
            <div className="space-y-2 text-sm text-gray-600">
              <div className="flex items-center justify-between">
                <span>Address</span>
                <button
                  onClick={() => navigator.clipboard.writeText(selectedAgent.wallet_address)}
                  className="rounded-md border border-gray-200 px-2 py-1 text-xs text-gray-600 hover:bg-gray-100"
                >
                  Copy
                </button>
              </div>
              <p className="break-all text-xs text-gray-500">{selectedAgent.wallet_address}</p>
              <p>
                Balance: <span className="font-semibold text-gray-900">{selectedAgent.balance_eth.toFixed(6)} ETH</span>
              </p>
              <button
                onClick={handleFaucet}
                disabled={requestingAgent}
                className="inline-flex items-center rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:cursor-not-allowed disabled:bg-blue-200"
              >
                {requestingAgent ? 'Requesting faucet…' : 'Request Testnet Funds'}
              </button>
            </div>
          )}
        </div>

        <div className="lg:col-span-2 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">Simulate & Send Transfer</h2>
          <p className="text-sm text-gray-600">
            Transfers route through the MCP wallet manager with rate limits and policy enforcement. Dry-run first to
            confirm gas and total cost.
          </p>

          <form className="mt-4 grid grid-cols-1 gap-4" onSubmit={handleSubmit}>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Recipient Address</label>
                <input
                  type="text"
                  value={form.to_address}
                  onChange={(e) => setForm((prev) => ({ ...prev, to_address: e.target.value }))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0x..."
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Amount (ETH)</label>
                <input
                  type="number"
                  min="0"
                  step="0.0001"
                  value={form.amount_eth}
                  onChange={(e) => setForm((prev) => ({ ...prev, amount_eth: e.target.value }))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Confirmation Code</label>
                <input
                  type="text"
                  value={form.confirmation_code}
                  onChange={(e) => setForm((prev) => ({ ...prev, confirmation_code: e.target.value }))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="optional"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Required if transfers exceed the configured on-chain spend limit.
                </p>
              </div>
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-gray-700">Dry run</label>
                <button
                  type="button"
                  onClick={() => setForm((prev) => ({ ...prev, dry_run: !prev.dry_run }))}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    form.dry_run ? 'bg-blue-600' : 'bg-gray-200'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      form.dry_run ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
                <span className="text-xs text-gray-500">Simulate without broadcasting</span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setForm((prev) => ({ ...prev, dry_run: true }))}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                Reset
              </button>
              <button
                type="submit"
                disabled={transferMutation.isPending}
                className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
              >
                {transferMutation.isPending ? (
                  <>
                    <ArrowPathIcon className="mr-2 h-4 w-4 animate-spin" /> Processing…
                  </>
                ) : form.dry_run ? (
                  'Run Simulation'
                ) : (
                  'Send Transfer'
                )}
              </button>
            </div>
          </form>

          {simulation && (
            <div className="mt-6 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-700">
              <p className="font-semibold">Simulation Results</p>
              <ul className="mt-2 space-y-1">
                <li>Estimated fee: {simulation.estimated_fee_eth ?? 'n/a'} ETH</li>
                <li>Estimated total: {simulation.estimated_total_eth ?? 'n/a'} ETH</li>
                <li>Gas estimate: {simulation.gas ?? 'n/a'}</li>
                <li>Max fee per gas: {simulation.max_fee_per_gas ?? 'n/a'}</li>
              </ul>
              <p className="mt-2 text-xs text-blue-600">
                Set "Dry run" to off and submit again to broadcast the transaction.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Wallet;
