import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { GiftIcon, CheckCircleIcon, ClockIcon, XCircleIcon } from '@heroicons/react/24/outline';
import { apiFetch } from '../utils/api';

interface AirdropClaim {
  id: string;
  amount: number;
  status: 'available' | 'claimed' | 'expired';
  claimDeadline: string;
  description: string;
  claimedAt?: string;
}

const Airdrop: React.FC = () => {
  const [isClaiming, setIsClaiming] = useState<string | null>(null);

  const {
    data: airdropClaims,
    isLoading,
    error,
    refetch,
  } = useQuery<AirdropClaim[]>({
    queryKey: ['airdrops'],
    queryFn: () => apiFetch<AirdropClaim[]>('/airdrops/claims'),
    refetchInterval: 30000,
  });

  const handleClaimAirdrop = async (claimId: string) => {
    setIsClaiming(claimId);
    try {
      await apiFetch(`/airdrops/claim/${claimId}`, { method: 'POST' });
      await refetch();
    } catch (err) {
      console.error('Failed to claim airdrop:', err);
    } finally {
      setIsClaiming(null);
    }
  };

  if (isLoading) {
    return <div className="p-6">Loading airdrop claims...</div>;
  }

  if (error) {
    return <div className="p-6 text-sm text-red-600">{(error as Error).message}</div>;
  }

  const availableClaims = airdropClaims?.filter((claim) => claim.status === 'available') || [];
  const claimedAirdrops = airdropClaims?.filter((claim) => claim.status === 'claimed') || [];
  const expiredClaims = airdropClaims?.filter((claim) => claim.status === 'expired') || [];

  return (
    <div className="p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Airdrop Claims</h1>
        <p className="mt-2 text-gray-600">Claim your AVT tokens from active airdrops</p>
      </div>

      {/* Available Claims */}
      {availableClaims.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Available Claims</h2>
          <div className="space-y-4">
            {availableClaims.map((claim) => (
              <div key={claim.id} className="border border-green-200 rounded-lg p-4 bg-green-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <GiftIcon className="h-8 w-8 text-green-600 mr-3" />
                    <div>
                      <h3 className="font-medium text-gray-900">{claim.description}</h3>
                      <p className="text-sm text-gray-600">
                        {claim.amount} AVT tokens • Claim by {new Date(claim.claimDeadline).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleClaimAirdrop(claim.id)}
                    disabled={isClaiming === claim.id}
                    className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center"
                  >
                    {isClaiming === claim.id ? (
                      <>
                        <ClockIcon className="h-4 w-4 mr-2 animate-spin" />
                        Claiming...
                      </>
                    ) : (
                      <>
                        <CheckCircleIcon className="h-4 w-4 mr-2" />
                        Claim Tokens
                      </>
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Claimed Airdrops */}
      {claimedAirdrops.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Claimed Airdrops</h2>
          <div className="space-y-3">
            {claimedAirdrops.map((claim) => (
              <div key={claim.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center">
                  <CheckCircleIcon className="h-5 w-5 text-green-500 mr-3" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">{claim.description}</p>
                    <p className="text-sm text-gray-500">{claim.amount} AVT tokens claimed</p>
                  </div>
                </div>
                <span className="text-xs text-green-600 font-medium">Claimed</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Expired Claims */}
      {expiredClaims.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Expired Claims</h2>
          <div className="space-y-3">
            {expiredClaims.map((claim) => (
              <div key={claim.id} className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                <div className="flex items-center">
                  <XCircleIcon className="h-5 w-5 text-red-500 mr-3" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">{claim.description}</p>
                    <p className="text-sm text-gray-500">{claim.amount} AVT tokens expired</p>
                  </div>
                </div>
                <span className="text-xs text-red-600 font-medium">Expired</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No Claims Available */}
      {(!airdropClaims || airdropClaims.length === 0) && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="text-center">
            <GiftIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No airdrops available</h3>
            <p className="mt-1 text-sm text-gray-500">
              Check back later for new airdrop opportunities
            </p>
          </div>
        </div>
      )}

      {/* Airdrop Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-sm font-medium text-gray-500">Total Claimed</h3>
          <p className="text-2xl font-bold text-gray-900">
            {claimedAirdrops.reduce((sum, claim) => sum + claim.amount, 0)} AVT
          </p>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-sm font-medium text-gray-500">Available to Claim</h3>
          <p className="text-2xl font-bold text-gray-900">
            {availableClaims.reduce((sum, claim) => sum + claim.amount, 0)} AVT
          </p>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-sm font-medium text-gray-500">Total Airdrops</h3>
          <p className="text-2xl font-bold text-gray-900">{airdropClaims?.length || 0}</p>
        </div>
      </div>
    </div>
  );
};

export default Airdrop;
