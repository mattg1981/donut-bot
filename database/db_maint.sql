delete from earn2tip where created_date < (select Date('now', '-90 days'));
delete from faucet where created_date < (select Date('now', '-90 days'));
delete from flair where flair.last_update < (select Date('now', '-90 days'));
delete from history where history.created_at < (select Date('now', '-90 days'));
delete from onchain_tip where created_date < (select Date('now', '-90 days'));
-- delete from post where created_date < (select Date('now', '-90 days'));
vacuum;
.quit