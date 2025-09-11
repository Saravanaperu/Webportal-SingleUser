import React from 'react';

const AccountOverview = ({ account }) => {
  const getConnectionStatus = () => {
    if (account?.error) return { text: 'DISCONNECTED', color: '#dc3545' };
    if (account?.balance !== undefined) return { text: 'CONNECTED', color: '#28a745' };
    return { text: 'CONNECTING...', color: '#ffc107' };
  };

  const status = getConnectionStatus();

  return (
    <div className="card">
      <h3>Account Overview</h3>
      <div style={{ marginBottom: '1rem' }}>
        <strong>Broker Status: </strong>
        <span className={status.color === '#28a745' ? 'status-positive' : status.color === '#dc3545' ? 'status-negative' : 'status-warning'}>
          {status.text}
        </span>
      </div>
      <div style={{ display: 'grid', gap: '0.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Balance:</span>
          <span style={{ fontWeight: '600', fontSize: '1.1rem' }}>
            {account ? `₹${account.balance?.toLocaleString('en-IN', {minimumFractionDigits: 2})}` : '--'}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Margin:</span>
          <span style={{ fontWeight: '600', fontSize: '1.1rem' }}>
            {account ? `₹${account.margin?.toLocaleString('en-IN', {minimumFractionDigits: 2})}` : '--'}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Available:</span>
          <span style={{ fontWeight: '600', fontSize: '1.1rem', color: '#28a745' }}>
            {account ? `₹${((account.balance || 0) - (account.margin || 0)).toLocaleString('en-IN', {minimumFractionDigits: 2})}` : '--'}
          </span>
        </div>
        {account?.error && (
          <div style={{ color: '#dc3545', fontSize: '0.9rem', marginTop: '0.5rem' }}>Error: {account.error}</div>
        )}
      </div>
    </div>
  );
};

export default AccountOverview;