import React from 'react';

const AccountOverview = ({ account }) => {
  return (
    <div>
      <h2>Account Overview</h2>
      <div id="account-details">
        <p>Balance: <span id="balance">{account ? `₹${account.balance?.toFixed(2)}` : '--'}</span></p>
        <p>Margin: <span id="margin">{account ? `₹${account.margin?.toFixed(2)}` : '--'}</span></p>
      </div>
    </div>
  );
};

export default AccountOverview;
