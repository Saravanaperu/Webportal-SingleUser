import React from 'react';

const AccountOverview = React.memo(({ account }) => {
  return (
    <div className="card">
      <h3>
        💰 Account Overview
        {account?.paper_mode && (
          <span style={{ 
            fontSize: '0.7rem', 
            background: '#ffc107', 
            color: '#744210', 
            padding: '0.2rem 0.5rem', 
            borderRadius: '4px', 
            marginLeft: '0.5rem',
            fontWeight: '600'
          }}>
            PAPER
          </span>
        )}
      </h3>
      <div style={{ display: 'grid', gap: '0.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Balance:</span>
          <span style={{ fontWeight: '600', fontSize: '1.1rem' }}>
            {account ? `₹${account.balance?.toLocaleString('en-IN', {minimumFractionDigits: 2})}` : '--'}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Margin Used:</span>
          <span style={{ fontWeight: '600', fontSize: '1.1rem' }}>
            {account ? `₹${account.margin?.toLocaleString('en-IN', {minimumFractionDigits: 2})}` : '--'}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Available:</span>
          <span style={{ fontWeight: '600', fontSize: '1.1rem', color: '#38a169' }}>
            {account ? `₹${(account.available || ((account.balance || 0) - (account.margin || 0))).toLocaleString('en-IN', {minimumFractionDigits: 2})}` : '--'}
          </span>
        </div>
        {account?.error && (
          <div style={{ color: '#e53e3e', fontSize: '0.9rem', marginTop: '0.5rem' }}>Error: {account.error}</div>
        )}
      </div>
    </div>
  );
});

export default AccountOverview;