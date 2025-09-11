import React from 'react';

const AccountOverview = ({ data }) => {
  return (
    <section>
      <h2>Account Overview</h2>
      <div className="stats-grid">
        <p>Balance: <span id="balance">{data?.balance ?? '--'}</span></p>
        <p>Margin: <span id="margin">{data?.margin ?? '--'}</span></p>
      </div>
    </section>
  );
};

export default AccountOverview;
